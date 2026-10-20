import math
from functools import lru_cache

import pygame

from scenery import desert_scene

WIDTH, HEIGHT = 960, 640
SS = 2
S = 1.0

NAVY = (26, 42, 88)
INK = (78, 54, 28)
MUTED = (146, 112, 72)
PAPER = (255, 250, 240)
PAPER_HOVER = (250, 236, 210)
PAPER_EDGE = (226, 202, 160)
FIELD = (78, 110, 178)
FIELD_FOCUS = (58, 88, 156)
FIELD_HINT = (214, 226, 248)
BUTTON = (30, 50, 104)
BUTTON_HOVER = (44, 70, 138)
GOLD_TEXT = (255, 214, 120)
WHITE = (255, 255, 255)
ERROR = (190, 58, 46)
SUCCESS = (70, 130, 60)
ON_BG = (30, 50, 104)
ON_BG_SOFT = (150, 104, 52)

FONT_STACK = 'avenirnext,avenir,segoeui,inter,helveticaneue,arial'


def setup_display(title):
    global S
    try:
        from pygame._sdl2.video import Renderer, Texture
        pygame.display.set_mode((1, 1), pygame.HIDDEN)
        window = pygame.Window(title, (WIDTH, HEIGHT), allow_high_dpi=True)
        renderer = Renderer(window)
        S = max(1.0, renderer.get_viewport().w/WIDTH)
        canvas = pygame.Surface((px(WIDTH), px(HEIGHT)))
        texture = Texture(renderer, canvas.get_size(), streaming=True)

        def present():
            texture.update(canvas)
            renderer.blit(texture)
            renderer.present()
        return canvas, present
    except (pygame.error, AttributeError, ImportError, TypeError):
        S = 1.0
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(title)
        return screen, pygame.display.flip


def px(value):
    return int(round(value*S))


def scaled(rect):
    r = pygame.Rect(rect)
    return pygame.Rect(px(r.x), px(r.y), px(r.right)-px(r.x), px(r.bottom)-px(r.y))


@lru_cache(maxsize=None)
def _font(pixel_size, bold):
    return pygame.font.SysFont(FONT_STACK, pixel_size, bold=bold)


def font(size, bold=False):
    return _font(px(size), bold)


def text(surface, value, size, color, pos, bold=False, anchor='topleft', tracking=0):
    f = font(size, bold)
    if tracking:
        glyphs = [f.render(ch, True, color) for ch in value]
        width = sum(g.get_width() for g in glyphs)+px(tracking)*(len(glyphs)-1)
        image = pygame.Surface((max(1, width), f.get_height()), pygame.SRCALPHA)
        x = 0
        for g in glyphs:
            image.blit(g, (x, 0))
            x += g.get_width()+px(tracking)
    else:
        image = f.render(value, True, color)
    rect = image.get_rect(**{anchor: (px(pos[0]), px(pos[1]))})
    surface.blit(image, rect)
    return rect


def text_width(value, size, bold=False):
    return font(size, bold).size(value)[0]/S


def wrap(value, size, width):
    lines, line = [], ''
    for word in value.split():
        candidate = f'{line} {word}'.strip()
        if line and text_width(candidate, size) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    return lines+[line]


@lru_cache(maxsize=256)
def _rounded(size, radius, color, border_color=None, border=0):
    w, h = size
    big = pygame.Surface((w*SS, h*SS), pygame.SRCALPHA)
    if border:
        pygame.draw.rect(big, border_color, big.get_rect(), border_radius=radius*SS)
        inner = big.get_rect().inflate(-border*2*SS, -border*2*SS)
        pygame.draw.rect(big, color, inner, border_radius=max(0, radius-border)*SS)
    else:
        pygame.draw.rect(big, color, big.get_rect(), border_radius=radius*SS)
    return pygame.transform.smoothscale(big, size)


def rounded(surface, rect, color, radius, border_color=None, border=0):
    r = scaled(rect)
    border = max(1, px(border)) if border else 0
    surface.blit(_rounded(r.size, px(radius), tuple(color), border_color and tuple(border_color), border), r)


def rounded_image(image, radius):
    clipped = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    clipped.blit(image, (0, 0))
    clipped.blit(_rounded(image.get_size(), px(radius), WHITE), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return clipped


def load_image(path, size, radius=0):
    image = pygame.transform.smoothscale(pygame.image.load(str(path)), (px(size[0]), px(size[1])))
    return rounded_image(image, radius) if radius else image


def blit(surface, image, pos):
    surface.blit(image, (px(pos[0]), px(pos[1])))


@lru_cache(maxsize=64)
def _circle(radius, color):
    big = pygame.Surface((radius*2*SS, radius*2*SS), pygame.SRCALPHA)
    pygame.draw.circle(big, color, (radius*SS, radius*SS), radius*SS)
    return pygame.transform.smoothscale(big, (radius*2, radius*2))


def circle(surface, center, radius, color):
    r = px(radius)
    surface.blit(_circle(r, tuple(color)), (px(center[0])-r, px(center[1])-r))


def line(surface, color, start, end, width=1):
    pygame.draw.line(surface, color, (px(start[0]), px(start[1])), (px(end[0]), px(end[1])), max(1, px(width)))


def dim(surface, color):
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    layer.fill(color)
    surface.blit(layer, (0, 0))


@lru_cache(maxsize=None)
def _icon(name, color, size):
    s = size*4
    big = pygame.Surface((s, s), pygame.SRCALPHA)
    w = max(2, s//11)
    if name == 'user':
        pygame.draw.circle(big, color, (s//2, s*0.32), s*0.18, w)
        pygame.draw.arc(big, color, (s*0.16, s*0.58, s*0.68, s*0.7), 0, math.pi, w)
    elif name == 'lock':
        pygame.draw.rect(big, color, (s*0.2, s*0.44, s*0.6, s*0.46), w, border_radius=s//12)
        pygame.draw.arc(big, color, (s*0.32, s*0.1, s*0.36, s*0.48), 0, math.pi, w)
        pygame.draw.line(big, color, (s*0.32, s*0.34), (s*0.32, s*0.46), w)
        pygame.draw.line(big, color, (s*0.68-w/2, s*0.34), (s*0.68-w/2, s*0.46), w)
    elif name == 'mail':
        pygame.draw.rect(big, color, (s*0.12, s*0.24, s*0.76, s*0.52), w, border_radius=s//14)
        pygame.draw.lines(big, color, False, [(s*0.14, s*0.28), (s*0.5, s*0.54), (s*0.86, s*0.28)], w)
    elif name == 'at':
        pygame.draw.circle(big, color, (s//2, s//2), s*0.36, w)
        pygame.draw.circle(big, color, (s//2, s//2), s*0.14, w)
    elif name == 'gear':
        c = s//2
        for k in range(8):
            a = k*math.pi/4
            pygame.draw.line(big, color, (c+math.cos(a)*s*0.22, c+math.sin(a)*s*0.22),
                             (c+math.cos(a)*s*0.42, c+math.sin(a)*s*0.42), int(w*1.6))
        pygame.draw.circle(big, color, (c, c), s*0.3)
        pygame.draw.circle(big, (0, 0, 0, 0), (c, c), s*0.12)
    elif name == 'back':
        pygame.draw.lines(big, color, False, [(s*0.62, s*0.2), (s*0.32, s*0.5), (s*0.62, s*0.8)], w+2)
    return pygame.transform.smoothscale(big, (size, size))


def icon(surface, name, color, size, center):
    image = _icon(name, tuple(color), px(size))
    surface.blit(image, image.get_rect(center=(px(center[0]), px(center[1]))))


def background(surface):
    surface.blit(desert_scene((px(WIDTH), px(HEIGHT)), 'wide', S), (0, 0))


@lru_cache(maxsize=8)
def _soft_shadow(size, radius, spread, alpha=80):
    w, h = size[0]+spread*2, size[1]+spread*2
    small = pygame.Surface((max(1, w//6), max(1, h//6)), pygame.SRCALPHA)
    pygame.draw.rect(small, (90, 50, 10, alpha), small.get_rect().inflate(-spread//3*2, -spread//3*2), border_radius=radius//6)
    for _ in range(2):
        half = (max(1, small.get_width()//2), max(1, small.get_height()//2))
        small = pygame.transform.smoothscale(pygame.transform.smoothscale(small, half), small.get_size())
    return pygame.transform.smoothscale(small, (w, h))


def card(surface, rect, radius=14):
    r = scaled(rect)
    surface.blit(_soft_shadow(r.size, px(radius), px(18)), (r.x-px(18), r.y-px(10)))
    rounded(surface, rect, PAPER, radius)


def card_with_art(surface, rect, art_height, radius=14):
    card(surface, rect, radius)
    r = scaled(rect)
    h = px(art_height)
    art = desert_scene((r.w, h), 'card', S)
    mask = _rounded((r.w, h+px(radius)*2), px(radius), WHITE)
    clipped = pygame.Surface((r.w, h), pygame.SRCALPHA)
    clipped.blit(art, (0, 0))
    clipped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(clipped, r.topleft)


def chip(surface, label, color, pos, anchor='topleft'):
    width = round(text_width(label, 11, True))+len(label)*2+20
    rect = pygame.Rect(0, 0, width, 22)
    setattr(rect, anchor, pos)
    rounded(surface, rect, color, 11)
    text(surface, label, 11, WHITE, rect.center, bold=True, anchor='center', tracking=2)
    return rect


class TextInput:
    def __init__(self, rect, placeholder, icon_name, secret=False, value=''):
        self.rect = pygame.Rect(rect)
        self.placeholder = placeholder
        self.icon_name = icon_name
        self.secret = secret
        self.value = value
        self.focused = False
        self.reveal = False
        self.blink = 0.0

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.focused = self.rect.collidepoint(event.pos)
            self.blink = 0
        elif self.focused and event.type == pygame.TEXTINPUT:
            if len(self.value) < 64:
                self.value += event.text
            self.blink = 0
        elif self.focused and event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
            if event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META | pygame.KMOD_ALT):
                self.value = ''
            else:
                self.value = self.value[:-1]
            self.blink = 0

    def update(self, dt):
        self.blink = (self.blink+dt) % 1.0

    def draw(self, surface):
        r = self.rect
        rounded(surface, r, FIELD_FOCUS if self.focused else FIELD, r.h//2)
        icon(surface, self.icon_name, WHITE, 16, (r.x+24, r.centery))
        x0, right = px(r.x+44), px(r.right-18)
        width = right-x0
        shown = '•'*len(self.value) if self.secret and not self.reveal else self.value
        image = font(15).render(shown or self.placeholder, True, WHITE if shown else FIELD_HINT)
        offset = max(0, image.get_width()-width) if shown else 0
        cy = px(r.centery)
        surface.blit(image, (x0, cy-image.get_height()//2), (offset, 0, width, image.get_height()))
        if self.focused and self.blink < 0.55:
            cx = x0+min(image.get_width() if shown else 0, width)+px(1)
            pygame.draw.line(surface, WHITE, (cx, cy-px(9)), (cx, cy+px(9)), max(1, px(2)))


class Button:
    def __init__(self, rect, label, style='primary', icon_name=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.style = style
        self.icon_name = icon_name

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

    def draw(self, surface, hover=None):
        r = self.rect
        if hover is None:
            hover = r.collidepoint(pygame.mouse.get_pos())
        if self.style == 'primary':
            rounded(surface, r, BUTTON_HOVER if hover else BUTTON, 8)
            text(surface, self.label.upper(), 14, WHITE, r.center, bold=True, anchor='center', tracking=2)
        elif self.style == 'hero':
            rounded(surface, r.move(0, 4), (16, 28, 64), r.h//2)
            rounded(surface, r, BUTTON_HOVER if hover else BUTTON, r.h//2)
            text(surface, self.label.upper(), 22, GOLD_TEXT, r.center, bold=True, anchor='center', tracking=5)
        elif self.style == 'ghost':
            rounded(surface, r, (255, 255, 255, 150 if hover else 90), r.h//2, (*ON_BG, 70), 1)
            icon(surface, self.icon_name, ON_BG, 20, r.center)
        elif self.style == 'secondary':
            rounded(surface, r, PAPER_HOVER if hover else PAPER, 8, PAPER_EDGE, 1)
            text(surface, self.label.upper(), 14, INK, r.center, bold=True, anchor='center', tracking=2)
        else:
            rect = text(surface, self.label, 14, BUTTON, r.center, anchor='center')
            if hover:
                pygame.draw.line(surface, BUTTON, rect.bottomleft, rect.bottomright, max(1, px(1)))


class Toggle:
    def __init__(self, pos, label, on=False):
        self.track = pygame.Rect(pos[0], pos[1], 30, 16)
        self.label = label
        self.on = on
        self.rect = pygame.Rect(pos[0], pos[1]-4, 160, 24)

    def clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.on = not self.on
            return True
        return False

    def draw(self, surface):
        t = self.track
        rounded(surface, t, BUTTON if self.on else (226, 206, 170), t.h//2)
        circle(surface, (t.right-8 if self.on else t.x+8, t.centery), 6, WHITE)
        text(surface, self.label, 13, MUTED, (t.right+10, t.centery), anchor='midleft')


class Form:
    def __init__(self, inputs):
        self.inputs = inputs

    def values(self):
        return [f.value for f in self.inputs]

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            focused = next((i for i, f in enumerate(self.inputs) if f.focused), -1)
            step = -1 if event.mod & pygame.KMOD_SHIFT else 1
            for f in self.inputs:
                f.focused = False
            self.inputs[(focused+step) % len(self.inputs)].focused = True
            return
        for f in self.inputs:
            f.handle(event)

    def update(self, dt):
        for f in self.inputs:
            f.update(dt)

    def draw(self, surface):
        for f in self.inputs:
            f.draw(surface)