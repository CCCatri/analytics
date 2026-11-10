"""ingest.py - source ingestion (Slate Kit module map: ingest).  Owns the on-disk layout, the information-time boundary FROZEN_THRU, the one fetcher of outside data,
and the raw manifest: nothing enters, changes or leaves data/ or sources/ without an explicit, verified acceptance.
Fetch sections - the information set (results through week N-1 + week N's price file):
  nflverse  seasons > FROZEN_THRU only: stats, pbp, snaps, injuries, weekly rosters, schedule -> data/_incoming, checked (same columns as the file it replaces, one season,
            weeks only growing), moved into data/ under facts' names only if every file passes
  dk        week N's DK DFS Classic price file -> sources/raw/dk_weekly/DK_{season}_w{week}.csv in DK DFS CSV layout (+ the raw draftables JSON beside it).
Opt-in sections - never an input to any law (the information-set check keeps every other module away from them):
  --odds-lines / --odds-props / --odds-history (The Odds API; ODDS_API_KEY from the environment only), --sources participation,ftn (completed seasons only).
Every new or changed raw file is listed by the raw manifest check and counts only after  python3 kit.py accept."""
import argparse, csv, glob, gzip, hashlib, json, math, os, re, shutil, statistics, sys, time, urllib.error, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
ROOT = Path(__file__).resolve().parent; DATA_DIR = ROOT / "data"; FACTS_DIR = ROOT / "facts"; PROJ_DIR = ROOT / "proj"; SOURCES_DIR = ROOT / "sources"
INC = DATA_DIR / "_incoming"; DKW = SOURCES_DIR / "raw/dk_weekly"; CACHE = SOURCES_DIR / "raw/odds_api/hist_cache"; ET = ZoneInfo("America/New_York")
RAW_MANIFEST = FACTS_DIR / "raw_manifest.json"; ARCHIVE_DIR = ROOT / "archive"; EVENT_LOG = PROJ_DIR / "events.jsonl"   # archive: every accepted raw version by content hash; events: what each command did
FROZEN_THRU = 2025     # every law fits on seasons <= this; later seasons are history only for an issue inside them
class Report:
    """One producer of a report file: each line printed as it is said, the whole report written once."""
    def __init__(self): self.lines = []
    def say(self, line_text=""): print(line_text, flush=True); self.lines.append(str(line_text))
    def write(self, path): open(path, "w").write("\n".join(self.lines) + "\n")

# ---------------- nflverse: results (history) ----------------
BASE = "https://github.com/nflverse/nflverse-data/releases/download/"
ASSETS = {"stats_{y}.csv.gz": "stats_player/stats_player_week_{y}.csv.gz", "pbp_{y}.csv.gz": "pbp/play_by_play_{y}.csv.gz",
          "snaps_{y}.csv.gz": "snap_counts/snap_counts_{y}.csv.gz", "injuries_{y}.csv": "injuries/injuries_{y}.csv",
          "rosters_{y}.csv.gz": "weekly_rosters/roster_weekly_{y}.csv.gz"}
def nflverse(y):
    if y <= FROZEN_THRU: print(f"nflverse: {y} <= FROZEN_THRU ({FROZEN_THRU}) - historical files are never re-fetched"); return False
    INC.mkdir(parents=True, exist_ok=True); bad = []
    def check(name, new):
        old_p = DATA_DIR / name; msg = f"{name}: rows {len(new)}"
        if "season" in new and set(new.season.dropna().unique()) != {y}: bad.append(f"{name}: seasons {sorted(new.season.dropna().unique())}")
        if old_p.exists():
            old = pd.read_csv(old_p, low_memory=False)
            if set(old.columns) != set(new.columns): bad.append(f"{name}: columns differ from the file it would replace")
            if "week" in old and "week" in new and not set(old.week.unique()) <= set(new.week.unique()): bad.append(f"{name}: weeks would shrink")
            msg += f" (was {len(old)}), weeks {sorted(old.week.unique()) if 'week' in old else '-'} -> {sorted(new.week.unique()) if 'week' in new else '-'}"
        print("  " + msg)
    for out, path in ASSETS.items():
        name = out.format(y=y); dst = INC / name
        urllib.request.urlretrieve(BASE + path.format(y=y), dst); check(name, pd.read_csv(dst, low_memory=False))
    fetch_name = f"injuries_{y}_fetched.csv"   # batch 72: the fetch time stamps an injury file that carries none (facts.game_status_as_of reads it)
    pd.DataFrame({"season": [y], "fetched_at": [datetime.now(timezone.utc).isoformat()]}).to_csv(INC / fetch_name, index=False); check(fetch_name, pd.read_csv(INC / fetch_name))
    g = INC / "games_all.csv"; urllib.request.urlretrieve(BASE + "schedules/games.csv", g)
    gy = pd.read_csv(g, low_memory=False); gy = gy[gy.season == y]; gname = f"games_{y}.csv.gz"; gy.to_csv(INC / gname, index=False); g.unlink()
    check(gname, gy)
    if bad: print("nflverse: NOT MOVED - files stay in data/_incoming:\n  " + "\n  ".join(bad)); return False
    for f in os.listdir(INC): shutil.move(str(INC / f), str(DATA_DIR / f))
    INC.rmdir(); print("nflverse: moved into data/"); return True

# ---------------- DK DFS: week N's price file ----------------
LOBBY = "https://www.draftkings.com/lobby/getcontests?sport=NFL"
DRAFTABLES = "https://api.draftkings.com/draftgroups/v1/draftgroups/{}/draftables"
COLS = ["Position", "Name + ID", "Name", "ID", "Roster Position", "Salary", "Game Info", "TeamAbbrev", "AvgPointsPerGame", "Status"]
def http(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}), timeout=30) as r: return r.read()
def price_rows(body):
    """DK DFS draftables JSON -> its CSV layout, one row per player (lowest draftableId among his roster-slot entries)."""
    by = {}
    for x in json.loads(body).get("draftables", []):
        if x["playerId"] not in by or x["draftableId"] < by[x["playerId"]]["draftableId"]: by[x["playerId"]] = x
    rows = []
    for x in by.values():
        c = x["competition"]; t = datetime.fromisoformat(c["startTime"][:19]).replace(tzinfo=timezone.utc).astimezone(ET)
        fp = pd.to_numeric(next((a["value"] for a in x.get("draftStatAttributes", []) if a.get("id") == 90), ""), errors="coerce"); fp = 0.0 if pd.isna(fp) else float(fp)   # DK DFS writes 0.0 when it has no average (the JSON holds a non-number or nothing)
        pos = x["position"]; tag = x.get("status") or ""
        rows.append({"Position": pos, "Name + ID": f'{x["displayName"]} ({x["draftableId"]})', "Name": x["displayName"], "ID": x["draftableId"],
                     "Roster Position": pos if pos in ("QB", "DST") else f"{pos}/FLEX", "Salary": x["salary"],
                     "Game Info": f'{c["name"].replace(" ", "")} {t.strftime("%m/%d/%Y %I:%M%p")} ET', "TeamAbbrev": x["teamAbbreviation"],
                     "AvgPointsPerGame": fp, "Status": "" if tag == "None" else tag})
    return pd.DataFrame(sorted(rows, key=lambda r: -r["Salary"]), columns=COLS)
def check_dk(csv_path, json_path):
    K = pd.read_csv(csv_path); R = price_rows(open(json_path, "rb").read())
    m = K.merge(R, on="ID", how="outer", suffixes=("_dk", "_ours"), indicator=True)
    print(f"check: DK DFS CSV {len(K)} rows, converted {len(R)} rows; only in CSV {int((m._merge == 'left_only').sum())}, only in conversion {int((m._merge == 'right_only').sum())}")
    m = m[m._merge == "both"]; bad = 0
    norm = lambda s, c: pd.to_numeric(s, errors="coerce").round(2).astype(str) if c in ("Salary", "AvgPointsPerGame") else s.fillna("").astype(str).str.strip()
    for c in [c for c in COLS if c != "ID"]:
        a, b = norm(m[c + "_dk"], c), norm(m[c + "_ours"], c); d = (a != b); bad += 0 if c == "Status" else int(d.sum())
        print(f"   {c:<17} differ {int(d.sum()):>4}" + ("  (injury tag: changes through the week, outside the information set - not counted)" if c == "Status" else "") + ("" if not d.any() else "   e.g. " + "; ".join(f"{x!r} vs {y!r}" for x, y in list(zip(a[d], b[d]))[:3])))
    ok = bad == 0 and len(K) == len(R) == len(m); print("DK CONVERSION EXACT" if ok else "DK CONVERSION DIFFERS"); return ok
def dk(season, week, group):
    groups = [g for g in json.loads(http(LOBBY)).get("DraftGroups", []) if g.get("Sport") == "NFL" and g.get("ContestTypeId") == 21]
    print("NFL Classic draft groups now in the lobby:")
    for g in sorted(groups, key=lambda g: str(g.get("StartDateEst"))): print(f"   {g['DraftGroupId']}  start {g.get('StartDateEst')}  games {g.get('GameCount')}  {g.get('ContestStartTimeSuffix') or ''}")
    if group is None: print("dk: no --dk-group given - no price file written"); return True
    body = http(DRAFTABLES.format(group)); R = price_rows(body)
    if R.empty: print(f"dk: draft group {group} has no salaried draftables yet - nothing written"); return False
    out = DKW / f"DK_{season}_w{week}.csv"; DKW.mkdir(parents=True, exist_ok=True)
    if out.exists():
        old = pd.read_csv(out)
        if set(zip(old.ID, old.Salary)) == set(zip(R.ID, R.Salary)): print(f"dk: {out.name} already holds these prices - unchanged"); return True
        print(f"dk: {out.name} exists with different prices - not overwritten (prices are fixed once released; move it aside by hand if deliberate)"); return False
    R.to_csv(out, index=False); (DKW / f"DK_{season}_w{week}_{group}.json").write_bytes(body)
    print(f"dk: wrote {out.name} ({len(R)} players, {R['Game Info'].str.split(' ').str[0].nunique()} games) and the raw JSON"); return True

# ---------------- The Odds API (opt-in; never a projection input) ----------------
HOST = "https://api.the-odds-api.com"; SPORT = "americanfootball_nfl"
GAME_MARKETS = ["h2h", "spreads", "totals"]
PROP_MARKETS = ["player_pass_yds", "player_pass_tds", "player_pass_interceptions", "player_rush_yds", "player_reception_yds", "player_receptions", "player_anytime_td"]
DKPTS = {"player_pass_yds": 0.04, "player_pass_tds": 4.0, "player_pass_interceptions": -1.0, "player_rush_yds": 0.1, "player_reception_yds": 0.1, "player_receptions": 1.0, "player_anytime_td": 6.0}
POISSON = {"player_pass_tds", "player_pass_interceptions"}
SEASONS = {2020: ("2020-09-10", "2021-01-03"), 2021: ("2021-09-09", "2022-01-09"), 2022: ("2022-09-08", "2023-01-08"),
           2023: ("2023-09-07", "2024-01-07"), 2024: ("2024-09-05", "2025-01-05"), 2025: ("2025-09-04", "2026-01-04")}
ABBR = {"Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL", "Buffalo Bills": "BUF", "Carolina Panthers": "CAR",
        "Chicago Bears": "CHI", "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL", "Denver Broncos": "DEN",
        "Detroit Lions": "DET", "Green Bay Packers": "GB", "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
        "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC", "Los Angeles Rams": "LAR", "Miami Dolphins": "MIA",
        "Minnesota Vikings": "MIN", "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG", "New York Jets": "NYJ",
        "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT", "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA",
        "Tampa Bay Buccaneers": "TB", "Tennessee Titans": "TEN", "Washington Commanders": "WAS", "Washington Football Team": "WAS"}
def team(name):
    if name not in ABBR: raise KeyError(f"team not in ABBR: {name!r}")
    return ABBR[name]
def ts(s): return datetime.fromisoformat(s.replace("Z", "+00:00"))
def iso(dt): return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
def oget(path, params, cache=False):
    key = os.environ.get("ODDS_API_KEY") or sys.exit("set ODDS_API_KEY first"); fn = None
    if cache:
        CACHE.mkdir(parents=True, exist_ok=True)
        fn = CACHE / (urllib.parse.quote(path + "?" + urllib.parse.urlencode(sorted(params.items())), safe="")[:200] + ".json")
        if fn.exists(): return json.loads(fn.read_text()), None                       # cached calls are free
    url = f"{HOST}{path}?{urllib.parse.urlencode(dict(params, apiKey=key))}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                body = json.loads(r.read())
                if fn: fn.write_text(json.dumps(body))
                time.sleep(0.4); return body, (r.headers.get("x-requests-last"), r.headers.get("x-requests-remaining"))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 * (attempt + 1)); continue
            if e.code in (404, 422): return ({"data": []} if cache else {}), None
            raise
        except (TimeoutError, urllib.error.URLError, ConnectionError):
            print(f"  network retry {attempt + 1}", flush=True); time.sleep(3)
    raise RuntimeError("API failed repeatedly: " + path)
def remaining():
    key = os.environ.get("ODDS_API_KEY") or sys.exit("set ODDS_API_KEY first")
    with urllib.request.urlopen(f"{HOST}/v4/sports/?apiKey={key}", timeout=20) as r: return r.headers.get("x-requests-remaining")
def prob_of(american): a = float(american); return 100 / (a + 100) if a > 0 else -a / (-a + 100)
def poisson_sf(lam, line): k = math.floor(line); return 1 - sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k + 1))
def solve_lambda(p_over, line):
    lo, hi = 1e-6, 15.0
    for _ in range(80):
        mid = (lo + hi) / 2; lo, hi = (mid, hi) if poisson_sf(mid, line) < p_over else (lo, mid)
    return (lo + hi) / 2
def game_consensus(ev):
    sp, tot, ml = defaultdict(list), [], defaultdict(list)
    for bk in ev.get("bookmakers", []):
        for m in bk.get("markets", []):
            for o in m.get("outcomes", []):
                if m["key"] == "spreads": sp[o["name"]].append(float(o["point"]))
                elif m["key"] == "totals" and o["name"] == "Over": tot.append(float(o["point"]))
                elif m["key"] == "h2h": ml[o["name"]].append(float(o["price"]))
    if not sp: return None
    med = {t: statistics.median(v) for t, v in sp.items()}; fav = min(med, key=med.get); dog = max(med, key=med.get)
    return dict(fav=team(fav), dog=team(dog), fav_spread_now=med[fav], total_now=statistics.median(tot) if tot else "",
                ml_fav=statistics.median(ml[fav]) if ml[fav] else "", ml_dog=statistics.median(ml[dog]) if ml[dog] else "", n_books=len(ev.get("bookmakers", [])))
def prop_consensus(ev):
    per = defaultdict(lambda: defaultdict(dict))
    for bk in ev.get("bookmakers", []):
        for m in bk.get("markets", []):
            if m["key"] not in DKPTS: continue
            for o in m.get("outcomes", []):
                if o.get("description") is None: continue
                per[(o["description"], m["key"])][bk["key"]][o["name"]] = (o.get("point"), o["price"])
    out = {}
    for (player, mk), books in per.items():
        lines, pov, est = [], [], []
        for sides in books.values():
            if mk == "player_anytime_td":
                if "Yes" in sides: p = prob_of(sides["Yes"][1]); pov.append(p); est.append(-math.log(max(1e-9, 1 - p)))
                continue
            if "Over" not in sides or "Under" not in sides: continue
            pt = float(sides["Over"][0]); io, iu = prob_of(sides["Over"][1]), prob_of(sides["Under"][1])
            p = io / (io + iu); lines.append(pt); pov.append(p); est.append(solve_lambda(p, pt) if mk in POISSON else pt)
        if not est: continue
        out[(player, mk)] = dict(player=player, market=mk, n_books=len(est), line_med=statistics.median(lines) if lines else "",
                                 p_over_med=round(statistics.median(pov), 4), mean_est=round(statistics.median(est), 4),
                                 method=("poisson_vig_in" if mk == "player_anytime_td" else "poisson_devig" if mk in POISSON else "median_line"))
    return out
def odds_live(season, week, label, days, props, dry, stop_below):
    now = datetime.now(timezone.utc); stamp = datetime.now().strftime("%Y%m%d_%H%M")
    events, cost = oget(f"/v4/sports/{SPORT}/events", {})
    events = sorted([e for e in events if now <= ts(e["commence_time"]) <= now + timedelta(days=days)], key=lambda e: e["commence_time"])
    for e in events: print(f"  {e['commence_time']}  {team(e['away_team'])} @ {team(e['home_team'])}")
    est = len(GAME_MARKETS) + (len(events) * len(PROP_MARKETS) if props else 0)
    print(f"odds: {len(events)} games; up to {est} credits" + ("" if not cost else f" (remaining {cost[1]})"))
    if dry or not events: return
    tag = f"{season}_w{week}_{label}_{stamp}"; jdir = DATA_DIR / "line_snapshots/raw_json" / stamp; jdir.mkdir(parents=True, exist_ok=True); (DATA_DIR / "prop_snapshots").mkdir(parents=True, exist_ok=True)
    raw = gzip.open(DATA_DIR / f"line_snapshots/{tag}_raw.csv.gz", "wt", newline=""); rw = csv.writer(raw)
    rw.writerow(["season", "week", "label", "snapshot_utc", "event_id", "commence_time", "home", "away", "bookmaker", "book_update", "market", "outcome", "description", "point", "price"])
    def dump(e, ev):
        for bk in ev.get("bookmakers", []):
            for m in bk.get("markets", []):
                for o in m.get("outcomes", []):
                    rw.writerow([season, week, label, now.isoformat(timespec="seconds"), e["id"], e["commence_time"], team(e["home_team"]), team(e["away_team"]),
                                 bk["key"], m.get("last_update", bk.get("last_update")), m["key"], o.get("name"), o.get("description"), o.get("point"), o.get("price")])
    bulk, cost = oget(f"/v4/sports/{SPORT}/odds", {"regions": "us", "markets": ",".join(GAME_MARKETS), "oddsFormat": "american", "eventIds": ",".join(e["id"] for e in events)})
    (jdir / "games_bulk.json").write_text(json.dumps(bulk)); by_id = {ev["id"]: ev for ev in (bulk or [])}; games, pr = [], {}
    for e in events:
        ev = by_id.get(e["id"], {}); dump(e, ev); g = game_consensus(ev)
        if g: games.append(dict(season=season, week=week, snapshot_local=datetime.now().strftime("%Y-%m-%d %H:%M"), source=f"odds_api {label}", commence_time=e["commence_time"], **g))
    print(f"odds: game lines {len(games)}/{len(events)}" + ("" if not cost else f", cost {cost[0]}, remaining {cost[1]}"), flush=True)
    for i, e in enumerate(events if props else []):
        ev, cost = oget(f"/v4/sports/{SPORT}/events/{e['id']}/odds", {"regions": "us", "markets": ",".join(PROP_MARKETS), "oddsFormat": "american"})
        (jdir / f"{e['id']}.json").write_text(json.dumps(ev)); dump(e, ev)
        for k, v in prop_consensus(ev).items(): pr[k] = dict(v, event_id=e["id"], game=f"{team(e['away_team'])}@{team(e['home_team'])}")
        print(f"[{i + 1}/{len(events)}] {team(e['away_team'])}@{team(e['home_team'])}: books {len(ev.get('bookmakers', []))}" + ("" if not cost else f", cost {cost[0]}, remaining {cost[1]}"), flush=True)
        if cost and cost[1] is not None and float(cost[1]) < stop_below: print("credit floor reached - stopping"); break
    raw.close()
    with open(DATA_DIR / f"line_snapshots/{tag}_games.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["season", "week", "snapshot_local", "source", "fav", "dog", "fav_spread_now", "fav_spread_open", "total_now", "total_open", "ml_fav", "ml_dog", "n_books", "commence_time"]); w.writeheader()
        for g in games: w.writerow(dict(g, fav_spread_open="", total_open=""))
    if props:
        with open(DATA_DIR / f"prop_snapshots/{tag}_props.csv", "w", newline="") as f:
            w = csv.DictWriter(f, ["game", "event_id", "player", "market", "n_books", "line_med", "p_over_med", "mean_est", "method"]); w.writeheader()
            for v in sorted(pr.values(), key=lambda v: (v["game"], v["player"], v["market"])): w.writerow(v)
        by = defaultdict(dict); gm = {}
        for v in pr.values(): by[v["player"]][v["market"]] = v["mean_est"]; gm[v["player"]] = v["game"]
        with open(DATA_DIR / f"prop_snapshots/{tag}_prop_pts.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["game", "player", *PROP_MARKETS, "dk_pts_props", "markets_present"])
            for p_ in sorted(by, key=lambda p_: (gm[p_], p_)):
                d = by[p_]; w.writerow([gm[p_], p_, *[d.get(m, "") for m in PROP_MARKETS], round(sum(DKPTS[m] * d[m] for m in d), 2), "|".join(m.replace("player_", "") for m in PROP_MARKETS if m in d)])
    print(f"odds: wrote {tag}: {len(games)} games, {len(pr)} player-markets")
def odds_history(seasons, clocks, mk, dry, stop_below):
    assert set(clocks) <= {"open", "pricing", "t2h"}, clocks
    if "t2h" in clocks: assert "pricing" in clocks, "t2h reads kickoff times from the pricing snapshot"
    def weeks(season):
        a, b = (datetime.fromisoformat(x).replace(tzinfo=timezone.utc) for x in SEASONS[season]); n, thu = 1, a
        while thu <= b: yield n, thu; n += 1; thu += timedelta(days=7)
    per = 10 * len(mk); nw = sum(1 for s in seasons for _ in weeks(s)); fixed = nw * per * sum(c in clocks for c in ("open", "pricing"))
    print(f"odds history: {nw} weeks; open/pricing: {fixed:,} credits; t2h ~{per} per distinct kickoff; cached calls free. Credits remaining: {remaining()}")
    if dry: return
    out = DATA_DIR / "line_history"; out.mkdir(parents=True, exist_ok=True); tag = f"clocks_{seasons[0]}_{seasons[-1]}"
    raw = gzip.open(out / f"{tag}_raw.csv.gz", "wt", newline=""); rw = csv.writer(raw)
    rw.writerow(["season", "week", "clock", "requested", "snapshot", "event_id", "commence_time", "home", "away", "bookmaker", "market_last_update", "market", "outcome", "point", "price"])
    agg = defaultdict(lambda: defaultdict(list)); meta = {}
    def pull(season, wk, clock, when, lo, hi, only=None):
        body, cost = oget(f"/v4/historical/sports/{SPORT}/odds", {"regions": "us", "markets": ",".join(mk), "oddsFormat": "american", "date": iso(when)}, cache=True); kept = []
        for ev in body.get("data", []):
            ct = ts(ev["commence_time"])
            if not (lo <= ct < hi) or (only is not None and ev["commence_time"] not in only) or ct <= when: continue
            kept.append(ev); k = (season, wk, clock, ev["id"]); meta[ev["id"]] = (ev["commence_time"], team(ev["home_team"]), team(ev["away_team"]))
            for bk in ev.get("bookmakers", []):
                for m in bk.get("markets", []):
                    for o in m.get("outcomes", []):
                        rw.writerow([season, wk, clock, iso(when), body.get("timestamp"), ev["id"], ev["commence_time"], team(ev["home_team"]), team(ev["away_team"]),
                                     bk["key"], m.get("last_update", bk.get("last_update")), m["key"], o.get("name"), o.get("point"), o.get("price")])
                        if m["key"] == "spreads" and o["name"] == ev["home_team"]: agg[k]["home_spread"].append(float(o["point"]))
                        if m["key"] == "totals" and o["name"] == "Over": agg[k]["total"].append(float(o["point"]))
                        if m["key"] == "h2h": agg[k]["ml_home" if o["name"] == ev["home_team"] else "ml_away"].append(float(o["price"]))
                agg[k]["books"].append(bk["key"])
        if cost:
            print(f"{season} w{wk:>2} {clock:<7} {iso(when)}: {len(kept)} games, cost {cost[0]}, remaining {cost[1]}", flush=True)
            if cost[1] is not None and float(cost[1]) < stop_below: raw.close(); sys.exit("credit floor reached - rerun later (cached calls are free)")
        return kept
    for s in seasons:
        for wk, thu in weeks(s):
            lo, hi = thu - timedelta(days=1), thu + timedelta(days=6)
            if "open" in clocks: pull(s, wk, "open", (thu - timedelta(days=3)).replace(hour=12), lo, hi)
            if "pricing" in clocks:
                evs = pull(s, wk, "pricing", (thu - timedelta(days=2)).replace(hour=16), lo, hi)
                if "t2h" in clocks:
                    for ct in sorted({e["commence_time"] for e in evs}): pull(s, wk, "t2h", ts(ct) - timedelta(hours=2), lo, hi, only={ct})
    raw.close()
    with open(out / f"{tag}_games.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["season", "week", "clock", "event_id", "commence_time", "home", "away", "home_spread", "total", "ml_home", "ml_away", "n_books"])
        for (s, wk, clock, eid), d in sorted(agg.items(), key=lambda x: (x[0][0], x[0][1], meta[x[0][3]][0], x[0][2])):
            med = lambda v: statistics.median(v) if v else ""
            w.writerow([s, wk, clock, eid, *meta[eid], med(d["home_spread"]), med(d["total"]), med(d["ml_home"]), med(d["ml_away"]), len(set(d["books"]))])
    print(f"odds history: wrote {out / (tag + '_games.csv')}: {len(agg)} game-clock rows")

# ---------------- nflverse source families (opt-in; completed seasons only; downloaded bytes kept) ----------------
SOURCES = {"participation": dict(path="pbp_participation/pbp_participation_{y}.csv", out="pbp_participation_{y}.csv.gz", first=2016, game="nflverse_game_id", play="play_id",
                                 need=["nflverse_game_id", "play_id", "offense_personnel", "defense_personnel", "defenders_in_box", "offense_players", "defense_players"]),
           "ftn": dict(path="ftn_charting/ftn_charting_{y}.csv", out="ftn_charting_{y}.csv.gz", first=2022, game="nflverse_game_id", play="nflverse_play_id",
                       need=["nflverse_game_id", "nflverse_play_id", "season", "week", "qb_location", "is_play_action", "is_qb_sneak", "n_defense_box"])}
def sources(families, seasons):
    """Source families for completed seasons (<= FROZEN_THRU): downloaded to data/_incoming, checked, the downloaded bytes gzipped unchanged and moved into data/ only if every
    file passes; a file already in data/ is never re-fetched.  Acquisition only - forecast eligibility: CHARTER "SOURCE FAMILIES - PARTICIPATION AND FTN - REGISTRATION"."""
    INC.mkdir(parents=True, exist_ok=True); bad, made = [], []
    for fam in families:
        if fam not in SOURCES: bad.append(f"unknown source family {fam!r}"); continue
        S = SOURCES[fam]
        for y in seasons:
            name = S["out"].format(y=y)
            if y > FROZEN_THRU: print(f"  {name}: season {y} > FROZEN_THRU - same-season sources need the availability-witness design; not fetched"); continue
            if y < S["first"]: print(f"  {name}: {fam} starts {S['first']} - not fetched"); continue
            if (DATA_DIR / name).exists(): print(f"  {name}: already in data/ - never re-fetched"); continue
            raw = INC / name[:-3]; urllib.request.urlretrieve(BASE + S["path"].format(y=y), raw)
            F = pd.read_csv(raw, low_memory=False); msg = f"  {name}: rows {len(F)}"; miss = [c for c in S["need"] if c not in F.columns]
            if len(F) == 0 or miss: bad.append(f"{name}: rows {len(F)}, missing columns {miss}")
            elif not F[S["game"]].astype(str).str.startswith(str(y)).all(): bad.append(f"{name}: game ids outside season {y}")
            else:
                pb = DATA_DIR / f"pbp_{y}.csv.gz"
                if pb.exists():
                    P = pd.read_csv(pb, usecols=["game_id", "play_id", "season_type", "play_type"], low_memory=False); P = P[(P.season_type == "REG") & P.play_type.isin(["pass", "run"])]
                    K = F[[S["game"], S["play"]]].rename(columns={S["game"]: "game_id", S["play"]: "play_id"}).drop_duplicates(); K["play_id"] = pd.to_numeric(K.play_id, errors="coerce")
                    j = P.merge(K.assign(hit=1), on=["game_id", "play_id"], how="left").hit.notna().mean(); msg += f", join to pbp pass / run plays {j:.4f}"
                    if j < 0.999: bad.append(f"{name}: join to pbp {j:.4f} < 0.999")
            with open(raw, "rb") as src, gzip.open(INC / name, "wb") as dst: shutil.copyfileobj(src, dst)
            raw.unlink(); made.append(name); print(msg)
    if bad: print("sources: NOT MOVED - files stay in data/_incoming:\n  " + "\n  ".join(bad)); return False
    for name in made: shutil.move(str(INC / name), str(DATA_DIR / name))
    if INC.exists() and not any(INC.iterdir()): INC.rmdir()
    print(f"sources: moved {len(made)} files into data/"); return True

# ---------------- the final corpus: the one historical fetch (CHARTER FINAL CORPUS, Oct 6 2026) ----------------
CORPUS_DIR = DATA_DIR / "corpus"
CORPUS_TIERS = {"deep_lockbox": tuple(range(1999, 2012)), "lockbox": (2012, 2013, 2014, 2015), "discovery": (2016, 2017, 2018, 2022)}   # every season the kit does not hold, by tier
SEALED_TIERS = ("deep_lockbox", "lockbox")   # never read except by a registered lockbox judgment; never in facts
def sealed_seasons(): return sorted(season for tier in SEALED_TIERS for season in CORPUS_TIERS[tier])
CORPUS_ATTEMPTS = 3   # downloads of one file before a truncated transfer stops the fetch
def corpus_intact(path):
    """A downloaded file is whole: a gzip file decompresses to its end-of-stream marker; a plain file is non-empty."""
    if not path.exists() or path.stat().st_size == 0: return False
    if path.suffix != ".gz": return True
    try:
        with gzip.open(path, "rb") as stream:
            while stream.read(1 << 22): pass
        return True
    except (EOFError, OSError): return False
def corpus_download(url, destination):
    """One corpus file, one encoding: "whole" when it is on disk whole (a whole file from an interrupted run is kept, not fetched again); "absent" when the release does
    not publish it (HTTP 404); "broken" when the release's own file arrives at its published length (Content-Length) and is still not whole - the release is broken, so
    the file is removed and the next encoding is tried.  A transfer shorter than its published length is fetched again, at most CORPUS_ATTEMPTS times, then the fetch
    stops with nothing moved; any other failure stops it."""
    if corpus_intact(destination): return "whole"
    for _ in range(CORPUS_ATTEMPTS):
        try: _, headers = urllib.request.urlretrieve(url, destination)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
            return "absent"
        if corpus_intact(destination): return "whole"
        published = headers.get("Content-Length")
        if published is not None and int(published) == destination.stat().st_size: destination.unlink(); return "broken"
    raise SystemExit(f"corpus: {url} arrived shorter than its published length {CORPUS_ATTEMPTS} times - stopped; nothing moved (data/corpus_incoming keeps every whole file for the next run)")
def corpus_fetch():
    """python3 kit.py fetch --corpus: the one historical fetch.  Every CORPUS_TIERS season: every ASSETS kind, the season's schedule rows, and each SOURCES family from its first
    season - into data/corpus_incoming/TIER/, checked (a season column holds only that season; a source family's game ids start with the season), then the
    folder becomes data/corpus/ only if every present file passes.  Each file keeps the kit's name; a kind published only as plain .csv is gzipped
    unchanged under that name.  A kind the release does not publish whole and non-empty for a season (HTTP 404, a broken file at its published length, or a header-only
    file, in every encoding) is measured absent with its reason, listed in
    data/corpus/absent.json and never retried once the corpus exists; an interrupted run resumes from data/corpus_incoming (whole files kept).  Refused once data/corpus exists: the corpus is fetched once and never extended; completed future seasons arrive by the
    weekly cycle."""
    if CORPUS_DIR.exists(): print("corpus: data/corpus exists - the final corpus is fetched once and never extended; nothing fetched"); return False
    incoming = DATA_DIR / "corpus_incoming"; incoming.mkdir(parents=True, exist_ok=True); bad, absent = [], []
    schedule_path = incoming / "games_all.csv"; urllib.request.urlretrieve(BASE + "schedules/games.csv", schedule_path); all_games = pd.read_csv(schedule_path, low_memory=False)
    for tier, seasons in CORPUS_TIERS.items():
        (incoming / tier).mkdir(exist_ok=True)
        for y in seasons:
            targets = [(out.format(y=y), path.format(y=y), "season") for out, path in ASSETS.items()] + [(S["out"].format(y=y), S["path"].format(y=y), S["game"]) for S in SOURCES.values() if y >= S["first"]]
            for name, path, season_column in targets:
                encodings = [path, path[:-3]] if path.endswith(".csv.gz") else [path]   # the release publishes some older seasons as plain .csv under the same name
                states = {}
                for encoding in encodings:   # the first whole encoding is the file
                    states[Path(encoding).name] = corpus_download(BASE + encoding, incoming / tier / Path(encoding).name)
                    if states[Path(encoding).name] == "whole": break
                fetched = [encoding for encoding in encodings if states.get(Path(encoding).name) == "whole"]
                if not fetched:
                    reason = ", ".join(f"{encoding_name} {state}" for encoding_name, state in states.items()); absent.append(f"{tier}/{name}: {reason}"); print(f"  {tier}/{name}: {reason} - absent"); continue
                destination = incoming / tier / Path(fetched[0]).name; gzip_after = name.endswith(".gz") and not destination.name.endswith(".gz")
                frame = pd.read_csv(destination, low_memory=False); line = f"  {tier}/{name}: rows {len(frame)}"
                if len(frame) == 0: destination.unlink(); reason = ", ".join(f"{encoding_name} {state}" for encoding_name, state in states.items()) + ", published empty (header only)"; absent.append(f"{tier}/{name}: {reason}"); print(f"  {tier}/{name}: {reason} - absent"); continue
                if season_column == "season" and "season" in frame and set(frame.season.dropna().unique()) != {y}: bad.append(f"{tier}/{name}: seasons {sorted(frame.season.dropna().unique())}")
                elif season_column != "season" and not frame[season_column].astype(str).str.startswith(str(y)).all(): bad.append(f"{tier}/{name}: game ids outside season {y}")
                if gzip_after:
                    with open(destination, "rb") as source, gzip.open(incoming / tier / name, "wb") as target: shutil.copyfileobj(source, target)
                    destination.unlink()
                elif destination.name != name: destination.rename(incoming / tier / name)
                print(line)
            season_games = all_games[all_games.season == y]; season_games.to_csv(incoming / tier / f"games_{y}.csv.gz", index=False); print(f"  {tier}/games_{y}.csv.gz: rows {len(season_games)}")
            if len(season_games) == 0: bad.append(f"{tier}/games_{y}.csv.gz: no rows")
    schedule_path.unlink()
    if bad: print("corpus: NOT MOVED - files stay in data/corpus_incoming:\n  " + "\n  ".join(bad)); return False
    json.dump(sorted(absent), open(incoming / "absent.json", "w"), indent=0); incoming.rename(CORPUS_DIR)
    print(f"corpus: data/corpus written - tiers {', '.join(f'{tier} {CORPUS_TIERS[tier][0]}-{CORPUS_TIERS[tier][-1]}' for tier in CORPUS_TIERS)}; kinds absent {len(absent)}"); return True

# ---------------- the fetch command ----------------
def fetch_command(argv):
    """One fetch per run: python3 kit.py fetch SEASON WEEK [--dk-group ID] [--no-nflverse] | --check-dk CSV JSON | --odds-history | --sources FAMILIES | --corpus (once ever)."""
    ap = argparse.ArgumentParser(description="the one fetcher: one fetch per run, then exit")
    ap.add_argument("season", type=int, nargs="?"); ap.add_argument("week", type=int, nargs="?")
    ap.add_argument("--no-nflverse", action="store_true"); ap.add_argument("--dk-group", type=int); ap.add_argument("--check-dk", nargs=2, metavar=("CSV", "JSON"))
    ap.add_argument("--odds-lines", action="store_true"); ap.add_argument("--odds-props", action="store_true"); ap.add_argument("--odds-history", action="store_true")
    ap.add_argument("--label", default="pricing"); ap.add_argument("--days", type=float, default=7); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stop-below", type=int, default=200); ap.add_argument("--seasons", default="2020,2021,2022,2023,2024,2025")
    ap.add_argument("--clocks", default="open,pricing,t2h"); ap.add_argument("--markets", default="spreads,totals")
    ap.add_argument("--sources", default=""); ap.add_argument("--source-seasons", default="2019,2020,2021,2023,2024,2025"); ap.add_argument("--corpus", action="store_true")
    a = ap.parse_args(argv)
    if a.check_dk: return 0 if check_dk(*a.check_dk) else 1
    if a.corpus: return 0 if corpus_fetch() else 1
    if a.season is None and not (a.odds_history or a.sources): ap.error("give season and week, or --check-dk, or --odds-history, or --sources")
    ok = True
    if a.season is not None:
        if a.week is None: ap.error("give both season and week")
        if not a.no_nflverse: ok = nflverse(a.season) and ok
        ok = dk(a.season, a.week, a.dk_group) and ok
        if a.odds_lines or a.odds_props: odds_live(a.season, a.week, a.label, a.days, a.odds_props, a.dry_run, a.stop_below)
    if a.odds_history: odds_history([int(x) for x in a.seasons.split(",")], a.clocks.split(","), a.markets.split(","), a.dry_run, a.stop_below)
    if a.sources: ok = sources(a.sources.split(","), [int(x) for x in a.source_seasons.split(",")]) and ok
    print("next: python3 kit.py guard (read the list of new raw files), then python3 kit.py accept"); return 0 if ok else 1

# ---------------- the raw manifest ----------------
def sha(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as file_handle:
        for block in iter(lambda: file_handle.read(1 << 20), b""): hasher.update(block)
    return hasher.hexdigest()
def raw_files():
    """Every raw file on disk (data/, sources/) with its SHA-256, keyed by its path relative to ROOT."""
    return {os.path.relpath(path, ROOT): sha(path) for folder in (DATA_DIR, SOURCES_DIR) for path in sorted(glob.glob(os.path.join(folder, "**", "*"), recursive=True)) if os.path.isfile(path) and not path.endswith(".DS_Store")}
def accept():
    """After verifying a deliberate change to raw data: every raw file now on disk is kept in archive/ under its SHA-256 (a copy - a hard link shares bytes with a file
    rewritten in place), the manifest accepts them, and the manifest itself is archived by its own hash - every accepted vintage stays reconstructible
    (CHARTER PROVENANCE ROOT, Oct 6 2026).  The changes against the previous manifest are printed; the event log records both manifests' hashes."""
    ARCHIVE_DIR.mkdir(exist_ok=True); current = raw_files(); previous = json.load(open(RAW_MANIFEST)) if RAW_MANIFEST.exists() else {}
    for relative_path, digest in current.items():
        if not (ARCHIVE_DIR / digest).exists(): shutil.copyfile(ROOT / relative_path, ARCHIVE_DIR / digest)
    for label, paths in (("added", sorted(set(current) - set(previous))), ("changed", sorted(path for path in current if path in previous and current[path] != previous[path])), ("removed", sorted(set(previous) - set(current)))):
        print(f"   {label} {len(paths)}" + (": " + ", ".join(paths) if paths else ""))
    json.dump(current, open(RAW_MANIFEST, "w"), indent=0); manifest_digest = sha(RAW_MANIFEST)
    if not (ARCHIVE_DIR / manifest_digest).exists(): shutil.copyfile(RAW_MANIFEST, ARCHIVE_DIR / manifest_digest)
    print(f"accepted: {len(current)} raw files written to {os.path.relpath(RAW_MANIFEST, ROOT)} (manifest {manifest_digest[:16]}, archived)"); return 0
def manifest_sha(): return sha(RAW_MANIFEST)
def record_event(event):
    """Append one command's record to proj/events.jsonl - written by the kit, never by hand."""
    with open(EVENT_LOG, "a") as log: log.write(json.dumps(event, sort_keys=True) + "\n")
def read_events():
    """Every recorded event, oldest first (an absent log is no events yet)."""
    if not EVENT_LOG.exists(): return []
    return [json.loads(line) for line in open(EVENT_LOG) if line.strip()]
def raw_manifest_check():
    """(passed, message): no raw file added, changed or removed since the accepted manifest."""
    if not RAW_MANIFEST.exists(): return False, "no raw manifest - verify the data, then run: python3 kit.py accept"
    current, accepted = raw_files(), json.load(open(RAW_MANIFEST))
    differences = [(label, paths) for label, paths in (("added", sorted(set(current) - set(accepted))), ("changed", sorted(path for path in current if path in accepted and current[path] != accepted[path])), ("removed", sorted(set(accepted) - set(current)))) if paths]
    if differences: return False, "; ".join(f"raw files {label} since the accepted manifest ({len(paths)}): " + ", ".join(paths[:6]) + (" ..." if len(paths) > 6 else "") for label, paths in differences)
    return True, f"raw data unchanged: {len(current)} files match the manifest"
RAW_READERS = {"ingest.py": ("data", "sources"), "facts.py": ("data", "sources/tidy", "sources/raw/dk_weekly")}   # facts reads the price file through ingest's DKW
def raw_reader_check(paths):
    """(passed, message): each raw source has one reader - a path literal under data/ or sources/ appears only in its reader."""
    pattern = re.compile(r"""["'](?:\./)?(data|sources)(/[^"'\s]*)?["']"""); stray = []
    for path in paths:
        hits = {match.group(1) + (match.group(2) or "") for match in pattern.finditer(open(path, errors="ignore").read())}
        stray += [f"{os.path.basename(path)}: {hit}" for hit in sorted(hits) if not any(hit.startswith(allowed) for allowed in RAW_READERS.get(os.path.basename(path), ()))]
    return (False, f"raw data read outside its reader: {stray[:5]}") if stray else (True, "every raw read sits in its one reader")
