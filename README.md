# ⚽ Football Club Tracker for the macOS menu bar

Your club's league position, next fixtures and recent results, one click away in the menu bar.

```
🛡 ARS 2nd · 21 pts
```

Click it for:

- **The league table**: top 4 up front, with the rest four at a time in submenus. Your club's row is highlighted and every team gets its crest.
- **Next 5 fixtures** in your own time zone. Cup and European games are shown in blue.
- **Last 5 results**, colour-coded win, draw or loss.

It works for any club in the leagues covered by the free football-data.org plan: the Premier League, Championship, La Liga, Serie A, Bundesliga, Ligue 1, Eredivisie, Primeira Liga and Brasileirão.

## Install (about 3 minutes, no API key needed)

**You need:** a Mac and Python 3. macOS will offer to install Python the first time you run `python3` in Terminal.

1. **Download this project**:
   ```bash
   git clone https://github.com/varungirish97/football-club-tracker.git
   cd football-club-tracker
   ```

2. **Run setup** and pick your league and club:
   ```bash
   ./setup.py
   ```
   Press Enter at the API key question to use the shared server. Then pick your league, club and an optional colour. Your choices are saved to `config.json`, which stays on your Mac and is never committed.

3. **Install [SwiftBar](https://swiftbar.app)**, the free app that puts scripts in the menu bar:
   ```bash
   brew install --cask swiftbar
   ```
   If you don't use Homebrew, download it from swiftbar.app instead.

4. **Open SwiftBar** and, when it asks for a plugin folder, choose this project's **`plugins`** folder. In the file picker, Cmd+Shift+G lets you paste a path.

Your club appears in the menu bar within a few seconds.

## Can't see it in the menu bar?

On MacBooks with a notch, macOS hides menu bar items that don't fit, without any warning. The menu bar shows just the crest, position and points to save space. If it's still hidden, quit a menu bar app you don't need, or tighten the spacing between all menu bar icons (log out and back in afterwards):

```bash
defaults -currentHost write -globalDomain NSStatusItemSpacing -int 8
defaults -currentHost write -globalDomain NSStatusItemSelectionPadding -int 6
```

To show the club's short name too (e.g. `ARS 2nd · 21 pts`), add `"compact": false` to `config.json`.

## Change club

Click the menu bar item, then choose **Change club…**, or run `./setup.py` again.

## How it works

```
your Mac ──▶ shared server (Cloudflare Worker) ──▶ football-data.org
             holds the API key, caches answers
```

- `plugins/football.10m.py` is the SwiftBar plugin. SwiftBar runs it every 10 minutes (the `10m` in the filename) and shows whatever it prints. The first line goes in the menu bar; lines after `---` go in the dropdown.
- By default it fetches data from a small **shared server**, a Cloudflare Worker that adds an API key and caches each answer for 10 minutes. Everyone following the same league shares one upstream call, so nobody needs their own key.
- Each refresh makes **2 requests**: the league table and your club's matches.
- Crests are downloaded once, shrunk with macOS's built-in `sips` tool and cached in `.crests/`.
- Only the Python standard library is used, so there's nothing to `pip install`.

## Using your own API key

The shared server is a free hobby service with no guarantees. For your own quota (10 calls a minute), get a free key at [football-data.org/client/register](https://www.football-data.org/client/register), run `./setup.py` and answer **y** at the API key question. The plugin then talks to football-data.org directly.

## Limitations

- On the free plan, scores and fixtures update with a delay. Live scores need a paid plan.
- The colour bands (top 4 green, 5–6 blue, bottom 3 orange) follow Premier League places. Other leagues award places a bit differently.

## Credits

Data from [football-data.org](https://www.football-data.org). Menu bar plumbing by [SwiftBar](https://github.com/swiftbar/SwiftBar). Found through [public-apis](https://github.com/public-apis/public-apis).
