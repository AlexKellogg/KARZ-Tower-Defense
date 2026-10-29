"""Export the approved Razorback Pass Hard-map logic."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SIZE = 48
ROWS = [
    '........X...........',
    '.BBB..BBX...........',
    'SPPPPPPBX.......XX..',
    '...XXXPXX.........PE',
    '...XBBP....BB...BBP.',
    '...XBBPPPPPPB...BBP.',
    '...XBB..BBBP.XXXX.P.',
    '.........BBT.XBBX.P.',
    '...........T..BBXXP.',
    '...........PPPPPPPP.',
    '...........BBB......',
    '....................',
]


def ordered_path(rows):
    path = {(x, y) for y, row in enumerate(rows) for x, c in enumerate(row) if c in 'PSTE'}
    start = next((x, y) for y, row in enumerate(rows) for x, c in enumerate(row) if c == 'S')
    end = next((x, y) for y, row in enumerate(rows) for x, c in enumerate(row) if c == 'E')

    def adjacent(point):
        x, y = point
        return [q for q in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)) if q in path]

    if any(len(adjacent(p)) != (1 if p in (start, end) else 2) for p in path):
        raise ValueError('The Razorback route must have two endpoints and no branches.')
    route = [start]
    while route[-1] != end:
        following = [p for p in adjacent(route[-1]) if p not in route]
        if len(following) != 1:
            raise ValueError('The Razorback route is disconnected or loops.')
        route.append(following[0])
    if len(route) != len(path):
        raise ValueError('Razorback contains unreachable route tiles.')
    return route


def generate():
    assert len(ROWS) == 12 and all(len(row) == 20 for row in ROWS)
    directory = ROOT / 'maps'
    route = ordered_path(ROWS)
    role_for = {'.': 0, 'S': 1, 'P': 1, 'E': 1, 'B': 2, 'X': 3, 'T': 4}
    roles = [role_for[c] for row in ROWS for c in row]
    points = [(x*SIZE+SIZE/2, y*SIZE+SIZE/2) for x, y in route]
    layout = dict(
        schema='karz-layout-v1', name='Razorback Pass', difficulty='Hard', clearWave=10,
        theme='desert-razorback', decoration='sandstone-ridges-v1', width=20, height=12,
        tileSize=SIZE, tiles=roles, entrance=route[0][1]*20+route[0][0],
        exit=route[-1][1]*20+route[-1][0], rows=ROWS,
        waypoints=[dict(x=x, y=y) for x, y in points],
    )
    (directory/'razorback_pass.json').write_text(json.dumps(layout, indent=2), encoding='utf-8')

    m = ET.Element('map', version='1.10', orientation='orthogonal', renderorder='right-down',
                   width='20', height='12', tilewidth='48', tileheight='48', infinite='0', nextlayerid='8')
    props = ET.SubElement(m, 'properties')
    for name, value, kind in [('name', 'Razorback Pass', None), ('difficulty', 'Hard', None),
                              ('clear_wave', '10', 'int'), ('theme', 'desert-razorback', None),
                              ('decoration', 'sandstone-ridges-v1', None)]:
        attrs = {'name': name, 'value': value}
        if kind:
            attrs['type'] = kind
        ET.SubElement(props, 'property', **attrs)
    tileset = ET.SubElement(m, 'tileset', firstgid='1', name='Razorback roles', tilewidth='48',
                            tileheight='48', tilecount='4', columns='4')
    ET.SubElement(tileset, 'image', source='roles_hard.png', width='192', height='48')
    for i, role in enumerate(('path', 'buildable', 'blocker', 'tunnel')):
        p = ET.SubElement(ET.SubElement(tileset, 'tile', id=str(i)), 'properties')
        ET.SubElement(p, 'property', name='role', value=role)
    art = ET.SubElement(m, 'imagelayer', id='1', name='Artwork', locked='1')
    ET.SubElement(art, 'image', source='razorback_pass.png', width='960', height='576')
    layer = ET.SubElement(m, 'layer', id='2', name='Tile roles', width='20', height='12', visible='0', opacity='0.4')
    ET.SubElement(layer, 'data', encoding='csv').text = ',\n'.join(
        ','.join(map(str, roles[y*20:y*20+20])) for y in range(12))
    oid = 1
    builds = ET.SubElement(m, 'objectgroup', id='3', name='Buildable zones', visible='0')
    blockers = ET.SubElement(m, 'objectgroup', id='4', name='Sight blockers', visible='0')
    tunnels = ET.SubElement(m, 'objectgroup', id='5', name='Tunnel', visible='0')
    groups = {'B': (builds, 'buildable'), 'X': (blockers, 'blocker'), 'T': (tunnels, 'tunnel')}
    for y, row in enumerate(ROWS):
        x = 0
        while x < 20:
            symbol = row[x]
            if symbol not in groups:
                x += 1
                continue
            first = x
            while x < 20 and row[x] == symbol:
                x += 1
            group, kind = groups[symbol]
            ET.SubElement(group, 'object', id=str(oid), name=f'{kind.title()} {oid}', type=kind,
                          x=str(first*SIZE), y=str(y*SIZE), width=str((x-first)*SIZE), height=str(SIZE))
            oid += 1
    enemies = ET.SubElement(m, 'objectgroup', id='6', name='Enemy route', visible='0')
    obj = ET.SubElement(enemies, 'object', id=str(oid), name='Enemy path', type='enemy_path', x='0', y='0')
    oid += 1
    ET.SubElement(obj, 'polyline', points=' '.join(f'{x:g},{y:g}' for x, y in points))
    endpoints = ET.SubElement(m, 'objectgroup', id='7', name='Entrance and exit', visible='0')
    for name, point in [('Entrance', points[0]), ('Exit', points[-1])]:
        obj = ET.SubElement(endpoints, 'object', id=str(oid), name=name, type=name.lower(),
                            x=str(point[0]), y=str(point[1]))
        ET.SubElement(obj, 'point')
        oid += 1
    m.set('nextobjectid', str(oid))
    ET.indent(m)
    ET.ElementTree(m).write(directory/'razorback_pass.tmx', encoding='utf-8', xml_declaration=True)
    print(f'Exported Razorback Pass: {len(route)} route tiles, {roles.count(2)} buildable, '
          f'{roles.count(3)} blockers, {roles.count(4)} tunnel tiles.')


if __name__ == '__main__':
    generate()
