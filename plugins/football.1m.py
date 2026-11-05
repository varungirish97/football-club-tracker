#!/usr/bin/env python3
# <swiftbar.title>Football Club Tracker</swiftbar.title>
# <swiftbar.desc>Your club's league position, next fixtures and live matchday scores in the macOS menu bar.</swiftbar.desc>
# <swiftbar.author>Varun Girish</swiftbar.author>
# <swiftbar.dependencies>python3</swiftbar.dependencies>
#
# SwiftBar runs this every minute (the "1m" in the filename), but it only goes
# online every 10 minutes, or every 2 minutes around kickoff. Otherwise it
# redraws from the copy saved in .cache.json.
# First printed line = menu bar text; lines after "---" = the dropdown.
# A line starting with "--" is a submenu of the line above it.
# Uses only the Python standard library, so there is nothing to pip install.

import base64
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

PLUGIN = os.path.realpath(__file__)
PLUGIN_ID = os.path.basename(PLUGIN)          # how SwiftBar identifies this plugin
ROOT = os.path.dirname(os.path.dirname(PLUGIN))
CONFIG_FILE = os.path.join(ROOT, "config.json")
CACHE_FILE = os.path.join(ROOT, ".cache.json")
CREST_DIR = os.path.join(ROOT, ".crests")
SETUP = os.path.join(ROOT, "setup.py")

# Default: the project's shared server, which holds an API key and caches
# responses. With your own key in config.json, talk to football-data.org directly.
SHARED_SERVER = "https://football-proxy.football-proxy.workers.dev/v4"
DIRECT_API = "https://api.football-data.org/v4"

PAGE = 4                 # teams per level of the table menu
NEXT_FIXTURES = 2        # upcoming matches shown
NORMAL_REFRESH = 10 * 60 # seconds between downloads on a normal day
MATCH_REFRESH = 2 * 60   # ...and around kickoff / during a match
LIVE = {"IN_PLAY", "PAUSED"}
UPCOMING = {"SCHEDULED", "TIMED"}

# Colours as "light-mode,dark-mode" pairs
DEFAULT_CLUB_COLOUR = "#DB0007,#FF4D4D"
GREEN = "#1E8E3E,#5DD879"
BLUE = "#1A6FD1,#6AA9FF"
ORANGE = "#C26A00,#FFA94D"
GREY = "#6E6E73,#A1A1A6"

# Short labels for competitions; anything not listed falls back to its code
COMP_LABELS = {
    "PL": "PL", "ELC": "Champ", "FAC": "FA Cup", "EFL": "EFL Cup",
    "CL": "UCL", "EL": "UEL", "UCL": "UECL", "CLI": "Libertadores",
    "PD": "La Liga", "CDR": "Copa", "SA": "Serie A", "CIT": "Coppa",
    "BL1": "Bundesliga", "DFB": "DFB-Pokal", "FL1": "Ligue 1", "CDF": "CdF",
    "DED": "Eredivisie", "PPL": "Liga PT", "BSA": "Brasileirão",
    "EC": "Euro", "WC": "World Cup",
}
RESULT_DOT = {"W": "🟢", "D": "⚪", "L": "🔴"}
RESULT_WORD = {"W": "Win ✅", "D": "Draw 🤝", "L": "Defeat ❌"}


# ---------- network ----------

def ssl_context():
    """Python from python.org ships without root certificates; macOS keeps a CA
    bundle at /etc/ssl/cert.pem. Certificates are still verified."""
    ctx = ssl.create_default_context()
    if os.path.exists("/etc/ssl/cert.pem"):
        ctx.load_verify_locations("/etc/ssl/cert.pem")
    return ctx


SSL_CTX = ssl_context()


def http_get(url, token=None):
    headers = {"User-Agent": "football-menubar"}
    if token:
        headers["X-Auth-Token"] = token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as r:
        return r.read()


def api(path, cfg):
    token = cfg.get("token")
    base = DIRECT_API if token else cfg.get("server", SHARED_SERVER)
    return json.loads(http_get(f"{base}{path}", token))


def crest(url, size):
    """Download a badge once, shrink it with macOS's `sips`, cache it, and return
    it base64-encoded for SwiftBar's image= parameter. None if anything fails."""
    try:
        if not url or not url.endswith(".png"):
            return None
        os.makedirs(CREST_DIR, exist_ok=True)
        name = os.path.basename(url)[:-4]
        small = os.path.join(CREST_DIR, f"{name}_{size}.png")
        if not os.path.exists(small):
            raw = os.path.join(CREST_DIR, f"{name}.png")
            if not os.path.exists(raw):
                with open(raw, "wb") as f:
                    f.write(http_get(url))
            subprocess.run(["sips", "-Z", str(size), raw, "--out", small],
                           check=True, capture_output=True)
        with open(small, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


# ---------- small helpers ----------

def nbsp(text):
    # SwiftBar trims leading spaces; non-breaking spaces keep columns aligned.
    return text.replace(" ", " ")


def style(color=None, image=None, mono=True):
    s = "|"
    if mono:
        s += " font=Menlo size=12"
    if color:
        s += f" color={color}"
    if image:
        s += f" image={image}"
    return s


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def short(team):
    return team.get("shortName") or team.get("name") or "?"


def tla(team):
    return team.get("tla") or short(team)[:3].upper()


def kickoff(m):
    return datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))


def comp_label(m):
    c = m.get("competition", {})
    return COMP_LABELS.get(c.get("code"), c.get("code") or c.get("name", "")[:10])


def uses_24h_clock(cfg):
    """Follow the Mac's own clock setting unless config.json says otherwise."""
    if cfg.get("clock") in ("12", "24"):
        return cfg["clock"] == "24"

    def read(key):
        r = subprocess.run(["defaults", "read", "-g", key], capture_output=True, text=True)
        return r.stdout.strip()

    try:
        if read("AppleICUForce24HourTime") == "1":
            return True
        if read("AppleICUForce12HourTime") == "1":
            return False
        locale = read("AppleLocale")
        return not locale.split("@")[0].endswith(("_US", "_CA", "_AU", "_NZ", "_IN", "_PH"))
    except Exception:
        return False


def clock(dt, h24):
    return f"{dt:%H:%M}" if h24 else f"{dt:%-I:%M %p}"


def result(m, team_id):
    h, a = m["score"]["fullTime"]["home"], m["score"]["fullTime"]["away"]
    us, them = (h, a) if m["homeTeam"]["id"] == team_id else (a, h)
    return "W" if us > them else "D" if us == them else "L"


def score_line(m):
    h, a = m["score"]["fullTime"]["home"], m["score"]["fullTime"]["away"]
    h = 0 if h is None else h
    a = 0 if a is None else a
    return f"{tla(m['homeTeam'])} {h}–{a} {tla(m['awayTeam'])}"


def opponent(m, team_id):
    home = m["homeTeam"]["id"] == team_id
    return ("vs" if home else "@"), (m["awayTeam"] if home else m["homeTeam"])


# ---------- cache, refresh timing and notifications ----------

def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def save_cache(cache):
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f)
    os.replace(tmp, CACHE_FILE)   # atomic: a half-written cache is never read


def match_window(matches, now):
    """True around kickoff and during a match, when we refresh more often."""
    for m in matches:
        if m["status"] in LIVE:
            return True
        if m["status"] in UPCOMING:
            k = kickoff(m)
            if k - timedelta(minutes=15) <= now <= k + timedelta(minutes=150):
                return True
    return False


def notify(title, subtitle, body):
    q = urllib.parse.urlencode({"plugin": PLUGIN_ID, "title": title,
                                "subtitle": subtitle, "body": body},
                               quote_via=urllib.parse.quote)
    subprocess.run(["open", "-g", f"swiftbar://notify?{q}"], capture_output=True)


def full_time_alerts(cache, cfg, now):
    """Notify once per newly finished match. On the very first run, just
    remember the matches that are already over, so nothing old pops up."""
    finished = [m for m in cache["matches"] if m["status"] == "FINISHED"]
    if "notified" not in cache:
        cache["notified"] = [m["id"] for m in finished]
        return
    seen = set(cache["notified"])
    for m in finished:
        if m["id"] in seen:
            continue
        seen.add(m["id"])
        if now - kickoff(m) > timedelta(hours=24) or not cfg.get("notifications", True):
            continue
        h, a = m["score"]["fullTime"]["home"], m["score"]["fullTime"]["away"]
        notify(f"{short(m['homeTeam'])} {h}–{a} {short(m['awayTeam'])}",
               f"Full time · {comp_label(m)}",
               RESULT_WORD[result(m, cfg["team_id"])])
    cache["notified"] = sorted(seen)


def get_data(cfg, force):
    """Return (cache, error). Uses the saved copy while it's fresh, downloads
    when it's due, and falls back to the saved copy if the download fails."""
    now = datetime.now(timezone.utc)
    cache = load_json(CACHE_FILE, {})
    if cache.get("team_id") != cfg["team_id"] or cache.get("league") != cfg["league"]:
        cache = {}          # club changed: start fresh
    age = time.time() - cache.get("fetched_at", 0)
    due = MATCH_REFRESH if match_window(cache.get("matches", []), now) else NORMAL_REFRESH
    if cache and not force and age < due:
        return cache, None
    try:
        standings = api(f"/competitions/{cfg['league']}/standings", cfg)
        matches = api(f"/teams/{cfg['team_id']}/matches", cfg)["matches"]
    except Exception as e:
        if cache:
            return cache, e
        raise
    cache.update(fetched_at=time.time(), team_id=cfg["team_id"], league=cfg["league"],
                 standings=standings, matches=matches)
    full_time_alerts(cache, cfg, now)
    save_cache(cache)
    return cache, None


# ---------- what the menu shows ----------

def menu_bar_text(cfg, mine, matches, now, h24):
    team_id = cfg["team_id"]
    live = next((m for m in matches if m["status"] in LIVE), None)
    if live:
        tag = "HT" if live["status"] == "PAUSED" else "●"
        return f"{tag} {score_line(live)}"
    finished = [m for m in matches if m["status"] == "FINISHED"]
    if finished and now - kickoff(finished[-1]) < timedelta(hours=6):
        return f"FT {score_line(finished[-1])}"
    nxt = next((m for m in matches if m["status"] in UPCOMING), None)
    if nxt:
        k = kickoff(nxt).astimezone()
        if k.date() == datetime.now().astimezone().date():
            side, opp = opponent(nxt, team_id)
            return f"{side} {tla(opp)} · {clock(k, h24)}"
    if mine:
        stats = f"{ordinal(mine['position'])} · {mine['points']}"
        return stats if cfg.get("compact", True) else f"{cfg.get('tla', '')} {stats} pts"
    return cfg.get("tla", "⚽")


def row_colour(r, n_teams, cfg):
    if r["team"]["id"] == cfg["team_id"]:
        return cfg["colour"]
    pos = r["position"]
    if pos <= 4:
        return GREEN
    if pos <= 6:
        return BLUE
    if pos > n_teams - 3:
        return ORANGE
    return None


def row_line(r):
    gd = f"{r['goalDifference']:+d}"
    return nbsp(f"{r['position']:>2}  {short(r['team'])[:15]:<16}"
                f"{r['playedGames']:>2}  {gd:>4}  {r['points']:>3}")


def print_form(matches, cfg):
    last5 = [m for m in matches if m["status"] == "FINISHED"][-5:]
    if not last5:
        return False
    dots = " ".join(RESULT_DOT[result(m, cfg["team_id"])] for m in last5)
    # Hovering shows the actual scores, newest last
    tip = "  ·  ".join(f"{result(m, cfg['team_id'])} {score_line(m)}" for m in last5)
    print(f'Form   {dots} | tooltip="{tip}"')
    return True


def print_table(table, emblem, cfg):
    n = len(table)
    print(nbsp(f"{'#':>2}  {'Team':<16}{'P':>2}  {'GD':>4}  {'Pts':>3}") + " "
          f"{style(GREY, crest(emblem, 16))}")
    for start in range(0, n, PAGE):
        depth = start // PAGE
        prefix = "--" * depth
        if depth > 0:
            end = min(start + PAGE, n)
            print(f"{'--' * (depth - 1)}Show {start + 1}–{end} ▸ {style(GREY)}")
        for r in table[start:start + PAGE]:
            badge = crest(r["team"].get("crest"), 16)
            print(f"{prefix}{row_line(r)} {style(row_colour(r, n, cfg), badge)}")
    mine = next((r for r in table if r["team"]["id"] == cfg["team_id"]), None)
    if mine and mine["position"] > PAGE:
        print(f"{nbsp('  …')} {style(GREY)}")
        print(f"{row_line(mine)} {style(cfg['colour'], crest(mine['team'].get('crest'), 16))}")


def print_fixtures(matches, cfg, h24):
    team_id = cfg["team_id"]
    live = [m for m in matches if m["status"] in LIVE]
    upcoming = [m for m in matches if m["status"] in UPCOMING][:NEXT_FIXTURES]
    print(f"Next up | color={cfg['colour']}")
    for m in live:
        tag = "Half time" if m["status"] == "PAUSED" else "● LIVE"
        print(nbsp(f"{tag:<19}  {score_line(m):<20}") + f"{comp_label(m)} {style(GREEN)}")
    if not live and not upcoming:
        print(f"No fixtures scheduled {style(GREY)}")
    for m in upcoming:
        k = kickoff(m).astimezone()
        side, opp = opponent(m, team_id)
        when = f"{k:%a %b %d} {clock(k, h24):>8}"
        colour = None if m["competition"].get("code") == cfg["league"] else BLUE
        print(nbsp(f"{when}  {side:<2} {short(opp):<16}") + f"{comp_label(m)} {style(colour)}")


def main():
    force = "--force" in sys.argv[1:]
    if not os.path.exists(CONFIG_FILE):
        print("⚽ Set up")
        print("---")
        print("Pick your club to get started")
        print(f'Run setup… | bash="{SETUP}" terminal=true')
        return

    cfg = load_json(CONFIG_FILE, {})
    cfg.setdefault("colour", DEFAULT_CLUB_COLOUR)
    cache, error = get_data(cfg, force)
    if force:
        return  # the Refresh item runs us once with --force, then SwiftBar redraws

    table = cache["standings"]["standings"][0]["table"]
    league_name = cache["standings"]["competition"]["name"]
    emblem = cache["standings"]["competition"].get("emblem")
    matches = cache["matches"]
    now = datetime.now(timezone.utc)
    h24 = uses_24h_clock(cfg)

    mine = next((r for r in table if r["team"]["id"] == cfg["team_id"]), None)
    badge = crest(cfg.get("crest") or (mine and mine["team"].get("crest")), 18)
    bar = menu_bar_text(cfg, mine, matches, now, h24)
    print(f"{bar} | image={badge}" if badge else bar)
    print("---")

    if print_form(matches, cfg):
        print("---")
    print(f"{league_name} | color={cfg['colour']}")
    print_table(table, emblem, cfg)
    print("---")
    print_fixtures(matches, cfg, h24)
    print("---")
    if error:
        updated = datetime.fromtimestamp(cache["fetched_at"]).astimezone()
        print(f"⚠ Offline · showing data from {clock(updated, h24)} {style(ORANGE, mono=False)}")
    print(f'Refresh | bash="{PLUGIN}" param1=--force terminal=false refresh=true')
    print(f'Change club… | bash="{SETUP}" terminal=true')


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("⚽ ⚠")
        print("---")
        print(f"Couldn't load data: {e}")
        print("Refresh | refresh=true")
        print(f'Run setup again… | bash="{SETUP}" terminal=true')
