#!/usr/bin/env python3
"""One-time setup for the Football Club Tracker.

Asks for your club (and optionally your own football-data.org token), then writes config.json.
Run it again any time to change club:   ./setup.py
"""

import json
import os
import ssl
import stat
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(ROOT, "config.json")
PLUGIN = os.path.join(ROOT, "plugins", "football.1m.py")
SHARED_SERVER = "https://football-proxy.football-proxy.workers.dev/v4"
DIRECT_API = "https://api.football-data.org/v4"
# Competitions the shared server serves (football-data.org's free plan)
FREE = {"PL", "ELC", "PD", "SA", "BL1", "FL1", "DED", "PPL", "BSA", "CL", "EC", "WC"}
DEFAULT_COLOUR = "#DB0007,#FF4D4D"


def ssl_context():
    """Python from python.org ships without root certificates, so HTTPS fails with
    CERTIFICATE_VERIFY_FAILED. macOS keeps a CA bundle at /etc/ssl/cert.pem: load
    it too. Certificates are still verified; we just tell Python where they are."""
    ctx = ssl.create_default_context()
    if os.path.exists("/etc/ssl/cert.pem"):
        ctx.load_verify_locations("/etc/ssl/cert.pem")
    return ctx


SSL_CTX = ssl_context()


def api(path, token=None):
    headers = {"User-Agent": "football-menubar"}
    if token:
        headers["X-Auth-Token"] = token
    req = urllib.request.Request(f"{DIRECT_API if token else SHARED_SERVER}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as r:
        return json.loads(r.read())


def choose(prompt, items, label):
    """Numbered picker. Typing text filters the list; a number picks."""
    shown = items
    while True:
        for i, item in enumerate(shown, 1):
            print(f"  {i:>2}. {label(item)}")
        answer = input(f"\n{prompt} (number, or type to search): ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(shown):
            return shown[int(answer) - 1]
        matches = [it for it in items if answer.lower() in label(it).lower()] if answer else items
        if not matches:
            print(f"\nNothing matches '{answer}'. Showing everything again.\n")
            shown = items
        elif len(matches) == 1:
            return matches[0]
        else:
            print()
            shown = matches


def main():
    print("\n⚽  Football Club Tracker setup\n")
    old = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            old = json.load(f)

    # 1. Data source: the shared server (no key) or the user's own token
    token = None
    print("By default this uses the project's shared server, so you don't need an API key.")
    own = input("Use your own football-data.org API key instead? [y/N]: ").strip().lower()
    if own.startswith("y"):
        print("Get a free key at https://www.football-data.org/client/register")
        hint = " (press Enter to keep your current one)" if old.get("token") else ""
        token = input(f"Paste your token{hint}: ").strip() or old.get("token", "")
        if not token:
            sys.exit("No token given. Run ./setup.py again, or answer N to use the shared server.")

    try:
        comps = api("/competitions", token)["competitions"]
    except urllib.error.HTTPError as e:
        if token:
            sys.exit(f"The API rejected that token (HTTP {e.code}). Check it and run ./setup.py again.")
        sys.exit(f"The shared server returned an error (HTTP {e.code}). Try again in a minute.")
    except urllib.error.URLError as e:
        sys.exit(f"Couldn't reach football-data.org: {e.reason}")

    # 2. League
    leagues = sorted((c for c in comps if c.get("type") == "LEAGUE" and (token or c.get("code") in FREE)),
                     key=lambda c: (c["area"]["name"], c["name"]))
    print("\nWhich league does your club play in?\n")
    league = choose("League", leagues, lambda c: f"{c['name']} ({c['area']['name']})")

    # 3. Club
    try:
        teams = api(f"/competitions/{league['code']}/teams", token)["teams"]
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            sys.exit(f"{league['name']} isn't included in your plan. Run ./setup.py and pick another league.")
        raise
    teams.sort(key=lambda t: t["name"])
    print(f"\nPick your club in {league['name']}:\n")
    team = choose("Club", teams, lambda t: t["name"])

    # 4. Colour
    print("\nMenu colour for your club, as a hex code like #6CABDD.")
    colour = input("Press Enter for red: ").strip()
    if colour and not colour.startswith("#"):
        colour = "#" + colour
    colour = colour or old.get("colour", DEFAULT_COLOUR)

    cfg = {
        "league": league["code"],
        "league_name": league["name"],
        "team_id": team["id"],
        "team_name": team["name"],
        "tla": team.get("tla") or team.get("shortName", team["name"])[:3].upper(),
        "crest": team.get("crest"),
        "colour": colour,
    }
    if token:
        cfg["token"] = token  # only stored if you chose your own key
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(CONFIG_FILE, stat.S_IRUSR | stat.S_IWUSR)  # only you can read it

    os.chmod(PLUGIN, os.stat(PLUGIN).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Ask SwiftBar (if it's running) to reload, so the change shows straight away
    subprocess.run(["open", "-g", "swiftbar://refreshallplugins"], capture_output=True)

    print(f"\n✅  Saved. Following {team['name']} in {league['name']}.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
