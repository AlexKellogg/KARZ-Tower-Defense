"""Export Canyon Crossing logic without modifying Desert Highway."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from export_map import ordered_path

ROOT = Path(__file__).resolve().parent
SIZE = 48
ROWS = [
    '....................',
    'SPPPPPPP............',
    '...BBBBP.BBB........',
    '...BBBBP.BBB.PPPPPP.',
    '.......P.....P....P.',
    '.BPPPPPP.....PBBBBP.',
    'BBP..........PBBBBP.',
    '..P.BBB......PBBBBP.',
    '..PPPPPPPPPPPPBBB.P.',
    '..............BBB.P.',
    '..................PE',
    '....................',
]

# The generated artwork uses a smooth road that is not snapped to tile centers.
# These points align enemy movement with the visible center line while ROWS remains
# the placement authority for path/buildable/blocked tiles.
ART_POINTS = [
    (0, 46), (403, 46), (403, 226), (160, 226), (160, 426),
    (620, 426), (620, 174), (886, 174), (886, 473), (960, 473),
]


def generate():
    assert len(ROWS) == 12 and all(len(row) == 20 for row in ROWS)
    directory = ROOT / 'maps'
    route = ordered_path(ROWS)
    roles = [2 if c == 'B' else 1 if c in 'PSE' else 0 for row in ROWS for c in row]
    points = ART_POINTS
    layout = dict(
        schema='karz-layout-v1', name='Canyon Crossing', difficulty='Medium', clearWave=7,
        theme='desert-canyon', decoration='sandstone-crossing-v1', width=20, height=12,
        tileSize=SIZE, tiles=roles, entrance=route[0][1]*20+route[0][0],
        exit=route[-1][1]*20+route[-1][0], rows=ROWS,
        waypoints=[dict(x=x, y=y) for x, y in points],
    )
    (directory/'canyon_crossing.json').write_text(json.dumps(layout, indent=2), encoding='utf-8')

    m = ET.Element('map', version='1.10', orientation='orthogonal', renderorder='right-down',
                   width='20', height='12', tilewidth='48', tileheight='48', infinite='0', nextlayerid='6')
    props = ET.SubElement(m, 'properties')
    for name, value, kind in [('name', 'Canyon Crossing', None), ('difficulty', 'Medium', None),
                              ('clear_wave', '7', 'int'), ('theme', 'desert-canyon', None),
                              ('decoration', 'sandstone-crossing-v1', None)]:
        attrs = {'name': name, 'value': value}
        if kind:
            attrs['type'] = kind
        ET.SubElement(props, 'property', **attrs)
    ts = ET.SubElement(m, 'tileset', firstgid='1', name='Placement roles', tilewidth='48',
                       tileheight='48', tilecount='2', columns='2')
    ET.SubElement(ts, 'image', source='roles.png', width='96', height='48')
    for i, role in enumerate(['path', 'buildable']):
        p = ET.SubElement(ET.SubElement(ts, 'tile', id=str(i)), 'properties')
        ET.SubElement(p, 'property', name='role', value=role)
    art = ET.SubElement(m, 'imagelayer', id='1', name='Artwork', locked='1')
    ET.SubElement(art, 'image', source='canyon_crossing.png', width='960', height='576')
    layer = ET.SubElement(m, 'layer', id='2', name='Tile roles', width='20', height='12',
                          visible='0', opacity='0.4')
    ET.SubElement(layer, 'data', encoding='csv').text = ',\n'.join(
        ','.join(map(str, roles[y*20:y*20+20])) for y in range(12))
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
        obj = ET.SubElement(endpoints, 'object', id=str(oid), name=name, type=name.lower(),
                            x=str(point[0]), y=str(point[1]))
        ET.SubElement(obj, 'point')
        oid += 1
    m.set('nextobjectid', str(oid))
    ET.indent(m)
    ET.ElementTree(m).write(directory/'canyon_crossing.tmx', encoding='utf-8', xml_declaration=True)
    print(f'Exported Canyon Crossing: {len(route)} route tiles, {roles.count(2)} buildable tiles.')


if __name__ == '__main__':
    generate()
