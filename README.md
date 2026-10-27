# KARZ TD — Desert highway map starter

## Maps and progression

- **Desert Highway** is the Easy map and clears after wave 5.
- **Canyon Crossing** is the Medium map and clears after wave 7. It has 49 route tiles and 38 buildable tiles.
- **Razorback Pass** is the Hard map and clears after wave 10. Its 31 build tiles are shaped by
  21 sight-blocking ridge tiles and a two-tile untargetable tunnel.
  KARZ disappear while their centers are inside the connected tunnel and reappear at the exit;
  they continue moving underground. Ridge tiles block tower targeting across them.
- Impossible retains a temporary Desert Highway placeholder until its dedicated map is approved.

The selected map supplies its artwork, route, build zones, difficulty rules, and clear wave automatically.
Sandbox mode continues indefinitely; the same post-clear behavior is intended for a future Freeplay option.

The approved 20 × 12 layout uses 48px tiles (960 × 576px). There are 59 ordered path tiles and 60 buildable tiles. Tower centers remain free to move within buildable areas; placement checks the entire circular footprint and existing towers.

## Run the full game on Windows

After installing dependencies as shown below, run `.\.venv\Scripts\python.exe main.py`.
Sign in, open the difficulty selector, and choose **Hard — Razorback Pass** for the approved
volcanic map. The card preview and playable map use the same artwork. Beat Medium to unlock
Hard, or use an existing admin account to test every map. Hard sandbox is also available
once unlocked. `Launch KARZ.cmd` and `preview.py` launch the older Easy-map preview, not this UI.

## Run the legacy preview on Windows

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
.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py"
.\.venv\Scripts\python.exe main.py --smoke
```

Format references: [Tiled TMX documentation](https://doc.mapeditor.org/en/stable/reference/tmx-map-format/) and [pytmx usage](https://github.com/bitcraft/pytmx/blob/master/readme.md).
