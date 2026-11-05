"""report: renders the certified serialized result. Every contract row of one week from the last run_log run whose manifest (code, Stan sources, model
version, dependencies and the data it opened) equals the current state, keyed by the player's id with his roster name beside it, the integer counts
behind each p (n_over of n_finished_worlds finishing worlds, of n_worlds) or its typed reason, and the run's terminal status and decisions.
No match refuses, naming each differing entry. display_check is run by the quality_gate on every row: displayed p = graded p; an injected change is caught;
the current state selects a run and an injected manifest difference is refused and named. Usage: python3 report.py SEASON WEEK"""
import sys, pathlib, hashlib, json, re
import pandas as pd
import policy as K
import record, run_log

HERE = pathlib.Path(__file__).resolve().parent
PROBE = HERE / "_probe"
PH = K.POLICY["print_hex"]


def differences(row_manifest, now):
    """Entries where a run's manifest differs from the current one: [(section, key, row value, current value)]."""
    out = []
    for sec in ("code", "stan", "data"):
        a, b = row_manifest.get(sec, {}), now.get(sec, {})
        for k in sorted(set(a) | set(b)):
            if k in a and k in b and a[k] != b[k]: out.append((sec, k, a[k], b[k]))
            elif k in a and k not in b and sec != "data": out.append((sec, k, a[k], None))
            elif k in b and k not in a: out.append((sec, k, None, b[k]))
    if row_manifest.get("model_version") != now.get("model_version"): out.append(("model_version", "", row_manifest.get("model_version"), now.get("model_version")))
    for k in sorted(set(row_manifest.get("dependencies", {})) | set(now.get("dependencies", {}))):
        if row_manifest.get("dependencies", {}).get(k) != now["dependencies"].get(k): out.append(("dependencies", k, row_manifest.get("dependencies", {}).get(k), now["dependencies"].get(k)))
    return out


def select(now, rows=None):
    """(row, None) for the last run with a contract whose manifest equals now; else (None, the latest such row's differences)."""
    rows = run_log.rows() if rows is None else rows; first = None
    for r in reversed(rows):
        if not r.get("contract"): continue
        why = differences(r.get("manifest", {}), now)
        if not why: return r, None
        if first is None: first = why
    return None, first


def proven_contract():
    now = run_log.manifest(); row, why = select(now)
    if row is None:
        raise SystemExit("report: nothing proven to show; the latest run differs in " + "; ".join(f"{s}:{k} (row {str(a)[:PH]}, now {str(b)[:PH]})" for s, k, a, b in (why or [])))
    return row, PROBE / row["contract"]


def render(C, season, week):
    C = C[C.season.eq(season) & C.week.eq(week)]
    pos, _ = record.positions(season); nm = record.names(season)
    C = C.merge(pos[pos.week.eq(week)][["player", "position"]], on="player", how="left").sort_values(["posteam", "position", "player", "stat"])
    out = []
    for r in C.itertuples(index=False):
        said = (f"p={r.p:.3f} ({int(r.n_over)} of {int(r.n_finished_worlds)} finishing worlds over, of {int(r.n_worlds)}; MC se {r.mc_se:.3f}; median {r.q50:g}, middle half {r.q25:g}-{r.q75:g})"
                if pd.notna(r.p) else f"not priced: {r.reason_words}")
        avg = f"{r.avg_sum / r.avg_n:.2f} over {int(r.avg_n)} finished games" if pd.notna(r.avg_n) and r.avg_n else "no average"
        out.append(f"{r.posteam:4s} {str(r.position):3s} {r.player:12s} {str(nm.get(r.player, '')):24s} {K.WORDS[r.stat]:16s} avg {avg:30s} {said}")
    return C, out


def key_check(now):
    row, _ = select(now)
    if row is None: raise SystemExit("KEY FAIL: the current state selects no run")
    named = {}
    for sec in ("code", "stan", "data", "dependencies"):
        k0 = next(iter(now[sec]), None)
        if k0 is None: continue
        injected = json.loads(json.dumps(now)); injected[sec][k0] = "injected"; r2, why = select(injected)
        named[f"{sec}:{k0}"] = r2 is None and any(x[0] == sec and x[1] == k0 for x in (why or []))
    injected = json.loads(json.dumps(now)); injected["model_version"] = "injected"; r3, why3 = select(injected); named["model_version"] = r3 is None and any(x[0] == "model_version" for x in (why3 or []))
    if not all(named.values()): raise SystemExit(f"KEY FAIL: injected manifest differences not all refused and named: {named}")
    return f"KEY: current state selects run {row['row_hash'][:PH]} -> PASS\nCAN FAIL KEY: an injected difference in each manifest section is refused and named {named}"


def mask_check(C):
    """One finishing mask per player: n_finished_worlds identical across his stats (DONE: shared mask); an injected change is caught."""
    g = C[C.p.notna()].groupby(["season", "week", "posteam", "player"]).n_finished_worlds.nunique()
    bad = int((g > 1).sum()); P = C.copy(); i = P.index[P.p.notna()]
    if len(i): P.loc[i[0], "n_finished_worlds"] = P.loc[i[0], "n_finished_worlds"] + 1
    g2 = P[P.p.notna()].groupby(["season", "week", "posteam", "player"]).n_finished_worlds.nunique(); caught = int((g2 > 1).sum()) > bad if len(i) else False
    return bad, caught


def display_check(path, now=None):
    """DISPLAY: render the latest week of the contract at path, read every shown p back in order and require each to equal the contract's p at the
    shown precision with every row shown; one p injected to its complement must be caught; the finishing mask is shared; then KEY."""
    C0 = pd.read_csv(path); season = int(C0.season.max()); week = int(C0[C0.season.eq(season)].week.max())
    shown = lambda C: [m.group(1) for m in (re.search(r"p=([0-9.]+)", l) for l in render(C, season, week)[1]) if m]
    Cs, lines = render(C0, season, week); want = [f"{p:.3f}" for p in Cs.p if pd.notna(p)]
    rows_ok, p_ok = len(lines) == len(Cs), shown(C0) == want
    P = C0.copy(); ix = P.index[P.season.eq(season) & P.week.eq(week) & P.p.notna()]
    caught = True
    if len(ix):
        j = next((i for i in ix if f"{P.at[i, 'p']:.3f}" != f"{1 - P.at[i, 'p']:.3f}"), None)
        if j is not None: P.at[j, "p"] = 1 - P.at[j, "p"]; caught = shown(P) != want
    bad_mask, mask_caught = mask_check(C0)
    if not (rows_ok and p_ok and caught and bad_mask == 0 and mask_caught): raise SystemExit(f"DISPLAY FAIL: rows shown {rows_ok}, p read back equal {p_ok}, injected change caught {caught}, players with more than one mask {bad_mask}, injected mask change caught {mask_caught}")
    text = (f"DISPLAY (displayed p = graded p): {pathlib.Path(path).name} season {season} week {week}: rows {len(Cs)} all shown, every p read back equal, one finishing mask per player -> PASS\n"
            f"CAN FAIL DISPLAY: one p injected to its complement is caught; one injected mask change is caught")
    return text + ("\n" + key_check(now) if now is not None else "")


def write(season, week):
    row, path = proven_contract(); C, lines = render(pd.read_csv(path), season, week)
    out = [K.SENTENCE, "", f"BENCHMARK: {K.BENCHMARK}", f"run {row['row_hash'][:PH]} status {row.get('status')} decisions {json.dumps(row.get('decisions'))}",
           f"contract {path.name} season {season} week {week} rows {len(C)} (priced {int(C.p.notna().sum())}, declared {int(C.reason.notna().sum())})", ""] + lines
    txt = "\n".join(out).encode(); h = hashlib.sha256(txt).hexdigest()[:PH]
    p_ = PROBE / f"face_{season}_w{week}_{h}.txt"; p_.write_bytes(txt)
    print(f"written {p_.name}"); print("\n".join(out[:PH]))


if __name__ == "__main__":
    _, season, week = sys.argv
    write(int(season), int(week))
