"""Rebuild the Tiled logic layers from the approved layout; keep artwork intact."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
ROWS = [
    '..S.................', '.BP.......PPPPPPPP..', '.BPBPPPBBBPBB.BBBP..',
    '..PBPBPBBBPBB.BBBP..', '..PPPBPBBBP...BBBP..', '.BB...P...PBBPPPPP..',
    '.BBPPPP.BBPBBPBBB...', '...PBBB.BBPBBPPPPP..', '...PPPPPPPP....BBP..',
    '.....BB..BB....BBP..', '.....BB..BB......P..', '.................E..',
]
SIZE = 48


def ordered_path(rows):
    path = {(x, y) for y, row in enumerate(rows) for x, c in enumerate(row) if c in 'PSE'}
    start = next((x, y) for y, row in enumerate(rows) for x, c in enumerate(row) if c == 'S')
    end = next((x, y) for y, row in enumerate(rows) for x, c in enumerate(row) if c == 'E')
    def adjacent(p):
        x, y = p
        return [q for q in [(x-1,y), (x+1,y), (x,y-1), (x,y+1)] if q in path]
    if any(len(adjacent(p)) != (1 if p in (start, end) else 2) for p in path):
        raise ValueError('The route must have two endpoints and no branches.')
    route = [start]
    while route[-1] != end:
        following = [p for p in adjacent(route[-1]) if p not in route]
        if len(following) != 1:
            raise ValueError('Route is disconnected or loops.')
        route.append(following[0])
    if len(route) != len(path):
        raise ValueError('Unreachable path tiles.')
    return route


def generate():
    assert len(ROWS) == 12 and all(len(row) == 20 for row in ROWS)
    directory = ROOT / 'maps'
    directory.mkdir(exist_ok=True)
    route = ordered_path(ROWS)
    roles = [2 if c == 'B' else 1 if c in 'PSE' else 0 for row in ROWS for c in row]
    points = [(x*SIZE+SIZE/2, y*SIZE+SIZE/2) for x, y in route]
    layout = dict(schema='karz-layout-v1', theme='desert-highway', decoration='roadside-oasis-v2',
                  width=20, height=12, tileSize=SIZE, tiles=roles,
                  entrance=route[0][1]*20+route[0][0], exit=route[-1][1]*20+route[-1][0],
                  rows=ROWS, waypoints=[dict(x=x, y=y) for x, y in points])
    (directory / 'desert_highway.json').write_text(json.dumps(layout, indent=2), encoding='utf-8')
    m = ET.Element('map', version='1.10', orientation='orthogonal', renderorder='right-down',
                   width='20', height='12', tilewidth='48', tileheight='48', infinite='0', nextlayerid='6')
    props = ET.SubElement(m, 'properties')
    ET.SubElement(props, 'property', name='theme', value='desert-highway')
    ET.SubElement(props, 'property', name='decoration', value='roadside-oasis-v2')
    ts = ET.SubElement(m, 'tileset', firstgid='1', name='Placement roles', tilewidth='48',
                       tileheight='48', tilecount='2', columns='2')
    ET.SubElement(ts, 'image', source='roles.png', width='96', height='48')
    for i, role in enumerate(['path', 'buildable']):
        p = ET.SubElement(ET.SubElement(ts, 'tile', id=str(i)), 'properties')
        ET.SubElement(p, 'property', name='role', value=role)
    art = ET.SubElement(m, 'imagelayer', id='1', name='Artwork', locked='1')
    ET.SubElement(art, 'image', source='desert_highway.png', width='960', height='576')
    layer = ET.SubElement(m, 'layer', id='2', name='Tile roles', width='20', height='12', visible='0', opacity='0.4')
    ET.SubElement(layer, 'data', encoding='csv').text = ',\n'.join(','.join(map(str, roles[y*20:y*20+20])) for y in range(12))
    oid = 1
    builds = ET.SubElement(m, 'objectgroup', id='3', name='Buildable zones', visible='0')
    for y, row in enumerate(ROWS):
        x = 0
        while x < 20:
            if row[x] != 'B':
                x += 1
                continue
            first = x
            while x < 20 and row[x] == 'B':
                x += 1
            ET.SubElement(builds, 'object', id=str(oid), name=f'Zone {oid}', type='buildable',
                          x=str(first*SIZE), y=str(y*SIZE), width=str((x-first)*SIZE), height=str(SIZE))
            oid += 1
    enemies = ET.SubElement(m, 'objectgroup', id='4', name='Enemy route', visible='0')
    obj = ET.SubElement(enemies, 'object', id=str(oid), name='Enemy path', type='enemy_path', x='0', y='0')
    oid += 1
    ET.SubElement(obj, 'polyline', points=' '.join(f'{x:g},{y:g}' for x, y in points))
    endpoints = ET.SubElement(m, 'objectgroup', id='5', name='Entrance and exit', visible='0')
    for name, point in [('Entrance', points[0]), ('Exit', points[-1])]:
        obj = ET.SubElement(endpoints, 'object', id=str(oid), name=name, type=name.lower(), x=str(point[0]), y=str(point[1]))
        ET.SubElement(obj, 'point')
        oid += 1
    m.set('nextobjectid', str(oid))
    ET.indent(m)
    ET.ElementTree(m).write(directory / 'desert_highway.tmx', encoding='utf-8', xml_declaration=True)
    import pygame
    palette = pygame.Surface((96, 48), pygame.SRCALPHA)
    palette.fill((225, 150, 50, 180), (0, 0, 48, 48))
    palette.fill((80, 200, 140, 180), (48, 0, 48, 48))
    pygame.image.save(palette, directory / 'roles.png')
    print(f'Exported 20 x 12 map: {len(route)} route tiles, {roles.count(2)} buildable tiles.')


if __name__ == '__main__':
    generate()
