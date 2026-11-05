# ⚽ Football Club Tracker

Your club in your Mac's menu bar: league position, live matchday scores, and a notification at full time.

<!-- Add a screenshot of the open menu here: docs/screenshot.png -->

## What you get

**In the menu bar**, always visible:

| When | It shows |
| --- | --- |
| Normal days | Your club's crest, league position and points: `2nd · 21` |
| Matchday | Who you play and when: `@ LIV · 8:30 AM` |
| During the match | The live score: `● LIV 1–2 ARS` |
| After the match | The final score for a few hours: `FT LIV 1–3 ARS` |

**Click it** to see:

- **Form**: your last five results as 🟢 🟢 ⚪ 🟢 🔴. Hover over it for the scores.
- **The league table**, top four first, then four at a time. Every club has its crest.
- **Your next two fixtures**, in your own time zone.

**At full time** you get a notification: *Liverpool 1–3 Arsenal · Win ✅*

It works for any club in the Premier League, Championship, La Liga, Serie A, Bundesliga, Ligue 1, Eredivisie, Primeira Liga or Brasileirão.

## Install

Open the **Terminal** app (press ⌘ Space, type *Terminal*, press Return), paste this line and press Return:

```bash
curl -fsSL https://raw.githubusercontent.com/varungirish97/football-club-tracker/main/install.sh | bash
```

The installer:

1. Downloads the app.
2. Installs [SwiftBar](https://swiftbar.app), the free app that puts it in your menu bar.
3. Asks you to pick your league, club and an optional colour. Press Return at the first question; no account or API key is needed.
4. Starts it. Your club's crest appears in the menu bar.

To **update**, run the same line again. Your club and settings are kept.

## Using it

- **Change club**: click the crest, then **Change club…**
- **Refresh now**: click the crest, then **Refresh**. It updates by itself every 10 minutes, and every 2 minutes around kickoff.
- **Offline?** It keeps showing the last data it got, with a note saying when that was.

### Can't see it in the menu bar?

On MacBooks with a notch, macOS hides menu bar icons that don't fit, without telling you. Quit a menu bar app you don't need. Apps with long menus, like Chrome or VS Code, can also push it out of view while they're in front.

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/varungirish97/football-club-tracker/main/install.sh | bash -s -- --uninstall
```

## Settings

Your choices live in `~/Library/Application Support/FootballClubTracker/config.json`. Optional extras you can add:

| Setting | Effect |
| --- | --- |
| `"compact": false` | Show the club's short name in the menu bar: `ARS 2nd · 21 pts` |
| `"notifications": false` | No full-time notifications |
| `"clock": "24"` or `"12"` | Force the time format (by default it follows your Mac's setting) |
| `"token": "…"` | Use your own free [football-data.org](https://www.football-data.org/client/register) API key instead of the shared server |

## Credits

Data from [football-data.org](https://www.football-data.org). On the free plan, scores update with a short delay. Menu bar by [SwiftBar](https://github.com/swiftbar/SwiftBar). Found through [public-apis](https://github.com/public-apis/public-apis). MIT licensed.
