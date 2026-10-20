import math
from functools import lru_cache

import pygame

SS = 2
SUN = (255, 248, 222)
SAND_SHADOW = (204, 150, 88)
SAND_LIT = (238, 196, 134)
DARK_STONE = (92, 58, 30)
FLAG = (30, 50, 104)
ASPHALT = (84, 80, 82)
ROAD_EDGE = (226, 160, 86)
ROAD_LINE = (246, 206, 84)
CAR = (208, 60, 46)

SCENES = {
    'wide': {
        'sky': ((255, 206, 128), (255, 242, 210)),
        'sun': (0.84, 0.17, 30),
        'layers': (((242, 196, 112), (254, 224, 154)), ((228, 172, 86), (250, 208, 124))),
        'dunes': (
            ((0.16, 0.73), -0.2, 0.5), ((0.52, 0.76), 0.2, 0.8), ((0.86, 0.72), 0.56, 1.2),
            ((0.0, 0.8), -0.5, 0.55), ((0.42, 0.82), -0.05, 0.85), ((0.82, 0.79), 0.4, 1.3),
        ),
        'road_horizon': 0.77,
        'cars': (1.35, 2.5, 4.2, 7.0),
        'far_towers': ((0.16, 0.735, 0.3), (0.53, 0.765, 0.26), (0.86, 0.725, 0.32)),
        'near_towers': ((0.08, 0.93, 0.95), (0.27, 0.86, 0.55), (0.76, 0.85, 0.52), (0.92, 0.95, 1.0)),
    },
    'card': {
        'sky': ((240, 150, 72), (255, 222, 150)),
        'sun': (0.88, 0.34, 16),
        'layers': (
            ((232, 168, 80), (252, 208, 118)),
            ((214, 146, 58), (246, 192, 96)),
            ((184, 116, 40), (236, 172, 70)),
        ),
        'dunes': (
            ((0.18, 0.6), -0.25, 0.6), ((0.66, 0.56), 0.28, 1.05), ((1.05, 0.66), 0.72, 1.4),
            ((0.36, 0.74), -0.05, 0.85), ((0.9, 0.76), 0.55, 1.3),
            ((0.04, 0.86), -0.4, 0.5), ((0.62, 0.9), 0.25, 1.1),
        ),
    },
}


def _bezier(points, steps=24):
    n = len(points)-1
    out = []
    for i in range(steps+1):
        t = i/steps
        x = y = 0
        for k, (px, py) in enumerate(points):
            c = math.comb(n, k)*(1-t)**(n-k)*t**k
            x += c*px
            y += c*py
        out.append((x, y))
    return out


def _haze(color, amount, toward=(255, 228, 176)):
    return tuple(round(c+(t-c)*amount) for c, t in zip(color, toward))


def _dune(surface, peak, left, right, base, shadow, lit):
    px, py = peak
    h = base-py
    left_edge = _bezier([(left, base), (px-(px-left)*0.42, py+h*0.22), (px, py)])
    right_edge = _bezier([(px, py), (px+(right-px)*0.4, py+h*0.18), (right, base)])
    pygame.draw.polygon(surface, shadow, left_edge+right_edge[1:])
    ridge = _bezier([(px, py), (px+(right-px)*0.04, py+h*0.55), (px+(right-px)*0.22, base-h*0.08), (px+(right-px)*0.6, base)])
    pygame.draw.polygon(surface, lit, ridge+right_edge[::-1][:-1])


def _tower(surface, x, base, scale, haze, unit):
    k = scale*SS*unit
    c = lambda col: _haze(col, haze)
    h, wb, wt = 118*k, 46*k, 38*k
    top = base-h
    pygame.draw.polygon(surface, c(SAND_SHADOW), [(x-wb/2, base), (x+wb/2, base), (x+wt/2, top), (x-wt/2, top)])
    pygame.draw.polygon(surface, c(SAND_LIT), [(x-wb*0.08, base), (x+wb/2, base), (x+wt/2, top), (x-wt*0.08, top)])
    for i in range(1, 6):
        y = top+h*i/6
        inset = (wb-wt)/2*(1-i/6)
        pygame.draw.line(surface, c((188, 134, 74)), (x-wb/2+inset, y), (x+wb/2-inset, y), max(1, int(k)))
    pw, ph, mh = 52*k, 14*k, 9*k
    pygame.draw.rect(surface, c(SAND_SHADOW), (x-pw/2, top-ph, pw, ph))
    pygame.draw.rect(surface, c(SAND_LIT), (x-pw*0.08, top-ph, pw*0.58, ph))
    pygame.draw.rect(surface, c((176, 120, 62)), (x-pw/2, top-2*k, pw, 3*k))
    mw = pw/7
    for i in range(0, 7, 2):
        mx = x-pw/2+i*mw
        pygame.draw.rect(surface, c(SAND_LIT if mx >= x-pw*0.1 else SAND_SHADOW), (mx, top-ph-mh, mw, mh))
    for wy in (top+h*0.28, top+h*0.62):
        pygame.draw.rect(surface, c(DARK_STONE), (x-3.5*k, wy, 7*k, 16*k), border_radius=int(3.5*k))
    pygame.draw.rect(surface, c(DARK_STONE), (x-8*k, base-22*k, 16*k, 22*k),
                     border_top_left_radius=int(8*k), border_top_right_radius=int(8*k))
    pole_bottom, pole_top = top-ph-mh, top-ph-mh-30*k
    pygame.draw.line(surface, c(DARK_STONE), (x, pole_bottom), (x, pole_top), max(1, int(2*k)))
    pygame.draw.polygon(surface, c(FLAG), [(x+k, pole_top), (x+22*k, pole_top+6*k), (x+k, pole_top+12*k)])


def _car(surface, x, y, scale, haze, unit):
    k = scale*SS*unit
    c = lambda col: _haze(col, haze)
    w, h = 34*k, 16*k
    pygame.draw.ellipse(surface, c((150, 100, 50)), (x-w*0.6, y-3*k, w*1.2, 7*k))
    for wx in (x-w*0.36, x+w*0.36):
        pygame.draw.rect(surface, c((30, 28, 30)), (wx-4*k, y-7*k, 8*k, 8*k), border_radius=int(2*k))
    pygame.draw.rect(surface, c(CAR), (x-w/2, y-h-3*k, w, h), border_radius=int(5*k))
    pygame.draw.rect(surface, c(tuple(int(v*0.78) for v in CAR)), (x-w*0.34, y-h-12*k, w*0.68, 11*k),
                     border_top_left_radius=int(6*k), border_top_right_radius=int(6*k))
    pygame.draw.rect(surface, c((64, 84, 120)), (x-w*0.27, y-h-9*k, w*0.54, 7*k), border_radius=int(2*k))
    for lx in (x-w*0.38, x+w*0.38):
        pygame.draw.rect(surface, c((255, 214, 120)), (lx-3*k, y-h+2*k, 6*k, 3*k))


def _road(surface, W, H, horizon_frac, unit):
    horizon, bottom = horizon_frac*H, 1.04*H
    lift = bottom-horizon
    half = 0.11*W
    distant = (240, 196, 120)

    def project(z, offset=0.0):
        sway = W*(-0.2+0.42*math.sin(0.5*(z-1)))
        return W*0.5+(sway+offset)/z, horizon+lift/z

    zs = [14*(1/14)**(i/240) for i in range(241)]
    for edge, color in ((1.12, ROAD_EDGE), (1.0, ASPHALT)):
        for z0, z1 in zip(zs, zs[1:]):
            shade = _haze(color, min(0.8, (z0-1)/11), distant)
            pygame.draw.polygon(surface, shade, [project(z0, -half*edge), project(z0, half*edge),
                                                 project(z1, half*edge), project(z1, -half*edge)])
    for z0, z1 in zip(zs, zs[1:]):
        if int(z0*2.2) % 2 == 0 and z0 < 7:
            pygame.draw.line(surface, _haze(ROAD_LINE, (z0-1)/9, distant), project(z0), project(z1), max(1, round(5*SS*unit/z1)))
    return project


def _sun(surface, x, y, r):
    halo = r*2.6
    glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for k in range(20, 0, -1):
        alpha = round(255*(1-(1-6/255)**(21-k)))
        pygame.draw.circle(glow, (255, 244, 210, alpha), (x, y), r+(halo-r)*k/20)
    surface.blit(glow, (0, 0))
    pygame.draw.circle(surface, SUN, (x, y), r)


@lru_cache(maxsize=8)
def desert_scene(size, layout='wide', unit=1.0):
    w, h = size
    W, H = w*SS, h*SS
    spec = SCENES[layout]
    big = pygame.Surface((W, H), depth=24)
    top, bottom = spec['sky']
    for y in range(H):
        t = (y/H)**1.4
        big.fill([round(a+(b-a)*t) for a, b in zip(top, bottom)], (0, y, W, 1))
    sx, sy, sr = spec['sun']
    _sun(big, sx*W, sy*H, sr*SS*unit)
    dunes, layers = spec['dunes'], spec['layers']
    per_layer = math.ceil(len(dunes)/len(layers))
    for i, ((px, py), left, right) in enumerate(dunes):
        layer = min(i//per_layer, len(layers)-1)
        if layer == len(layers)-1 and i % per_layer == 0:
            for tx, ty, scale in spec.get('far_towers', ()):
                _tower(big, tx*W, ty*H, scale, 0.45, unit)
        shadow, lit = layers[layer]
        _dune(big, (px*W, py*H), left*W, right*W, H*1.02, shadow, lit)
    if 'road_horizon' in spec:
        project = _road(big, W, H, spec['road_horizon'], unit)
        items = [(project(z, 0.045*W)[1], 'car', project(z, 0.045*W)[0], 1.5/z) for z in spec['cars']]
        items += [(ty*H, 'tower', tx*W, scale) for tx, ty, scale in spec['near_towers']]
        for y, kind, x, scale in sorted(items):
            if kind == 'car':
                _car(big, x, y, max(0.18, scale), max(0.0, 0.5-scale*0.4), unit)
            else:
                _tower(big, x, y, scale, max(0.0, 0.35-scale*0.35), unit)
    return pygame.transform.smoothscale(big, size)