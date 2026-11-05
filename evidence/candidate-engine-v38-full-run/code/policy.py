"""version 4 contract: RUBRIC.md section 9 as code. One name per quantity (M7, A15). Nothing here is read from version 3."""
import os

RAW_DIR = "/Users/cameroncatri/LocalWork/nfl/data/raw"
PINS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RAW_PINS.json")
RAW_FILE_COUNT = 45
# data_version := sha256 over the sorted "name:sha\n" lines of the 45 pins, full hex (RUBRIC section 9).
DATA_VERSION = "8d9f37846c0cc3bcdac6ea2f3082c1297cfe076306f4cffc34b8f20eb3e36107"
SEASONS = (2019, 2020, 2021, 2022, 2023, 2024, 2025)
HOLD = 2022                   # R10: held_out
assert HOLD == 2022


POLICY = {
    "holdout_season": 2022,   # R10: which season is held_out (identity)
    "k_se": 2.0,              # the one reading convention; printed beside every interval
    "unseal": None,           # X7: the event, executed once by the reviewer when its line prints
}
OWNER_KEYS = ("unseal",)

class INSUFFICIENT(Exception):
    """A quality_gate whose POLICY key is None (RUBRIC section 7), or a run that needs a number the files do not hold. Never caught and turned into PASS."""

def policy(key):
    if key not in POLICY:
        raise KeyError(f"POLICY has no key {key!r}")
    if key in OWNER_KEYS and POLICY[key] is None:
        raise INSUFFICIENT(f"POLICY {key} is None: reviewer event required (RUBRIC section 7)")
    return POLICY[key]

# "no price: <reason>" enum (section 0, Order 3). Fixed; a reason outside it is a DataGap.
NO_PRICE = ("not_forecastable", "not_pregame_knowable", "dependent", "unconserved_team_game",
            "below_baseline", "insufficient_ruling", "no_prior_finished_game", "population")

POSITIONS = ("QB", "RB", "WR", "TE")
STATS = ("targets", "receptions", "rec_yards", "rec_td", "carries", "rush_yards", "rush_td", "tds",
         "attempts", "completions", "pass_yards", "pass_td", "interceptions")
KIND = {"targets": ("targets", "receptions", "rec_yards", "rec_td"),
        "carries": ("carries", "rush_yards", "rush_td"),
        "attempts": ("attempts", "completions", "pass_yards", "pass_td", "interceptions"),
        "tds": ("tds",)}
COUNT_STATS = ("targets", "carries", "attempts")
CELLS = {"QB": ("attempts", "completions", "pass_yards", "pass_td", "interceptions", "carries", "rush_yards"),
         "RB": ("targets", "receptions", "rec_yards", "tds", "carries", "rush_yards"),
         "WR": ("targets", "receptions", "rec_yards", "tds", "carries", "rush_yards"),
         "TE": ("targets", "receptions", "rec_yards", "tds", "carries", "rush_yards")}

# official column map: stat -> the raw column names accepted; exactly one must exist in the file
OFFICIAL_COLUMNS = {
    "targets": ("targets",), "receptions": ("receptions",), "rec_yards": ("receiving_yards",),
    "rec_td": ("receiving_tds",), "carries": ("carries",), "rush_yards": ("rushing_yards",),
    "rush_td": ("rushing_tds",), "attempts": ("attempts", "passing_attempts"),
    "completions": ("completions", "passing_completions"), "pass_yards": ("passing_yards",),
    "pass_td": ("passing_tds",), "interceptions": ("interceptions", "passing_interceptions"),
}
# tds = rec_td + rush_td (nflverse definition); never read from a column
OFFICIAL_BASE = ("player_id", "position", "position_group", "season", "week", "season_type",
                 "game_id", "team", "opponent_team")
OFFICIAL_BASE_TYPES = {"player_id": ("str", False), "position": ("str", True), "position_group": ("str", True),
                       "season": ("int", False), "week": ("int", False), "season_type": ("str", False),
                       "game_id": ("str", False), "team": ("str", False), "opponent_team": ("str", True)}
# a contradiction in the record raises DataGap (R2): (lesser, greater)
# (rec_td, receptions) is not an identity: a lateral TD credits the scorer a receiving TD and no reception
# (2024_03_DET_ARI 00-0039139, 2024_13_SF_BUF 00-0034857; ruled 2026-10-25 from the pbp lateral read).
OFFICIAL_CONTRADICTIONS = (("completions", "attempts"), ("interceptions", "attempts"), ("pass_td", "completions"),
                           ("receptions", "targets"), ("rush_td", "carries"))

TEAM_ALIASES = {"LAR": "LA", "WSH": "WAS", "JAC": "JAX", "SD": "LAC", "STL": "LA", "OAK": "LV",
                "ARZ": "ARI", "BLT": "BAL", "CLV": "CLE", "HST": "HOU"}

BETTING_EXCLUDED = ("spread_line", "total_line", "away_moneyline", "home_moneyline", "away_spread_odds",
                    "home_spread_odds", "under_odds", "over_odds")

SCHEDULE_FILE = "games.csv"
SCHEDULE_COLUMNS = ("game_id", "season", "game_type", "week", "gameday", "gametime", "away_team", "home_team",
                    "away_score", "home_score", "roof", "surface", "away_rest", "home_rest", "div_game")
SCHEDULE_TYPES = {"game_id": ("str", False), "season": ("int", False), "game_type": ("str", False),
                  "week": ("int", False), "gameday": ("str", False), "gametime": ("str", True),
                  "away_team": ("str", False), "home_team": ("str", False), "away_score": ("int", True),
                  "home_score": ("int", True), "roof": ("str", True), "surface": ("str", True),
                  "away_rest": ("int", False), "home_rest": ("int", False), "div_game": ("int", False)}

PBP_FILE = "pbp_{season}.csv.gz"
PBP_CACHE_COLUMNS = ("air_yards",)
PARTICIPATION_FILE = "pbp_participation_{season}.csv.gz"
ROSTER_FILE = "rosters_{season}.csv.gz"
SNAPS_FILE = "snaps_{season}.csv.gz"
STATS_FILE = "stats_{season}.csv.gz"
INJURIES_FILE = "injuries_{season}.csv"
PLAYERS_FILE, PLAYERIDS_FILE = "players.csv", "db_playerids.csv"

CALL_KINDS = ("pass", "sack", "scramble", "run", "kneel", "spike")
DROPBACK = ("pass", "sack", "scramble", "spike")
CARRY_KINDS = ("run", "scramble", "kneel")
ATTEMPT_KINDS = ("pass", "spike")
KIND_NEEDS = {"pass": ("passer", "complete", "interception", "pass_td", "yards", "yardline", "down", "ydstogo"),
              "sack": ("passer", "yards", "yardline", "down", "ydstogo"),
              "scramble": ("rusher", "yards", "rush_td", "yardline", "down", "ydstogo"),
              "run": ("rusher", "yards", "rush_td", "yardline", "down", "ydstogo"),
              "kneel": ("rusher", "yards", "yardline", "down", "ydstogo"),
              "spike": ("passer", "yardline", "down", "ydstogo")}

POSITION_GROUP = {"QB": "QB", "RB": "RB", "HB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
                  "T": "OL", "G": "OL", "C": "OL", "OT": "OL", "OG": "OL", "OL": "OL", "LS": "OL"}
def position_group(pos):
    return POSITION_GROUP.get(pos, "OTHER")
