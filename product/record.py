"""version 4 record, identity layer (S0): what is true of the raw files. No fit, no simulation, no fill (R2).
Every function prints what it excluded (section 8). HOLD-OUT 2022 is held_out here (R10)."""
import os, re, json, hashlib
import pandas as pd
import policy

assert policy.HOLD == 2022


class DataGap(Exception):
    """A contradiction, an untyped arrival, a missing or altered file. Stops the run; never a value."""


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def raw_pins():
    if not os.path.exists(policy.PINS_FILE):
        raise DataGap(f"pins file missing: {policy.PINS_FILE}")
    pins = json.load(open(policy.PINS_FILE))
    if pins.get("raw_dir") != policy.RAW_DIR:
        raise DataGap(f"pins raw_dir {pins.get('raw_dir')!r} != policy.RAW_DIR {policy.RAW_DIR!r}")
    if len(pins["pins"]) != policy.RAW_FILE_COUNT:
        raise DataGap(f"pins count {len(pins['pins'])} != policy.RAW_FILE_COUNT {policy.RAW_FILE_COUNT}")
    return pins


def data_version(pins=None):
    pins = raw_pins() if pins is None else pins
    text = "".join(f"{n}:{pins['pins'][n]}\n" for n in sorted(pins["pins"]))
    return hashlib.sha256(text.encode()).hexdigest()


def seasons_on_disk():
    found = sorted(int(m.group(1)) for n in os.listdir(policy.RAW_DIR)
                   for m in [re.fullmatch(r"pbp_(\d{4})\.csv\.gz", n)] if m)
    print(f"seasons_on_disk {found}")
    return tuple(found)


def disk_shas(pins):
    return {n: sha(os.path.join(policy.RAW_DIR, n)) for n in sorted(pins["pins"])
            if os.path.exists(os.path.join(policy.RAW_DIR, n))}


def deficiencies(pins=None, shas=None):
    """Every way the raw directory differs from the pins. Empty list = none."""
    pins = raw_pins() if pins is None else pins
    on_disk = set(os.listdir(policy.RAW_DIR))
    missing = sorted(set(pins["pins"]) - on_disk)
    unpinned = sorted(on_disk - set(pins["pins"]))
    shas = disk_shas(pins) if shas is None else shas
    altered = sorted(n for n in pins["pins"] if n in shas and shas[n] != pins["pins"][n])
    out = [f"missing {n}" for n in missing] + [f"unpinned {n}" for n in unpinned] + [f"altered {n}" for n in altered]
    print(f"deficiencies pinned {len(pins['pins'])} on_disk {len(on_disk)} missing {len(missing)} "
          f"unpinned {len(unpinned)} altered {len(altered)}")
    return out, shas


def identity(pins=None, shas=None):
    """R1 DATA IDENTITY. Prints PASS or raises DataGap. FAILS WHEN any deficiency exists or the derived
    data_version != policy.DATA_VERSION. REPLAY is declared UNBUILT until the credits chain lands."""
    pins = raw_pins() if pins is None else pins
    defs, shas = deficiencies(pins, shas)
    dv = data_version(pins)
    matched = sum(1 for n in pins["pins"] if shas.get(n) == pins["pins"][n])
    line = (f"R1 DATA IDENTITY pins matched {matched}/{len(pins['pins'])} data_version {dv} "
            f"contract {policy.DATA_VERSION} pinned {pins['data_version']}")
    if defs or dv != policy.DATA_VERSION or pins["data_version"] != policy.DATA_VERSION:
        print(line + " FAIL")
        raise DataGap("R1 FAIL: " + "; ".join(defs or [f"data_version {dv} pinned {pins['data_version']} contract {policy.DATA_VERSION}"]))
    print(line + " PASS")
    print("R1 REPLAY per stat: UNBUILT (credits chain not accepted); no read runs before it prints")
    return {"data_version": dv, "shas": shas}


INT_RE = re.compile(r"^-?\d+(\.0+)?$")
EMPTY = ("", "NA", "NaN", "nan", "NULL")


def typed(df, types, where):
    """Every column arrives typed by the manifest or the run stops (R2). An empty cell is None only where
    the manifest says nullable. FAILS WHEN a column outside the manifest arrives, a typed column is absent,
    a non-nullable column has an empty cell, or an int column holds a non-integer."""
    untyped = [c for c in df.columns if c not in types]
    if untyped:
        raise DataGap(f"{where}: untyped arrival {untyped}")
    absent = [c for c in types if c not in df.columns]
    if absent:
        raise DataGap(f"{where}: typed column absent {absent}")
    out = {}
    for c, (kind, nullable) in types.items():
        s = df[c].astype(str).str.strip()
        empty = s.isin(EMPTY)
        if empty.any() and not nullable:
            raise DataGap(f"{where}: {c} empty in {int(empty.sum())} rows, not nullable")
        if kind == "int":
            bad = ~empty & ~s.str.match(INT_RE)
            if bad.any():
                raise DataGap(f"{where}: {c} non-integer in {int(bad.sum())} rows e.g. {s[bad].iloc[0]!r}")
            out[c] = pd.array([None if e else int(float(v)) for v, e in zip(s, empty)], dtype="Int64")
        elif kind == "float":
            num = pd.to_numeric(s.mask(empty), errors="coerce")
            bad = ~empty & num.isna()
            if bad.any():
                raise DataGap(f"{where}: {c} non-numeric in {int(bad.sum())} rows e.g. {s[bad].iloc[0]!r}")
            out[c] = num.astype(float)
        elif kind == "str":
            out[c] = pd.Series([None if e else v for v, e in zip(s, empty)], dtype=object, index=s.index)
        else:
            raise DataGap(f"{where}: unknown kind {kind!r} for {c}")
    return pd.DataFrame(out)


def header(name):
    path = os.path.join(policy.RAW_DIR, name)
    opener = __import__("gzip").open if name.endswith(".gz") else open
    with opener(path, "rt") as f:
        return f.readline().rstrip("\n").split(",")


def opened(name):
    """The record's one reader: every file opened is fingerprinted against its pin before a byte is read."""
    path = os.path.join(policy.RAW_DIR, name)
    pins = raw_pins()["pins"]
    if name not in pins:
        raise DataGap(f"unpinned raw file {name}")
    if not os.path.exists(path):
        raise DataGap(f"missing raw file {name}")
    got = sha(path)
    if got != pins[name]:
        raise DataGap(f"fingerprint mismatch {name}: disk {got[:12]} pin {pins[name][:12]}")
    return path


def raw_frame(name, columns, where):
    """The fingerprinted file as text columns; typed() follows before any value is used."""
    path = opened(name)
    cols = header(name)
    missing = [c for c in columns if c not in cols]
    if missing:
        raise DataGap(f"{where}: columns absent from {name}: {missing}")
    present_betting = [c for c in policy.BETTING_EXCLUDED if c in columns]
    if present_betting:
        raise DataGap(f"{where}: betting inputs requested {present_betting}")
    print(f"raw_frame {name} columns {len(columns)} absent {len(missing)} betting {len(present_betting)}")
    return pd.read_csv(path, usecols=list(columns), dtype=str, keep_default_na=False)


def read(name, columns, types, where):
    return typed(raw_frame(name, columns, where), types, where)


def held_out(season, where):
    """R10. FAILS WHEN a dev run reads the hold-out season while POLICY unseal is None."""
    if season == policy.HOLD and policy.POLICY["unseal"] is None:
        raise DataGap(f"{where}: HOLD-OUT {policy.HOLD} held_out; POLICY unseal is None (R10, X7)")


def schedule():
    """All seasons' games, hold-out rows excluded and counted. Betting columns are never loaded."""
    df = read(policy.SCHEDULE_FILE, policy.SCHEDULE_COLUMNS, policy.SCHEDULE_TYPES, "schedule")
    off = ~df["season"].isin(policy.SEASONS)
    hold = df["season"].eq(policy.HOLD)
    out = df[~off & ~hold].reset_index(drop=True)
    unplayed = int(out["home_score"].isna().sum())
    print(f"schedule rows {len(out)} excluded outside SEASONS {int(off.sum())} "
          f"({int(df.loc[off, 'season'].min())}-{int(df.loc[off, 'season'].max())}) excluded hold-out {int(hold.sum())} "
          f"seasons {sorted(out['season'].unique().tolist())} game_type {out['game_type'].value_counts().to_dict()} unplayed {unplayed}")
    return out


def games(season):
    held_out(season, "games")
    df = schedule()
    out = df[df["season"].eq(season)].reset_index(drop=True)
    print(f"games season {season} rows {len(out)}")
    if len(out) == 0:
        raise DataGap(f"games: no rows for season {season}")
    return out


def season_team_codes(season):
    g = games(season)
    codes = frozenset(g["home_team"].tolist()) | frozenset(g["away_team"].tolist())
    print(f"season_team_codes {season} n {len(codes)}")
    return codes


def resolve_code(code, codes):
    """Itself when a season identity, its alias when the alias is one and it is not, else None."""
    if code in codes:
        return code
    alias = policy.TEAM_ALIASES.get(code)
    if alias is not None and alias in codes:
        return alias
    return None


def contradictions(df, where):
    """R2 on the official record. FAILS WHEN any (lesser, greater) pair is violated in any row."""
    for lesser, greater in policy.OFFICIAL_CONTRADICTIONS:
        bad = df[lesser] > df[greater]
        if bad.any():
            r = df[bad].iloc[0]
            raise DataGap(f"{where}: contradiction {lesser} > {greater} in {int(bad.sum())} rows "
                      f"e.g. {r.get('player_id')} {r.get('game_id')} {lesser}={r[lesser]} {greater}={r[greater]}")
    print(f"{where} contradictions 0 over {len(policy.OFFICIAL_CONTRADICTIONS)} pairs rows {len(df)}")


def no_id_rows(raw, stat_cols, where):
    """The mask of rows with no player_id, excluded and counted. FAILS WHEN any such row carries a
    non-numeric stat or a nonzero stat (a stat credited to no one is a contradiction, R2)."""
    noid = raw["player_id"].str.strip().isin(EMPTY)
    num = raw.loc[noid, stat_cols].apply(pd.to_numeric, errors="coerce")
    if num.isna().any().any():
        raise DataGap(f"{where}: {int(num.isna().any(axis=1).sum())} rows with no player_id carry a non-numeric stat")
    nonzero = num.ne(0).any(axis=1)
    if nonzero.any():
        raise DataGap(f"{where}: {int(nonzero.sum())} rows with no player_id carry a nonzero stat (credited to no one)")
    print(f"{where} excluded rows with no player_id {int(noid.sum())} over weeks {raw.loc[noid, 'week'].nunique()} "
          f"no-id rows with nonzero stat {int(nonzero.sum())}")
    return noid


def official(season):
    """The nflverse weekly record for one season, STATS-named, with every exclusion counted."""
    held_out(season, "official")
    name = policy.STATS_FILE.format(season=season)
    cols = header(name)
    chosen = {}
    for stat, alts in policy.OFFICIAL_COLUMNS.items():
        present = [a for a in alts if a in cols]
        if len(present) != 1:
            raise DataGap(f"official {season}: {stat} maps to {present} of {alts}; exactly one required")
        chosen[stat] = present[0]
    types = dict(policy.OFFICIAL_BASE_TYPES)
    types.update({chosen[s]: ("int", False) for s in chosen})
    raw = raw_frame(name, policy.OFFICIAL_BASE + tuple(chosen.values()), f"official {season}")
    noid = no_id_rows(raw, list(chosen.values()), f"official {season}")
    df = typed(raw[~noid].reset_index(drop=True), types, f"official {season}")
    df = df.rename(columns={v: k for k, v in chosen.items()})
    df["tds"] = df["rec_td"] + df["rush_td"]
    bad_season = df["season"].ne(season)
    if bad_season.any():
        raise DataGap(f"official {season}: {int(bad_season.sum())} rows carry another season")
    dup = df.duplicated(["player_id", "game_id"]).sum()
    if dup:
        raise DataGap(f"official {season}: {int(dup)} duplicate (player, game) keys (R4)")
    print(f"official {season} R4 duplicate (player, game) keys {int(dup)} other-season rows {int(bad_season.sum())}")
    contradictions(df, f"official {season}")
    in_pos = df["position"].isin(policy.POSITIONS)
    print(f"official {season} rows {len(df)} players {df['player_id'].nunique()} games {df['game_id'].nunique()} "
          f"season_type {df['season_type'].value_counts().to_dict()} position null {int(df['position'].isna().sum())} "
          f"rows outside {policy.POSITIONS} {int((~in_pos).sum())} (kept; population(name) excludes at S1)")
    return df


def scoring_view(season):
    """The only path to realized outcomes for scoring. Refuses the hold-out season outside an unseal decision."""
    held_out(season, "scoring_view")
    return official(season)


# ---------------- S2: events layer (RUBRIC section 9; R5, R7, X9). No fill: the only zero is the sum over no events. ----------------
import time
import numpy as np

EVENT_COLUMNS = ("game_id", "season", "week", "posteam", "play_id", "play_type", "timeout", "two_point_attempt", "pass", "rush", "sack",
                 "qb_scramble", "passer_player_id", "receiver_player_id", "rusher_player_id", "complete_pass", "incomplete_pass",
                 "interception", "fumble_lost", "yards_gained", "pass_touchdown", "rush_touchdown", "touchdown", "td_team",
                 "yardline_100", "down", "ydstogo", "qtr", "game_seconds_remaining", "fixed_drive", "penalty",
                 "lateral_receiver_player_id", "lateral_rusher_player_id", "lateral_receiving_yards", "lateral_rushing_yards",
                 # scores, the scoring side and try results: the possession author reads who scored and how (11-5-1(b), 11-5-2, 11-3)
                 "home_team", "away_team", "defteam", "home_score", "away_score", "total_home_score", "total_away_score", "extra_point_result", "two_point_conv_result", "field_goal_result", "safety", "defensive_two_point_conv", "defensive_extra_point_conv")
EVENT_TYPES = {"game_id": ("str", False), "season": ("int", False), "week": ("int", False), "posteam": ("str", True),
               "play_id": ("int", False), "play_type": ("str", True), "timeout": ("int", True), "two_point_attempt": ("int", True), "pass": ("int", True),
               "rush": ("int", True), "sack": ("int", True), "qb_scramble": ("int", True), "passer_player_id": ("str", True),
               "receiver_player_id": ("str", True), "rusher_player_id": ("str", True), "complete_pass": ("int", True),
               "incomplete_pass": ("int", True), "interception": ("int", True), "fumble_lost": ("int", True),
               "yards_gained": ("int", True), "pass_touchdown": ("int", True), "rush_touchdown": ("int", True),
               "touchdown": ("int", True), "td_team": ("str", True), "yardline_100": ("int", True), "down": ("int", True),
               "ydstogo": ("int", True), "qtr": ("int", False), "game_seconds_remaining": ("int", True), "fixed_drive": ("int", False),
               "penalty": ("int", True), "lateral_receiver_player_id": ("str", True), "lateral_rusher_player_id": ("str", True),
               "lateral_receiving_yards": ("int", True), "lateral_rushing_yards": ("int", True),
               "home_team": ("str", False), "away_team": ("str", False), "defteam": ("str", True), "home_score": ("int", True), "away_score": ("int", True), "total_home_score": ("int", True), "total_away_score": ("int", True), "extra_point_result": ("str", True), "two_point_conv_result": ("str", True), "field_goal_result": ("str", True), "safety": ("int", True), "defensive_two_point_conv": ("int", True), "defensive_extra_point_conv": ("int", True)}
FLAGS = ("two_point_attempt", "pass", "rush", "sack", "qb_scramble", "complete_pass", "incomplete_pass", "interception",
         "fumble_lost", "pass_touchdown", "rush_touchdown", "touchdown", "penalty")
PLAY_TYPE_KIND = {"pass": "pass", "run": "run", "qb_kneel": "kneel", "qb_spike": "spike", "punt": "punt", "field_goal": "field_goal",
                  "kickoff": "kickoff", "extra_point": "try", "no_play": "penalty", "": "other"}
KIND_NEEDS_ID = {"passer_player_id": ("pass", "sack", "spike"), "rusher_player_id": ("run", "scramble", "kneel")}


def flag(df, c):
    """True where the flag is 1. A null flag is not set; events() counts null flags and refuses them on scrimmage rows."""
    return (df[c].notna() & (df[c] == 1)).to_numpy(dtype=bool)


def zero_sum(series, index):
    """The sum over no events is 0: a count, not a fill."""
    return series.reindex(index).to_numpy(dtype=float, na_value=0.0)


def holds_snap(text):
    """True where a play's text opens with a game clock in parentheses, "(m:ss)" or "(:ss)": a snap was run on that row.
    15-1: a lost challenge is charged a timeout, and the record writes that charge onto the snapped play's row."""
    out = np.zeros(len(text), dtype=bool)
    for i, t in enumerate(text):
        if isinstance(t, str) and t.startswith("(") and ")" in t:
            m, colon, s = t[1:t.index(")")].strip().partition(":")
            out[i] = colon == ":" and len(s) == 2 and s.isdigit() and (m == "" or (len(m) <= 2 and m.isdigit()))
    return out


def timeout_rows(pt, timeout_flag, snap):
    """The timeout label: a no_play row charged a timeout whose text holds no snap. A row that holds a snap keeps its play's
    label (a no_play is a penalty); its charged timeout stays on its timeout flag."""
    return (pt == "no_play") & timeout_flag & ~snap


def events(season):
    """One row per play with its kind (section 9 event kinds). FAILS WHEN a play_type is outside the contract, a flag is null
    on a scrimmage row, yards are null on a scrimmage row, or a kind lacks the id it needs (KIND_NEEDS)."""
    held_out(season, "events")
    t0 = time.time()
    df = read(policy.PBP_FILE.format(season=season), EVENT_COLUMNS + ("desc",), {**EVENT_TYPES, "desc": ("str", True)}, f"events {season}")   # desc read only for the snap test (15-1); dropped before return
    pt = df["play_type"].where(df["play_type"].notna(), "").to_numpy(dtype=object)
    unknown = sorted(set(pt) - set(PLAY_TYPE_KIND))
    print(f"events {season} play_type values outside the contract {len(unknown)} {unknown}")
    if unknown:
        raise DataGap(f"events {season}: play_type outside the contract {unknown}")
    kind = np.array([PLAY_TYPE_KIND[p] for p in pt], dtype=object)
    kind[(pt == "pass") & flag(df, "sack")] = "sack"
    kind[(pt == "run") & flag(df, "qb_scramble")] = "scramble"
    kind[flag(df, "two_point_attempt")] = "try"
    snap = holds_snap(df["desc"].to_numpy(dtype=object))
    tmo = timeout_rows(pt, flag(df, "timeout"), snap)
    kind[tmo] = "timeout"   # a charged timeout whose text holds no snap: not a down, not a foul
    kept = (pt == "no_play") & flag(df, "timeout") & snap
    print(f"events {season} no_play rows that are timeouts {int(tmo.sum())} | no_play rows charged a timeout that hold a snap, kept as penalty (15-1) {int(kept.sum())}")
    fake = np.isin(pt, ["field_goal", "punt"]) & df["passer_player_id"].notna().to_numpy() & (flag(df, "complete_pass") | flag(df, "incomplete_pass") | flag(df, "interception"))
    kind[fake] = "pass"   # Rule 3-24-6: a kick play that becomes a passing play in the same down is a pass (fake kick)
    df["kind"] = kind
    print(f"events {season} fake-kick passes (kick formation, passer named, pass outcome) {int(fake.sum())}")
    sc = df["kind"].isin(policy.CALL_KINDS).to_numpy()
    null_sc = {c: int((df[c].isna().to_numpy() & sc).sum()) for c in FLAGS}
    print(f"events {season} null flags on scrimmage rows {sum(null_sc.values())}")
    if any(null_sc.values()):
        raise DataGap(f"events {season}: null flags on scrimmage rows {dict((k, v) for k, v in null_sc.items() if v)}")
    null_flags = {c: int(df[c].isna().sum()) for c in FLAGS if df[c].isna().any()}
    ny = int((sc & df["yards_gained"].isna().to_numpy()).sum())
    print(f"events {season} yards_gained null on scrimmage rows {ny}")
    if ny:
        raise DataGap(f"events {season}: yards_gained null on {ny} scrimmage rows")
    for col, kinds in KIND_NEEDS_ID.items():
        m = df["kind"].isin(kinds).to_numpy() & df[col].isna().to_numpy()
        n = int(m.sum())
        print(f"events {season} KIND_NEEDS {col} missing on {n} rows of kinds {kinds}")
        if n:
            for _, r in df[m].iterrows():
                print(f"  {r['game_id']} play {r['play_id']} kind {r['kind']} play_type {r['play_type']} yards {r['yards_gained']} down {r['down']} penalty {r['penalty']}")
            raise DataGap(f"events {season}: {col} missing on {n} rows (section 9 KIND_NEEDS)")
    print(f"events {season} rows {len(df)} kinds {df['kind'].value_counts().to_dict()} scrimmage {int(sc.sum())} "
          f"null flags on non-scrimmage rows (read as not set) {null_flags} wall {time.time() - t0:.1f}s")
    df = df.drop(columns=["desc"])   # read only for the snap test; events returns EVENT_COLUMNS + kind
    return df


def time_order(ev):
    """Time order within a game: qtr, clock descending, then play_id. play_id alone is NOT time order in this record (section 9)."""
    return ev.sort_values(["game_id", "qtr", "game_seconds_remaining", "play_id"], ascending=[True, True, False, True], na_position="last")


def rulebook_checks(ev, where):
    """Section 9 rulebook identities as counts, in time order. Violating rows print. A injected_fault must raise its count."""
    sc = ev["kind"].isin(policy.CALL_KINDS).to_numpy()
    off_td = sc & (flag(ev, "pass_touchdown") | flag(ev, "rush_touchdown")) & (ev["td_team"] == ev["posteam"]).to_numpy(dtype=bool)
    sub = ev[off_td]
    out = {}
    out["TD-YARDS"] = int(sub["yards_gained"].ne(sub["yardline_100"]).to_numpy(dtype=bool, na_value=True).sum())
    inc = ev[sc & flag(ev, "incomplete_pass")]
    out["INCOMPLETE"] = int(inc["yards_gained"].ne(0).to_numpy(dtype=bool, na_value=True).sum())
    s = ev[sc]
    y = s["yardline_100"].to_numpy(dtype=float, na_value=np.nan); g = s["yards_gained"].to_numpy(dtype=float)
    out["BOUNDS yardline null"] = int(np.isnan(y).sum())
    ok = ~np.isnan(y)
    out["BOUNDS"] = int(((y[ok] < 1) | (y[ok] > 99) | (g[ok] > y[ok]) | (g[ok] < -(100 - y[ok]))).sum())
    srt = time_order(ev).copy()
    srt["t"] = np.arange(len(srt))
    srt["off_td"] = pd.Series(off_td, index=ev.index)
    prev_id = srt.groupby("game_id")["play_id"].shift()
    out["PLAY-ORDER play_id out of time order (declared)"] = int(((srt["play_id"] < prev_id) & prev_id.notna()).sum())
    q = srt[srt["game_seconds_remaining"].notna() & (srt["qtr"] <= 4)]
    firstq = q.groupby(["game_id", "qtr"])["game_seconds_remaining"].first()
    expected = 900 * (5 - firstq.index.get_level_values("qtr").to_numpy())
    badq = firstq[firstq.to_numpy() != expected]
    out["CLOCK quarter start != 900*(5-qtr)"] = int(len(badq))
    for (gid, qq), v in badq.items():
        print(f"  CLOCK {where}: {gid} qtr {qq} first clock {v}")
    ot = srt[srt["qtr"] >= 5]["game_seconds_remaining"]
    out["CLOCK OT rows"] = int(len(ot)); out["CLOCK OT max seconds"] = int(ot.max()) if len(ot) else 0
    scs = srt[srt["kind"].isin(policy.CALL_KINDS)]
    last_t = scs.groupby(["game_id", "posteam", "fixed_drive"])["t"].max().rename("last_t")
    j = srt[srt["off_td"]].join(last_t, on=["game_id", "posteam", "fixed_drive"])
    bad = j[j["t"] != j["last_t"]]
    out["DRIVE-END"] = int(len(bad))
    for _, r in bad.iterrows():
        later = scs[(scs["game_id"] == r["game_id"]) & (scs["posteam"] == r["posteam"]) & (scs["fixed_drive"] == r["fixed_drive"]) & (scs["t"] > r["t"])]
        print(f"  DRIVE-END {where}: {r['game_id']} drive {r['fixed_drive']} TD play {r['play_id']} clock {r['game_seconds_remaining']} | later scrimmage plays in time order {[(int(a), k, int(c)) for a, k, c in zip(later['play_id'], later['kind'], later['game_seconds_remaining'])]}")
    out["offensive scrimmage TDs"] = int(off_td.sum())
    print(f"rulebook {where}: " + " | ".join(f"{k} {v}" for k, v in out.items()))
    return out


def credits(ev):
    """Per (player, game, stat) from events, by section 9 Credits. Laterals split yards at the lateral; a try credits nothing;
    a penalty no-play credits nothing; a sack is no passing stat; a kneel is a carry; a spike is an attempt."""
    k = ev["kind"].to_numpy(dtype=object)
    is_pass = k == "pass"; is_spike = k == "spike"; carry = np.isin(k, policy.CARRY_KINDS)
    has_lr = ev["lateral_receiver_player_id"].notna().to_numpy(); has_lu = ev["lateral_rusher_player_id"].notna().to_numpy()
    if (has_lr & ev["lateral_receiving_yards"].isna().to_numpy()).any() or (has_lu & ev["lateral_rushing_yards"].isna().to_numpy()).any():
        raise DataGap("credits: a lateral with no lateral yards")
    yg = ev["yards_gained"].to_numpy(dtype=float, na_value=np.nan)
    lry = ev["lateral_receiving_yards"].to_numpy(dtype=float, na_value=0.0); lry[~has_lr] = 0.0   # no lateral: no yards after it
    lru = ev["lateral_rushing_yards"].to_numpy(dtype=float, na_value=0.0); lru[~has_lu] = 0.0
    ids = {c: ev[c].to_numpy(dtype=object) for c in ("passer_player_id", "receiver_player_id", "rusher_player_id",
                                                     "lateral_receiver_player_id", "lateral_rusher_player_id")}
    gid = ev["game_id"].to_numpy(dtype=object)
    comp = flag(ev, "complete_pass") & is_pass; inter = flag(ev, "interception") & is_pass
    ptd = flag(ev, "pass_touchdown") & is_pass; rtd = flag(ev, "rush_touchdown") & carry
    ones = np.ones(len(ev))
    rows = []
    def add(mask, col, stat, vals):
        m = mask & pd.notna(ids[col])
        rows.append(pd.DataFrame({"player_id": ids[col][m], "game_id": gid[m], "stat": stat, "value": vals[m]}))
    add(is_pass | is_spike, "passer_player_id", "attempts", ones)
    add(is_pass, "receiver_player_id", "targets", ones)
    add(comp, "passer_player_id", "completions", ones); add(comp, "receiver_player_id", "receptions", ones)
    add(comp, "passer_player_id", "pass_yards", yg); add(comp, "receiver_player_id", "rec_yards", yg - lry)
    add(comp & has_lr, "lateral_receiver_player_id", "rec_yards", lry)
    add(inter, "passer_player_id", "interceptions", ones)
    add(ptd, "passer_player_id", "pass_td", ones)
    add(ptd & ~has_lr, "receiver_player_id", "rec_td", ones); add(ptd & has_lr, "lateral_receiver_player_id", "rec_td", ones)
    add(carry, "rusher_player_id", "carries", ones); add(carry, "rusher_player_id", "rush_yards", yg - lru)
    add(carry & has_lu, "lateral_rusher_player_id", "rush_yards", lru)
    add(rtd & ~has_lu, "rusher_player_id", "rush_td", ones); add(rtd & has_lu, "lateral_rusher_player_id", "rush_td", ones)
    long = pd.concat(rows, ignore_index=True)
    pairs = pd.MultiIndex.from_frame(long[["player_id", "game_id"]].drop_duplicates()).set_names(["player_id", "game_id"])
    wide = pd.DataFrame(index=pairs)
    for stat in policy.STATS:
        if stat != "tds":
            wide[stat] = zero_sum(long[long["stat"] == stat].groupby(["player_id", "game_id"])["value"].sum(), pairs)
    wide["tds"] = wide["rec_td"] + wide["rush_td"]
    print(f"credits: plays with a lateral receiver {int(has_lr.sum())} lateral rusher {int(has_lu.sum())} credited (player, game) pairs {len(wide)}")
    return wide


def replay_vs_official(season, ev, built):
    """R7 AGREE. Every (player, game, stat) where events and the official file differ is listed with its rule (section 9):
    lateral_penalty - named on a lateral play carrying a flag (official yards are not the pbp's yards_gained);
    lateral_chain   - a yards stat in a game with a lateral play, where the game's yard disagreements conserve
                      (receivers' sum == passer's sum, rushing sum == 0; the pbp names one lateral receiver, the official file a chain);
    penalty         - named on a no_play row (a foul after the ball is dead does not nullify the play; the official file counts it).
    FAILS WHEN any disagreement has no rule."""
    off = official(season)
    offw = off.set_index(["player_id", "game_id"])[list(policy.STATS)].astype(float)
    idx = built.index.union(offw.index)
    B = pd.DataFrame({s: zero_sum(built[s], idx) for s in policy.STATS}, index=idx)
    O = pd.DataFrame({s: zero_sum(offw[s], idx) for s in policy.STATS}, index=idx)
    in_b = idx.isin(built.index); in_o = idx.isin(offw.index)
    k = ev["kind"].to_numpy(dtype=object)
    lat = (ev["lateral_receiver_player_id"].notna() | ev["lateral_rusher_player_id"].notna()).to_numpy()
    pen = flag(ev, "penalty")
    idcols = ("passer_player_id", "receiver_player_id", "rusher_player_id", "lateral_receiver_player_id", "lateral_rusher_player_id")
    tags = {}
    def tag(mask, name):
        for c in idcols:
            sub = ev[mask & ev[c].notna().to_numpy()]
            for g, p in zip(sub["game_id"], sub[c]):
                tags.setdefault((p, g), set()).add(name)
    tag(lat & pen, "lateral_penalty"); tag(k == "penalty", "penalty"); tag(flag(ev, "fumble_lost"), "fumble"); tag(k == "try", "try")
    diff = (B != O)
    rows = diff.any(axis=1)
    D = B - O
    yards = ("rec_yards", "pass_yards", "rush_yards")
    chain_games = set()
    for g in sorted(set(ev.loc[lat, "game_id"])):
        m = rows.to_numpy() & (idx.get_level_values("game_id") == g)
        pairs = list(idx[m])
        if not pairs:
            continue
        sub = D.loc[pairs]
        nonyard = bool(diff.loc[pairs, [s for s in policy.STATS if s not in yards]].any().any())
        conserved = (not nonyard) and sub["rec_yards"].sum() == sub["pass_yards"].sum() and sub["rush_yards"].sum() == 0
        print(f"  lateral game {g}: disagreeing pairs {len(pairs)} rec sum {int(sub['rec_yards'].sum())} pass sum {int(sub['pass_yards'].sum())} rush sum {int(sub['rush_yards'].sum())} non-yard stat differs {nonyard} -> {'lateral_chain' if conserved else 'NOT CONSERVED'}")
        if conserved:
            chain_games.add(g)
    per_stat = {s: int(diff[s].sum()) for s in policy.STATS}
    print(f"AGREE {season} pairs compared {len(idx)} (events only {int((in_b & ~in_o).sum())}, official only {int((~in_b & in_o).sum())}) disagreeing pairs {int(rows.sum())} per stat {per_stat}")
    rules = ("lateral_penalty", "lateral_chain", "penalty")
    counts = {"lateral_penalty": 0, "lateral_chain": 0, "penalty": 0, "UNEXPLAINED": 0}
    for (p, g), r in zip(idx[rows.to_numpy()], diff[rows].itertuples(index=False)):
        t = set(tags.get((p, g), set()))
        if g in chain_games and "lateral_penalty" not in t:
            t.add("lateral_chain")
        pos = idx.get_loc((p, g))
        if not in_o[pos]: t.add("official_absent")
        if not in_b[pos]: t.add("events_absent")
        explained = [x for x in rules if x in t]
        if not explained:
            t.add("UNEXPLAINED"); counts["UNEXPLAINED"] += 1
        else:
            counts[explained[0]] += 1
        stats = [s for s, d in zip(policy.STATS, r) if d]
        print(f"  {g} {p} " + " ".join(f"{s} built {B.at[(p, g), s]:.0f} official {O.at[(p, g), s]:.0f}" for s in stats) + " | " + ",".join(sorted(t)))
    print(f"AGREE {season} disagreeing pairs by rule {counts}")
    return counts["UNEXPLAINED"]

PART_COLUMNS = ("nflverse_game_id", "play_id", "possession_team", "offense_players", "n_offense")
PART_TYPES = {"nflverse_game_id": ("str", False), "play_id": ("int", False), "possession_team": ("str", True),
              "offense_players": ("str", True), "n_offense": ("int", False)}


def participation(season):
    held_out(season, "participation")
    df = read(policy.PARTICIPATION_FILE.format(season=season), PART_COLUMNS, PART_TYPES, f"participation {season}")
    dup = int(df.duplicated(["nflverse_game_id", "play_id"]).sum())
    print(f"participation {season} duplicate (game, play) keys {dup}")
    if dup:
        raise DataGap(f"participation {season}: {dup} duplicate (game, play) keys")
    print(f"participation {season} rows {len(df)} offense_players empty {int(df['offense_players'].isna().sum())} "
          f"n_offense {dict((int(k), int(v)) for k, v in df['n_offense'].value_counts().items())}")
    return df


def on_field_sets(ev, part, where):
    """(game_id, play_id) -> frozenset of offense ids, or None when unknown. Never guessed."""
    keys = set(zip(ev["game_id"], ev["play_id"]))
    pkeys = set(zip(part["nflverse_game_id"], part["play_id"]))
    sets = {}
    size_mismatch = 0
    for g, p, s, n in zip(part["nflverse_game_id"], part["play_id"], part["offense_players"], part["n_offense"]):
        if s is None:
            sets[(g, p)] = None
        else:
            fs = frozenset(x for x in s.split(";") if x)
            if len(fs) != n:
                size_mismatch += 1
            sets[(g, p)] = fs
    print(f"on_field_sets {where}: events plays {len(keys)} participation plays {len(pkeys)} events without participation {len(keys - pkeys)} "
          f"participation without events {len(pkeys - keys)} unknown sets {sum(1 for v in sets.values() if v is None)} n_offense != set size {size_mismatch}")
    return sets


ROSTER_COLUMNS = ("season", "week", "gsis_id", "position")
ROSTER_TYPES = {"season": ("int", False), "week": ("int", False), "gsis_id": ("str", True), "position": ("str", True)}


def positions(season):
    """gsis_id -> position for the season; a player with two positions in one week is excluded and counted."""
    held_out(season, "positions")
    df = read(policy.ROSTER_FILE.format(season=season), ROSTER_COLUMNS, ROSTER_TYPES, f"positions {season}")
    noid = int(df["gsis_id"].isna().sum()); nopos = int(df["position"].isna().sum())
    d = df[df["gsis_id"].notna() & df["position"].notna()]
    wk = d.groupby(["gsis_id", "week"])["position"].nunique()
    two_in_week = set(wk[wk > 1].index.get_level_values(0))
    se = d.groupby("gsis_id")["position"].nunique()
    multi = set(se[se > 1].index) | two_in_week
    pos = {g: p for g, p in d.drop_duplicates("gsis_id")[["gsis_id", "position"]].itertuples(index=False) if g not in multi}
    print(f"positions {season} roster rows {len(df)} no gsis_id {noid} no position {nopos} players {d['gsis_id'].nunique()} "
          f"two positions in a week {len(two_in_week)} excluded (any ambiguity) {len(multi)} mapped {len(pos)}")
    return pos


def finished_pairs(season, ev, sets, pos):
    """FINISH per (game, player) over the participation pairs; the counts finished() prints are taken from this dict.
    TRUE: on a known snap of the team's final offensive drive. FALSE: every snap of that drive known and he is on none.
    UNKNOWN: otherwise. A penalty no-play is a snap when its known set shows a QB and no K or P; unknown position = unknown snap."""
    sc = ev[ev["kind"].isin(policy.CALL_KINDS) & ev["posteam"].notna()]
    final = sc.groupby(["game_id", "posteam"])["fixed_drive"].max()
    team_games = ev[ev["posteam"].notna()].groupby(["game_id", "posteam"]).size()
    no_drive = [k for k in team_games.index if k not in final.index]
    print(f"finished {season} team-games with no scrimmage snap {len(no_drive)}")
    if no_drive:
        raise DataGap(f"finished {season}: team-games with no scrimmage snap {no_drive}")
    status = {}; tg_unknown = 0; snaps_final = 0; unknown_final = 0
    ev_team = ev[ev["posteam"].notna()]
    for (g, team), fd in final.items():
        rows = ev_team[(ev_team["game_id"] == g) & (ev_team["posteam"] == team)]
        players = set()
        for p in rows["play_id"]:
            s = sets.get((g, p))
            if s:
                players |= s
        drive = rows[rows["fixed_drive"] == fd]
        known = []; unknown = 0
        for p, k in zip(drive["play_id"], drive["kind"]):
            s = sets.get((g, p))
            if k in policy.CALL_KINDS:
                if s: known.append(s)
                else: unknown += 1
            elif k == "penalty":
                if not s:
                    unknown += 1
                else:
                    ps = [pos.get(x) for x in s]
                    if any(q is None for q in ps):
                        unknown += 1
                    elif "QB" in ps and "K" not in ps and "P" not in ps:
                        known.append(s)
        snaps_final += len(known); unknown_final += unknown
        if unknown: tg_unknown += 1
        on = set().union(*known) if known else set()
        for m in players:
            status[(g, m)] = "TRUE" if m in on else ("FALSE" if unknown == 0 else "UNKNOWN")
    return status, len(final), snaps_final, unknown_final, tg_unknown


def finished(season, ev, sets, pos):
    """The S2 counts, taken from finished_pairs; byte-identical to the accepted printout."""
    status, n_tg, snaps_final, unknown_final, tg_unknown = finished_pairs(season, ev, sets, pos)
    counts = {"TRUE": 0, "FALSE": 0, "UNKNOWN": 0}
    for v in status.values():
        counts[v] += 1
    pairs = len(status); total = sum(counts.values())
    print(f"FINISH {season} team-games {n_tg} participation pairs {pairs} TRUE {counts['TRUE']} FALSE {counts['FALSE']} UNKNOWN {counts['UNKNOWN']} "
          f"sum {total} {'PASS' if total == pairs else 'FAIL'} | final-drive known snaps {snaps_final} unknown snaps {unknown_final} team-games with an unknown final-drive snap {tg_unknown}")
    return counts
