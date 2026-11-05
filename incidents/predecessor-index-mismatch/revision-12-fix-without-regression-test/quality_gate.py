"""quality_gate: the one release run. Lint; the raw files against their pins; the manifest; every construction check proven able to fail; the fits of every
cutoff in scope (typed); every slate priced through the joint simulation; the contract serialized; the grader's structured decisions; the report's
display readback; one terminal run_log record (PASSED, FAILED_REQUIREMENTS, INSUFFICIENT, STOPPED or CRASHED) for every attempted run, a crash
recorded with its exception and phase. Usage: python3 quality_gate.py [--pin] [--seasons 2020,2021] [--weeks 4-17]; VERSION3_SCORE_HOLDOUT=<season> opens the
certification data once (its access is marked in the run_log before any outcome is read)."""
import ast, os, sys, json, pickle, traceback, pathlib
import multiprocessing as mp
import numpy as np, pandas as pd
import policy as K
import record, rules, model, product, grader, checks, run_log, report

HERE = pathlib.Path(__file__).resolve().parent
PROBE = HERE / "_probe"
PINS = PROBE / "raw_pins.json"
FORBID = {"grader.py": {"product", "report", "quality_gate"}, "product.py": {"grader", "checks", "report", "quality_gate"}, "record.py": {"product", "grader", "checks", "report", "quality_gate", "model"},
          "rules.py": {"record", "product", "grader", "model"}, "model.py": {"product", "grader", "report", "quality_gate"}, "policy.py": {"record", "rules", "model", "product", "grader"}}


class Stop(RuntimeError):
    pass


def lint():
    refusals = []
    for f, forbidden in FORBID.items():
        tree = ast.parse((HERE / f).read_text())
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for n in names:
                if n.split(".")[0] in forbidden: refusals.append(f"{f}: imports {n}")
    return refusals


def check_raw():
    now = record.raw_pins()
    if "--pin" in sys.argv: PINS.write_text(json.dumps(now, indent=1, sort_keys=True)); print(f"RAW pinned {len(now)} files (the reviewer's --pin)")
    if not PINS.exists(): raise Stop("RAW: no pins; the reviewer pins the raw files once with: python3 quality_gate.py --pin")
    pins = json.loads(PINS.read_text())
    diff = {"changed": sorted(k for k in pins if k in now and now[k] != pins[k]), "missing": sorted(set(pins) - set(now)), "new": sorted(set(now) - set(pins))}
    injected = dict(pins); injected[next(iter(injected))] = "injected-sha"
    if not sorted(k for k in injected if k in pins and pins[k] != injected[k]): raise Stop("RAW: the pin comparison cannot see a changed file (vacuous)")
    print(f"\nGAP   RAW: files={len(now)} pinned={len(pins)} {diff} -> {'PASS' if not any(diff.values()) else 'FAIL'}\nCAN FAIL RAW: an injected sha is seen as changed")
    if any(diff.values()): raise Stop("RAW: the raw files differ from their pins")


def guard(rows):
    """Refusals before pricing: the manifest carries every required entry (an injected manifest lacking one raises); NO WRITE when product, model,
    grader, quality_gate and report equal the last run's."""
    m = run_log.manifest(); why = []
    injected = dict(m); injected.pop("stan")
    missing_caught = [k for k in run_log.REQUIRED_MANIFEST if not injected.get(k)] == ["stan"]
    if not missing_caught: raise Stop("GUARD: a manifest missing a required entry is not named (vacuous)")
    last = rows[-1] if rows else None
    if last is not None and all(m["code"].get(f) == last.get("manifest", {}).get("code", {}).get(f) for f in ("product.py", "model.py", "grader.py", "quality_gate.py", "report.py")) \
            and m["stan"] == last.get("manifest", {}).get("stan") and "--rerun" not in sys.argv:
        why.append("NO WRITE: product.py, model.py, grader.py, quality_gate.py, report.py and the Stan sources equal the last run's (pass --rerun to re-grade the same code)")
    print(f"\nGAP   GUARD: {why or 'none'} -> {'PASS' if not why else 'FAIL'}\nCAN FAIL GUARD: a manifest lacking a required entry is named")
    if why: raise Stop("GUARD: " + "; ".join(why))
    return m


def arg(name, default):
    if name in sys.argv: return sys.argv[sys.argv.index(name) + 1]
    return default


def scope():
    """Seasons and weeks to forecast. Development: seasons on disk with a prior season, never the hold-out. Certification: the hold-out alone, under
    VERSION3_SCORE_HOLDOUT, access marked first and refused if already inspected."""
    hold = K.POLICY["holdout_season"]; on_disk = record.seasons_on_disk(); lo, hi = K.POLICY["claim_weeks"]
    weeks = arg("--weeks", f"{lo}-{hi}"); a, b = (int(x) for x in weeks.split("-")); weeks = list(range(a, b + 1))
    if os.environ.get("VERSION3_SCORE_HOLDOUT") == str(hold):
        if run_log.inspected(hold): raise Stop(f"CERTIFICATION: hold-out {hold} (dataset {run_log.dataset_identity(hold)}) was inspected before; it stays inspected across product hashes")
        did = run_log.mark_access(hold, "quality_gate certification run"); print(f"CERTIFICATION: access to hold-out {hold} marked (dataset {did}) before any outcome is read")
        return [hold], weeks, K.CERTIFICATION
    s_arg = arg("--seasons", None); seasons = [int(x) for x in s_arg.split(",")] if s_arg else [s for s in on_disk if s != hold and any(t < s for t in on_disk if t != hold)]
    if hold in seasons: raise Stop("SCOPE: the hold-out cannot be a development season")
    return seasons, weeks, K.DEVELOPMENT


_F = {}


def _price_game(args):
    season, week, home, away, cutoff = args
    F = _F.get(cutoff.fit_key()) or model.load_fits(cutoff); _F[cutoff.fit_key()] = F
    out = []
    for team in (home, away):
        L = product.price(season, week, team, F, cutoff); out.append((L.frame, L.counts, L.audit, L.team_frame))
    return out


def price_all(games):
    workers = K.POLICY["workers"] or max(1, (os.cpu_count() or 1) - 1); frames = []; tframes = []; counts = {k: 0 for k in product.COUNT_KEYS}; audit = {k: 0 for k in product.AUDIT_KEYS}
    print(f"PRICE games={len(games)} workers={workers}")
    with mp.get_context("fork").Pool(workers) as pool: results = pool.map(_price_game, games, chunksize=1)
    for res in results:
        for frame, c, a, tf in res:
            frames.append(frame); tframes.append(tf)
            for k, v in c.items(): counts[k] += v
            for k, v in a.items(): audit[k] += v
    return pd.concat(frames, ignore_index=True), counts, audit, pd.concat(tframes, ignore_index=True)


def main():
    phase = "start"; row = {"status": None, "phase": None}; code = 1
    try:
        phase = "LINT"; ref = lint(); print(f"LINT refusals={len(ref)}" + "".join(f"\n  {r}" for r in ref))
        if ref: raise Stop("LINT: " + "; ".join(ref))
        phase = "RAW"; check_raw()
        phase = "SCOPE"; seasons, weeks, partition = scope(); on_disk = record.seasons_on_disk()
        print(f"SEASONS on disk={on_disk} forecast={seasons} weeks={weeks[0]}-{weeks[-1]} partition={partition} hold-out={K.POLICY['holdout_season']} model_version={K.MODEL_VERSION}")
        read = [s for s in on_disk if s != K.POLICY["holdout_season"]]
        for s in read + ([K.POLICY["holdout_season"]] if partition == K.CERTIFICATION else []): print(f"RECORD {s}: {json.dumps(record.counts(s), default=str)}")
        for s in seasons: print(f"AVAILABILITY {s}: {record.availability(s)}")
        print(f"ISSUE TIME: {K.ISSUE_TIME}")
        fdir, wrote = record.materialize(PROBE / "facts", read); print(f"FACTS {'written' if wrote else 'present'} at {fdir} (game, plays, team_game, player_game; one copy per data version)")
        phase = "GUARD"; rows = run_log.rows(); guard(rows)
        phase = "CHECKS"; cut0 = record.make_cutoff(seasons[0], weeks[0], partition)
        for c in checks.build(read, cut0):
            ok, detail = c.run(); print(f"\n{'DataGap  ' if c.gates else 'PRINT'} {c.name}: {'PASS' if ok else 'FAIL'}\n{detail}")
            print(f"CAN FAIL {c.name}: {c.can_fail()}")
            if c.gates and not ok: raise Stop(c.name)
        phase = "FIT"; cutoffs = {}; fit_status = {}
        for s in seasons:
            for w in weeks:
                c_ = record.make_cutoff(s, w, partition); cutoffs[(s, w)] = c_
                if c_.fit_key() not in fit_status:
                    F = model.load_or_fit(c_); fit_status[c_.fit_key()] = {"fit": f"{c_.season}w{c_.fit_week:02d}", "status": F.status(), "counts": F.counts}
        bad = {k: v for k, v in fit_status.items() if any(st != K.FIT_OK for st in v["status"].values())}
        print(f"\nFITS: {json.dumps(fit_status, default=str)}")
        if bad:
            row.update({"status": K.INSUFFICIENT, "phase": phase, "fits": fit_status, "why": "a fit is not FIT_OK: a numerical or data failure is not a predictive decision"})
            raise Stop("FIT: " + json.dumps({k: v["status"] for k, v in bad.items()}))
        phase = "PRICE"; games = []
        for (s, w), c_ in cutoffs.items():
            G = record.games(s); G = G[G.week.eq(w)]
            games += [(s, w, r.home_team, r.away_team, c_) for r in G.itertuples(index=False)]
        C, counts, audit, TF = price_all(games)
        print(f"\nPRODUCT counts: {counts}\nAUDIT (construction identities over every world; each must be 0 except worlds): {audit}")
        bad_a = {k: v for k, v in audit.items() if k != "worlds" and v}
        if bad_a: raise Stop(f"AUDIT {bad_a}")
        phase = "CONTRACT"; path, csha = product.write_contract(C, PROBE); print(f"CONTRACT {path.name} rows={len(C)}")
        tpath = PROBE / f"patterns_{csha[: K.POLICY['print_hex']]}.csv.gz"; TF.to_csv(tpath, index=False)
        PT = grader.patterns(TF); print(f"PATTERNS written {tpath.name} ({len(PT)} side-lens rows)")
        GF, gf = grader.gameflow(TF)
        phase = "JUDGE"; prior = [s for s in read if s < min(seasons)]
        L = grader.baseline(grader.lines(prior + seasons, cutoffs[(seasons[0], weeks[0])]), seasons)
        D, summary, user, Jm = grader.score(L, product.read_contract(path), seasons, weeks)
        phase = "DISPLAY"; m = run_log.manifest(fit_keys=list(fit_status))
        pre = dict(manifest=m, contract=path.name, contract_sha=csha, product_counts=counts, audit=audit, fits=fit_status, grader=summary, decisions={k: v["status"] for k, v in D.items()},
                   partition=partition, seasons=seasons, weeks=[weeks[0], weeks[-1]], patterns=tpath.name, gameflow=gf, availability={s: record.availability(s) for s in seasons},
                   pattern_pooled=(PT.groupby(["side", "lens"]).agg(simulated=("simulated", "mean"), baseline=("baseline", "mean"), covered=("inside_band", "mean")).reset_index().to_dict("records") if len(PT) else []))
        # the report must be able to select this run: append a provisional row, run DISPLAY, then record the terminal status
        h = run_log.append(dict(pre, status="PROVISIONAL", phase=phase)); print(report.display_check(path, m))
        cert = D["certifiable"]["status"]
        status = K.PASSED if cert == K.PASS else (K.FAILED_REQUIREMENTS if cert == K.FAIL else K.INSUFFICIENT)
        row.update(pre | {"status": status, "phase": "DONE", "provisional_row": h})
        code = 0 if status == K.PASSED else 1
    except Stop as e:
        print(f"\nCHAIN STOPPED at {phase}: {e}"); row.update({"status": row.get("status") or K.STOPPED, "phase": phase, "why": str(e)})
    except BaseException as e:
        print(f"\nCHAIN CRASHED at {phase}: {type(e).__name__}: {e}"); traceback.print_exc()
        row.update({"status": K.CRASHED, "phase": phase, "exception": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()[-4000:]})
    try: row.setdefault("manifest", run_log.manifest())
    except Exception as e: row["manifest_error"] = str(e)
    h = run_log.append(row); print(f"\nLEDGER row {h[: K.POLICY['print_hex']]}  STATUS {row['status']} (phase {row['phase']})")
    sys.exit(code)


if __name__ == "__main__":
    main()
