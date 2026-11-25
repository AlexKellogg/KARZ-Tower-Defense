"""Export Caldera's Edge from the approved 20x12 editor layout (1-based coordinates)."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
BUILDS = [(4,3),(5,3),(4,4),(5,4),(7,3),(8,3),(12,3),(13,3),(12,4),(13,4),
          (16,3),(17,3),(17,4),(8,6),(9,6),(13,6),(13,7),(14,7),(5,9),(6,9),
          (5,10),(6,10),(8,9),(9,9),(13,9),(14,9),(13,10),(14,10),(16,9),(17,9)]
BLOCKERS = [(3,3),(3,4),(7,4),(8,4),(11,3),(11,4),(16,4),(16,5),
            (4,9),(4,10),(8,10),(9,10),(12,9),(12,10),(16,10),(17,10)]
TUNNELS = [[(9,5),(10,5)], [(11,8),(12,8)]]


def expand(corners):
    result = [corners[0]]
    for tx, ty in corners[1:]:
        x, y = result[-1]
        assert x == tx or y == ty
        while (x, y) != (tx, ty):
            x += (tx > x)-(tx < x)
            y += (ty > y)-(ty < y)
            result.append((x, y))
    return result


ROUTES = [expand([(1,2),(6,2),(6,5),(14,5),(14,2),(20,2)]),
          expand([(1,11),(7,11),(7,8),(15,8),(15,11),(20,11)])]
ROWS = [['.']*20 for _ in range(12)]
for lane, route in enumerate(ROUTES):
    for c, r in route:
        ROWS[r-1][c-1] = 'PQ'[lane]
    for c, r in TUNNELS[lane]:
        ROWS[r-1][c-1] = 'TU'[lane]
    c, r = route[0]
    ROWS[r-1][c-1] = 'Ss'[lane]
    c, r = route[-1]
    ROWS[r-1][c-1] = 'Ee'[lane]
for r in (6,7):
    ROWS[r-1] = ['L']*20
for symbol, coords in [('B', BUILDS), ('X', BLOCKERS)]:
    for c, r in coords:
        ROWS[r-1][c-1] = symbol
ROWS = [''.join(row) for row in ROWS]


def generate():
    directory = ROOT/'maps'
    # Reuse the same role tileset and layer conventions as Hard, not its geometry.
    tree = ET.parse(directory/'razorback_pass.tmx')
    m = tree.getroot()
    properties = {'name': "Caldera's Edge", 'difficulty': 'Impossible', 'clear_wave': '10',
                  'theme': 'volcanic-caldera', 'decoration': 'approved-caldera-v1'}
    for prop in m.find('properties'):
        prop.set('value', properties[prop.get('name')])
    m.find('imagelayer/image').set('source', 'calderas_edge.png')
    role = {'.':0, 'L':0, 'B':2, 'X':3, 'T':4, 'U':4}
    roles = [role.get(c, 1) for row in ROWS for c in row]
    m.find('layer/data').text = ',\n'.join(','.join(map(str,roles[r*20:(r+1)*20])) for r in range(12))
    groups = {g.get('name'):g for g in m.findall('objectgroup')}
    for group in groups.values():
        for obj in list(group):
            group.remove(obj)
    oid = 0
    def obj(group, **attrs):
        nonlocal oid
        oid += 1
        return ET.SubElement(groups[group], 'object', id=str(oid), **attrs)
    for group, kind, coords in [('Buildable zones','buildable',BUILDS),
                                ('Sight blockers','blocker',BLOCKERS),
                                ('Tunnel','tunnel',sum(TUNNELS, []))]:
        for c,r in coords:
            obj(group, name=f'{kind} {c},{r}', type=kind, x=str((c-1)*48), y=str((r-1)*48), width='48', height='48')
    routes = [[{'x':(c-.5)*48,'y':(r-.5)*48} for c,r in route] for route in ROUTES]
    for lane, points in enumerate(routes):
        path = obj('Enemy route', name=f'Route {lane+1}', type='enemy_path', x='0', y='0')
        ET.SubElement(path,'polyline',points=' '.join(f"{p['x']:g},{p['y']:g}" for p in points))
        for kind,p in [('entrance',points[0]),('exit',points[-1])]:
            endpoint = obj('Entrance and exit',name=f'{kind} {lane+1}',type=kind,x=str(p['x']),y=str(p['y']))
            ET.SubElement(endpoint,'point')
    m.set('nextobjectid',str(oid+1))
    ET.indent(m)
    tree.write(directory/'calderas_edge.tmx',encoding='utf-8',xml_declaration=True)
    layout = dict(schema='karz-layout-v2',name="Caldera's Edge",difficulty='Impossible',
                  clearWave=10,width=20,height=12,tileSize=48,tiles=roles,rows=ROWS,
                  routes=routes,waypoints=routes[0])
    (directory/'calderas_edge.json').write_text(json.dumps(layout,indent=2),encoding='utf-8')


if __name__ == '__main__':
    generate()
