"""Tiled logic is authoritative. Artwork is a separate, replaceable image layer."""
from dataclasses import dataclass
from math import floor, hypot, isfinite
from pathlib import Path


@dataclass
class GameMap:
    width: int
    height: int
    tile_size: int
    roles: list
    waypoints: list
    artwork: object

    def role_at(self, x, y):
        col, row = floor(x/self.tile_size), floor(y/self.tile_size)
        if 0 <= col < self.width and 0 <= row < self.height:
            return self.roles[row*self.width+col]
        return 0

    @staticmethod
    def _segment_hits_rect(ax, ay, bx, by, left, top, right, bottom):
        """Liang-Barsky segment/AABB intersection, including boundary contact."""
        dx, dy = bx-ax, by-ay
        low, high = 0.0, 1.0
        for p, q in ((-dx, ax-left), (dx, right-ax), (-dy, ay-top), (dy, bottom-ay)):
            if p == 0:
                if q < 0:
                    return False
                continue
            t = q/p
            if p < 0:
                low = max(low, t)
            else:
                high = min(high, t)
            if low > high:
                return False
        return True

    def has_line_of_sight(self, ax, ay, bx, by):
        s = self.tile_size
        for i, role in enumerate(self.roles):
            if role != 3:
                continue
            col, row = i % self.width, i // self.width
            if self._segment_hits_rect(ax, ay, bx, by, col*s, row*s, (col+1)*s, (row+1)*s):
                return False
        return True

    def can_target(self, tower_x, tower_y, enemy_pos):
        ex, ey = enemy_pos
        return self.role_at(ex, ey) != 4 and self.has_line_of_sight(tower_x, tower_y, ex, ey)

    def enemy_visible(self, enemy_pos):
        return self.role_at(*enemy_pos) != 4

    def can_place(self, x, y, radius=16, towers=()):
        """Check the entire circular footprint, without snapping the tower center."""
        if not all(isfinite(v) for v in (x, y, radius)) or radius <= 0:
            return False
        s = self.tile_size
        if x-radius < 0 or y-radius < 0 or x+radius > self.width*s or y+radius > self.height*s:
            return False
        for row in range(max(0, floor((y-radius)/s)), min(self.height-1, floor((y+radius)/s))+1):
            for col in range(max(0, floor((x-radius)/s)), min(self.width-1, floor((x+radius)/s))+1):
                if self.roles[row*self.width+col] == 2:
                    continue
                nx = max(col*s, min(x, (col+1)*s))
                ny = max(row*s, min(y, (row+1)*s))
                if (x-nx)**2+(y-ny)**2 < radius**2-1e-9:
                    return False
        return all(hypot(x-tx, y-ty) >= radius+tr for tx, ty, tr in towers)


def load_map(path):
    """Call after creating a Pygame display, as required for image conversion."""
    import pytmx
    from pytmx.util_pygame import load_pygame
    tiled = load_pygame(str(Path(path)))
    if tiled.tilewidth != tiled.tileheight:
        raise ValueError('Square tiles are required.')
    role_layer = tiled.get_layer_by_name('Tile roles')
    roles = []
    for row in role_layer.data:
        for gid in row:
            properties = tiled.get_tile_properties_by_gid(gid) or {}
            roles.append({'path': 1, 'buildable': 2, 'blocker': 3, 'tunnel': 4}.get(properties.get('role'), 0))
    route = tiled.get_layer_by_name('Enemy route')
    path_obj = next(obj for obj in route if obj.type == 'enemy_path')
    points = [(point.x, point.y) for point in path_obj.points]
    art_layer = tiled.get_layer_by_name('Artwork')
    art = tiled.get_tile_image_by_gid(art_layer.gid)
    if len(points) < 2 or art is None or art.get_size() != (tiled.width*tiled.tilewidth, tiled.height*tiled.tileheight):
        raise ValueError('Missing route or artwork with incorrect dimensions.')
    if not isinstance(role_layer, pytmx.TiledTileLayer):
        raise ValueError('Tile roles must be a Tiled tile layer.')
    return GameMap(tiled.width, tiled.height, tiled.tilewidth, roles, points, art)
