"""run_log: evidence identities. The one dependency manifest (every project module, every Stan source, every raw file opened, the fit
identities and the pinned library versions), the chained run history (one terminal record per attempted run: PASSED, FAILED_REQUIREMENTS,
INSUFFICIENT, STOPPED or CRASHED), and the certification-access state, tracked by dataset identity and marked before any outcome is read."""
import json, sys, pathlib, hashlib, datetime, importlib
import policy as K
import record

HERE = pathlib.Path(__file__).resolve().parent
PATH = HERE / "_probe" / "run_log.jsonl"
ACCESS = HERE / "_probe" / "certification_access.json"
MODULES = ["policy.py", "rules.py", "record.py", "model.py", "product.py", "grader.py", "run_log.py", "checks.py", "quality_gate.py", "report.py"]
REQUIRED_MANIFEST = ("code", "stan", "data", "model_version", "dependencies")


def dependencies():
    out = {"python": sys.version.split()[0]}
    for name in ("numpy", "pandas", "scipy", "cmdstanpy"):
        try: out[name] = importlib.import_module(name).__version__
        except Exception: out[name] = None
    return out


def manifest(fit_keys=None):
    """The one manifest schema: used by the guard, its injected tests and the report's selection alike."""
    code = {f: record.sha(HERE / f) for f in MODULES if (HERE / f).exists()}
    stan = {p.name: record.sha(p) for p in sorted((HERE / K.MODEL["stan_dir"]).glob("*.stan"))}
    if (HERE / "map.json").exists(): code["map.json"] = record.sha(HERE / "map.json")
    m = {"code": dict(sorted(code.items())), "stan": stan, "data": dict(sorted(record.OPENED.items())), "model_version": K.MODEL_VERSION,
         "dependencies": dependencies(), "fits": sorted(fit_keys or [])}
    missing = [k for k in REQUIRED_MANIFEST if not m.get(k)]
    if missing: raise RuntimeError(f"run_log: manifest lacks required entries {missing}")
    return m


def rows():
    return [json.loads(x) for x in PATH.read_text().splitlines() if x.strip()] if PATH.exists() else []


def append(row):
    PATH.parent.mkdir(exist_ok=True)
    prev = rows(); row = dict(row, time=datetime.datetime.now().isoformat(timespec="seconds"), prev_hash=prev[-1]["row_hash"] if prev else None)
    row["row_hash"] = hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()
    with open(PATH, "a") as f: f.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    return row["row_hash"]


# ----------------------------------------------------------------------------------------------------------------------------- certification access
def access_state():
    return json.loads(ACCESS.read_text()) if ACCESS.exists() else {"datasets": {}}


def dataset_identity(season):
    """The certification dataset's identity: the evaluation population (the hold-out season), independent of file copies, hashes, later revisions of
    the files and any product hash. The files' shas are recorded as attributes of each access, never as the identity."""
    return f"holdout-{season}"


def dataset_files(season):
    return {p.name: record.sha(p) for p in sorted(record.RAW.glob(f"*{season}*")) if p.is_file()}


def inspected(season):
    return dataset_identity(season) in access_state()["datasets"]


def mark_access(season, why):
    """Record that the certification data is about to be read. Written before any outcome is revealed; never removed."""
    st = access_state(); did = dataset_identity(season)
    st["datasets"].setdefault(did, {"season": season, "first_access": datetime.datetime.now().isoformat(timespec="seconds"), "accesses": []})
    st["datasets"][did]["accesses"].append({"time": datetime.datetime.now().isoformat(timespec="seconds"), "why": why, "model_version": K.MODEL_VERSION, "files": dataset_files(season)})
    ACCESS.parent.mkdir(exist_ok=True); ACCESS.write_text(json.dumps(st, indent=1, sort_keys=True)); return did
