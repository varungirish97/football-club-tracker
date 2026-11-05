#!/usr/bin/env python3
# <swiftbar.title>Football Club Tracker</swiftbar.title>
# <swiftbar.desc>Your club's league position, fixtures and results in the macOS menu bar.</swiftbar.desc>
# <swiftbar.dependencies>python3</swiftbar.dependencies>
#
# SwiftBar runs this every 10 minutes (the "10m" in the filename).
# First printed line = menu bar text; lines after "---" = the dropdown.
# A line starting with "--" is a submenu of the line above it ("----" = two levels deep).
# Uses only the Python standard library, so there is nothing to pip install.

import base64
import json
import os
import ssl
import subprocess
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
CONFIG_FILE = os.path.join(ROOT, "config.json")
CREST_DIR = os.path.join(ROOT, ".crests")
SETUP = os.path.join(ROOT, "setup.py")
# Default: the project's shared server, which holds an API key and caches
# responses, so users don't need a key. With your own key in config.json the
# plugin talks to football-data.org directly instead.
SHARED_SERVER = "https://football-proxy.football-proxy.workers.dev/v4"
DIRECT_API = "https://api.football-data.org/v4"
PAGE = 4  # teams shown per menu level

# Colours as "light-mode,dark-mode" pairs
DEFAULT_CLUB_COLOUR = "#DB0007,#FF4D4D"
WIN     = "#1E8E3E,#5DD879"
EUROPE  = "#1A6FD1,#6AA9FF"
RELEG   = "#C26A00,#FFA94D"
GREY    = "#6E6E73,#A1A1A6"
LOSS    = "#DB0007,#FF4D4D"
RESULT_COLOUR = {"W": WIN, "D": GREY, "L": LOSS}


def ssl_context():
    """Python from python.org ships without root certificates, so HTTPS fails with
    CERTIFICATE_VERIFY_FAILED. macOS keeps a CA bundle at /etc/ssl/cert.pem: load
    it too. Certificates are still verified; we just tell Python where they are."""
    ctx = ssl.create_default_context()
    if os.path.exists("/etc/ssl/cert.pem"):
        ctx.load_verify_locations("/etc/ssl/cert.pem")
    return ctx


SSL_CTX = ssl_context()


# ---------- helpers ----------

def http_get(url, token=None):
    headers = {"User-Agent": "football-menubar"}
    if token:
        headers["X-Auth-Token"] = token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=10, context=SSL_CTX) as r:
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
                    f.write(http_get(url))  # crest CDN, not the rate-limited API
            subprocess.run(["sips", "-Z", str(size), raw, "--out", small],
                           check=True, capture_output=True)
        with open(small, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


def nbsp(text):
    # SwiftBar trims leading spaces, which breaks column alignment;
    # non-breaking spaces are kept and are the same width in Menlo.
    return text.replace(" ", " ")


def style(color=None, image=None):
    s = "| font=Menlo size=12"
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


# ---------- sections ----------

def row_colour(r, n_teams, cfg):
    if r["team"]["id"] == cfg["team_id"]:
        return cfg["colour"]
    pos = r["position"]
    if pos <= 4:
        return WIN
    if pos <= 6:
        return EUROPE
    if pos > n_teams - 3:
        return RELEG
    return None


def row_line(r):
    gd = f"{r['goalDifference']:+d}"
    return nbsp(f"{r['position']:>2}  {short(r['team'])[:15]:<16}"
                f"{r['playedGames']:>2}  {gd:>4}  {r['points']:>3}")


def print_table(table, emblem, cfg):
    n = len(table)
    print(nbsp(f"{'#':>2}  {'Team':<16}{'P':>2}  {'GD':>4}  {'Pts':>3}") + " "
          f"{style(GREY, crest(emblem, 16))}")
    # Top 4 at the top level, then each further block of 4 one submenu deeper.
    for start in range(0, n, PAGE):
        depth = start // PAGE
        prefix = "--" * depth
        if depth > 0:
            end = min(start + PAGE, n)
            print(f"{'--' * (depth - 1)}Show {start + 1}–{end} ▸ {style(GREY)}")
        for r in table[start:start + PAGE]:
            badge = crest(r["team"].get("crest"), 16)
            print(f"{prefix}{row_line(r)} {style(row_colour(r, n, cfg), badge)}")
    # If your club is outside the top 4, also pin its row up top
    mine = next((r for r in table if r["team"]["id"] == cfg["team_id"]), None)
    if mine and mine["position"] > PAGE:
        print(f"{nbsp('  …')} {style(GREY)}")
        print(f"{row_line(mine)} {style(cfg['colour'], crest(mine['team'].get('crest'), 16))}")


def print_fixtures(matches, cfg):
    upcoming = [m for m in matches if m["status"] in ("SCHEDULED", "TIMED")][:5]
    print(f"Next fixtures | color={cfg['colour']}")
    if not upcoming:
        print(f"No fixtures scheduled {style(GREY)}")
    for m in upcoming:
        # astimezone() with no argument = this Mac's own time zone
        kick = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).astimezone()
        teams = f"{short(m['homeTeam'])} vs {short(m['awayTeam'])}"
        comp = m["competition"]
        colour = None if comp.get("code") == cfg["league"] else EUROPE
        print(nbsp(f"{kick:%a %b %d %H:%M}  {teams:<26}") + f"{comp['name']} {style(colour)}")


def print_results(matches, cfg):
    finished = [m for m in matches if m["status"] == "FINISHED"][-5:][::-1]
    print(f"Last results | color={cfg['colour']}")
    if not finished:
        print(f"No results yet {style(GREY)}")
    for m in finished:
        h, a = m["score"]["fullTime"]["home"], m["score"]["fullTime"]["away"]
        us, them = (h, a) if m["homeTeam"]["id"] == cfg["team_id"] else (a, h)
        res = "W" if us > them else "D" if us == them else "L"
        line = f"{short(m['homeTeam'])} {h}-{a} {short(m['awayTeam'])}"
        print(nbsp(f"{res}  {line:<30}") + f"{m['competition']['name']} {style(RESULT_COLOUR[res])}")


def load_config():
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    cfg.setdefault("colour", DEFAULT_CLUB_COLOUR)
    return cfg


def main():
    if not os.path.exists(CONFIG_FILE):
        print("⚽ Set up")
        print("---")
        print("Pick your club to get started")
        print(f'Run setup… | bash="{SETUP}" terminal=true')
        return

    cfg = load_config()
    standings = api(f"/competitions/{cfg['league']}/standings", cfg)
    table = standings["standings"][0]["table"]
    league_name = standings["competition"]["name"]
    emblem = standings["competition"].get("emblem")
    matches = api(f"/teams/{cfg['team_id']}/matches", cfg)["matches"]

    # --- menu bar line ---
    mine = next((r for r in table if r["team"]["id"] == cfg["team_id"]), None)
    # Keep the menu bar text short: on MacBooks with a notch, macOS silently hides
    # status items that don't fit. With a crest, the club name is redundant.
    label = cfg.get("tla") or cfg.get("team_name", "⚽")
    badge = crest(cfg.get("crest") or (mine and mine["team"].get("crest")), 18)
    if mine:
        stats = f"{ordinal(mine['position'])} · {mine['points']}"
        bar = stats if (badge and cfg.get("compact", True)) else f"{label} {stats} pts"
    else:
        bar = label
    print(f"{bar} | image={badge}" if badge else bar)
    print("---")

    print(f"{league_name} | color={cfg['colour']}")
    print_table(table, emblem, cfg)
    print("---")
    print_fixtures(matches, cfg)
    print("---")
    print_results(matches, cfg)
    print("---")
    print("Refresh | refresh=true")
    print(f'Change club… | bash="{SETUP}" terminal=true')


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("⚽ ⚠")
        print("---")
        print(f"Error: {e}")
        print("Refresh | refresh=true")
        print(f'Run setup again… | bash="{SETUP}" terminal=true')
