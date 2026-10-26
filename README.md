# KARZ TD — Desert highway map starter

The approved 20 × 12 layout uses 48px tiles (960 × 576px). There are 59 ordered path tiles and 60 buildable tiles. Tower centers remain free to move within buildable areas; placement checks the entire circular footprint and existing towers.

## Run the preview on Windows

Map layout and design: **Reagan Moore**.

![Desert highway map](maps/desert_highway.png)

After completing setup below, double-click **Launch KARZ.cmd** to start the preview.

Install Python 3.12, then open a new PowerShell window in the repository folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe preview.py
```

Click a green spot to place a base tower. Click a tower to select it and see its range, then press **Upgrade (free)** or U to upgrade it (3 levels). Right-click deselects, B shows buildable zones, Z removes the latest tower, and Esc exits. Placeholder enemies spawn continuously along the route; towers target the enemy furthest along the path within range. The bottom bar shows towers, kills, and enemies that leaked. There is no economy yet: upgrades are free and enemy stats are placeholders.

On macOS, use `python3 -m venv .venv`, then `.venv/bin/python` in place of `.\.venv\Scripts\python.exe` in the commands above and below.

## In-game controls

| Key / button | Action |
| --- | --- |
| Click | Place a tower, or select one |
| U / Upgrade | Upgrade the selected tower |
| Z | Undo the latest tower |
| Space or P / pause button | Pause and resume (you can still place and upgrade towers while paused) |
| F / speed button | Cycle game speed 1x → 2x → 3x |
| N | Start the next wave now (sandbox only) |
| B | Show buildable zones |
| Right-click | Deselect |
| Esc | Back to the menu |

Between waves, the top banner previews the next wave (enemy count and HP). During a wave, the chip in the top-right corner shows what is coming next. Speed-ups run the simulation in extra steps, so the in-game timer counts game time and the time leaderboard stays fair.

## Online accounts (FastAPI server)

By default the game saves accounts and scores to a SQLite file on your own computer (`local_backend.py`). To share accounts and leaderboards between players and devices, run the server in `server/` and point the game at it. Both use the same `Backend` interface in `backend.py`, so the screens work the same either way.

Install the server requirements (this also installs the game requirements):

```powershell
.\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
```

Start the server locally (it creates `karz_server.db` in the repository folder):

```powershell
.\.venv\Scripts\python.exe -m uvicorn server.app:create_app --factory --port 8000
```

Then, in a second window, start the game against it:

```powershell
.\.venv\Scripts\python.exe main.py --server http://127.0.0.1:8000
```

You can set the `KARZ_SERVER_URL` environment variable instead of passing `--server`. With neither set, or with `--offline`, the game saves locally like before. If the server can't be reached, the game shows a message instead of crashing.

Interactive API docs are at http://127.0.0.1:8000/docs while the server is running.

To make an account an admin on the server database:

```powershell
.\.venv\Scripts\python.exe -m server.make_admin you@example.com
```

### Hosting

Set `DATABASE_URL` to the hosted PostgreSQL connection string (Render and Railway both provide one; `postgres://` URLs are converted automatically). Use this start command:

```
uvicorn server.app:create_app --factory --host 0.0.0.0 --port $PORT
```

Players then launch with `--server https://your-app-url`.

### API

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | none | Server is up |
| POST | `/auth/signup` | none | Create account, returns token |
| POST | `/auth/login` | none | Log in, returns token |
| POST | `/auth/logout` | token | Revoke the token |
| GET / PUT | `/me` | token | Read or update your account |
| GET | `/me/unlocked` | token | Difficulties you can play |
| POST | `/me/runs` | token | Save a finished game, returns new unlocks |
| GET | `/leaderboard/{score,time,lives}` | none | Top players, optional `?difficulty=` |
| GET | `/admin/accounts` | admin token | All accounts |
| PUT | `/admin/accounts/{id}/role` | admin token | Change a role |

Passwords are hashed with PBKDF2 and a per-account salt. Tokens are random, stored only as SHA-256 hashes, and expire after 30 days. Roles are always checked against the database, never trusted from the client.

## Open in Tiled

Open `maps/desert_highway.tmx`. The layers are:

- **Artwork:** the polished map image, locked to prevent accidental movement.
- **Tile roles:** hidden by default; enable to paint semantic path/buildable tiles with the included role tileset.
- **Buildable zones:** rectangles matching the original buildable tiles, for inspection.
- **Enemy route:** the ordered polyline through cell centers.
- **Entrance and exit:** named point objects.

The Python loader reads Tile roles for placement and Enemy route for movement. After editing roles in Tiled, update the route polyline as needed. Buildable zone rectangles are reference overlays, not the runtime authority. The JSON is an original-layout snapshot; it is not updated automatically by Tiled. `export_map.py` regenerates the original logic layers and overwrites the TMX/JSON, so do not run it over manual edits you wish to keep.

The artwork is a flattened background. Tiled logic edits do not redraw the road or decorations; revise the background separately if the layout changes. The map's decorative objects are baked into the artwork, not individual movable sprites yet.

## Integrate into the game

After creating the Pygame display, call `load_map(path)` from `map_runtime.py`. Blit `game_map.artwork`, move enemies through `game_map.waypoints`, and call `game_map.can_place(x, y, radius, towers)` before placing a tower. Existing towers use `(x, y, radius)` tuples. `preview.py` shows those calls together.

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s . -p test_map.py
.\.venv\Scripts\python.exe preview.py --smoke
```

Run every test (needs `server\requirements.txt` installed). `test_server.py` runs the same account, role, unlock and leaderboard tests from `test_backend.py` against the FastAPI server, so both backends must behave identically:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py"
```

To also run the server tests against a real PostgreSQL database, set `KARZ_TEST_POSTGRES_URL` (for example `postgresql://user@127.0.0.1:5432/karz_test`) first. Those tests wipe that database, so use a throwaway one.

Format references: [Tiled TMX documentation](https://doc.mapeditor.org/en/stable/reference/tmx-map-format/) and [pytmx usage](https://github.com/bitcraft/pytmx/blob/master/readme.md).
