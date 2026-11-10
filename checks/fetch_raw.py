"""Fetch the pinned raw files from their public sources, so any clean checkout can rerun the record checks (gate E3: evidence someone can replay).
Reads product/RAW_PINS.json. For each pinned file absent from data/raw it downloads the file from its public source (SOURCES: nflverse's releases), checks its
SHA-256 against the pin, and keeps it only on a match; a mismatch is refused by name (the source revised the file: a foundation change, which reopens everything
built on it). The 15 files no public source serves as the pinned bytes (the living schedule and player files, and files re-compressed on download) are
committed in data/raw instead (COMMITTED). Measured 2026-11-10: the other 30 match their pins byte for byte.
python3 checks/fetch_raw.py   |   --self-test (a download whose bytes differ from its pin must be refused)
Exit 0 when every pinned file is in data/raw with its pinned fingerprint; 1 otherwise."""
import hashlib, json, os, re, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); RAW = os.path.join(ROOT, "data", "raw"); PINS = os.path.join(ROOT, "product", "RAW_PINS.json")
BASE = "https://github.com/nflverse/nflverse-data/releases/download/"
SOURCES = {"pbp": "pbp/play_by_play_{y}.csv.gz", "stats": "stats_player/stats_player_week_{y}.csv.gz", "injuries": "injuries/injuries_{y}.csv",
           "snaps": "snap_counts/snap_counts_{y}.csv.gz", "rosters": "weekly_rosters/roster_weekly_{y}.csv.gz"}
COMMITTED = {"games.csv", "players.csv", "db_playerids.csv"} | {f"pbp_participation_{y}.csv.gz" for y in range(2019, 2026)} | {f"rosters_{y}.csv.gz" for y in range(2019, 2024)}


def sha(data): return hashlib.sha256(data).hexdigest()


def url_of(name):
    m = re.fullmatch(r"([a-z]+)_(\d{4})\.csv(\.gz)?", name)
    return BASE + SOURCES[m.group(1)].format(y=m.group(2)) if m and m.group(1) in SOURCES else None


def accept(name, data, pin):
    """(kept, message): the bytes are kept only when their fingerprint is the pin."""
    got = sha(data)
    return (got == pin), (f"{name}: fingerprint {got[:12]} matches its pin" if got == pin else f"{name}: REFUSED - fingerprint {got[:12]}, pinned {pin[:12]} (the source revised it)")


def self_test():
    data = b"season,week\n2024,15\n"; right, wrong = sha(data), sha(b"other")
    ok_right, _ = accept("t.csv", data, right); ok_wrong, msg = accept("t.csv", data, wrong)
    routed = url_of("pbp_2024.csv.gz") == BASE + "pbp/play_by_play_2024.csv.gz" and url_of("games.csv") is None and url_of("pbp_participation_2024.csv.gz") is None
    ok = ok_right and not ok_wrong and routed and len(COMMITTED) == 15
    print(f"self-test: matching bytes kept {ok_right} (want True) | differing bytes refused {not ok_wrong} (want True) | sources routed {routed} | committed files {len(COMMITTED)} (want 15) | {'PASS' if ok else 'FAIL, the fetch is blind'}")
    return ok


def main():
    pins = json.load(open(PINS))["pins"]; os.makedirs(RAW, exist_ok=True); bad, fetched, present = [], 0, 0
    for name, pin in sorted(pins.items()):
        path = os.path.join(RAW, name)
        if os.path.exists(path):
            ok, msg = accept(name, open(path, "rb").read(), pin); present += 1
            if not ok: bad.append(msg.replace("the source revised it", "the file on disk differs from its pin"))
            continue
        if name in COMMITTED: bad.append(f"{name}: missing - it is committed in data/raw, so the checkout is incomplete"); continue
        url = url_of(name)
        if url is None: bad.append(f"{name}: no public source registered"); continue
        print(f"  fetching {name} <- {url}", flush=True)
        data = urllib.request.urlopen(url, timeout=300).read(); ok, msg = accept(name, data, pin); print("   ", msg, flush=True)
        if ok: open(path + ".part", "wb").write(data); os.replace(path + ".part", path); fetched += 1
        else: bad.append(msg)
    for b in bad: print("  FAIL:", b)
    print(f"RAW FILES: {'PASS' if not bad else 'FAIL'} | pinned {len(pins)} | already present {present} | fetched {fetched} | failures {len(bad)}")
    return not bad


if __name__ == "__main__":
    if "--self-test" in sys.argv: sys.exit(0 if self_test() else 1)
    sys.exit(0 if main() else 1)
