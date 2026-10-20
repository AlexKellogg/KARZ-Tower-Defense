import pygame

import ui
from accounts import AccountError
from game_screen import DIFFICULTIES, MAP_IMAGE, GameScreen
from ui import Button, Form, TextInput, Toggle


def pressed_enter(event):
    return event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)


def pressed_escape(event):
    return event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE


class App:
    def __init__(self, store):
        self.screen, self.present = ui.setup_display('KARZ Tower Defense')
        pygame.key.set_repeat(350, 35)
        pygame.key.start_text_input()
        self.clock = pygame.time.Clock()
        self.store = store
        self.account = None
        self.running = True
        self.current = LoginScreen(self)

    def go(self, screen):
        self.current = screen

    def log_in(self, account):
        self.account = account
        self.go(HomeScreen(self))

    def log_out(self):
        self.account = None
        self.go(LoginScreen(self))

    def play(self, difficulty):
        self.go(GameScreen(difficulty, on_exit=lambda: self.go(MapSelectScreen(self))))

    def run(self, frames=None):
        count = 0
        while self.running and (frames is None or count < frames):
            dt = min(self.clock.tick(60)/1000, 0.05)
            for event in pygame.event.get():
                if event.type in (pygame.QUIT, pygame.WINDOWCLOSE):
                    self.running = False
                else:
                    self.current.handle(event)
            self.current.update(dt)
            self.current.draw(self.screen)
            self.present()
            count += 1


class LoginScreen:
    def __init__(self, app):
        self.app = app
        self.email = TextInput((350, 330, 260, 42), 'Email', 'mail')
        self.password = TextInput((350, 384, 260, 42), 'Password', 'lock', secret=True)
        self.form = Form([self.email, self.password])
        self.show = Toggle((352, 440), 'Show password')
        self.submit = Button((350, 488, 260, 44), 'Log in')
        self.switch = Button((350, 550, 260, 24), 'New here? Create an account', 'link')
        self.error = ''
        self.email.focused = True

    def attempt(self):
        try:
            self.app.log_in(self.app.store.log_in(self.email.value, self.password.value))
        except AccountError as e:
            self.error = str(e)
            self.password.value = ''

    def handle(self, event):
        if self.show.clicked(event):
            self.password.reveal = self.show.on
        elif self.switch.clicked(event):
            self.app.go(SignUpScreen(self.app))
        elif self.submit.clicked(event) or pressed_enter(event):
            self.attempt()
        else:
            self.form.handle(event)

    def update(self, dt):
        self.form.update(dt)

    def draw(self, screen):
        ui.background(screen)
        ui.card_with_art(screen, (310, 36, 340, 568), 200)
        ui.text(screen, 'KARZ', 40, ui.WHITE, (480, 92), bold=True, anchor='center', tracking=10)
        ui.text(screen, 'TOWER DEFENSE', 11, (255, 246, 226), (480, 124), anchor='center', tracking=4)
        ui.text(screen, 'Welcome back', 26, ui.NAVY, (350, 260), bold=True)
        ui.text(screen, 'Log in to pick up where you left off.', 13, ui.MUTED, (350, 296))
        self.form.draw(screen)
        self.show.draw(screen)
        if self.error:
            ui.text(screen, self.error, 13, ui.ERROR, (480, 472), anchor='center')
        self.submit.draw(screen)
        self.switch.draw(screen)


class SignUpScreen:
    def __init__(self, app):
        self.app = app
        self.fields = [
            TextInput((350, 240, 260, 42), 'Name', 'user'),
            TextInput((350, 292, 260, 42), 'Username', 'at'),
            TextInput((350, 344, 260, 42), 'Email', 'mail'),
            TextInput((350, 396, 260, 42), 'Password (8+ characters)', 'lock', secret=True),
        ]
        self.form = Form(self.fields)
        self.show = Toggle((352, 452), 'Show password')
        self.submit = Button((350, 506, 260, 44), 'Sign up')
        self.switch = Button((350, 562, 260, 24), 'Already have an account? Log in', 'link')
        self.error = ''
        self.fields[0].focused = True

    def attempt(self):
        try:
            self.app.log_in(self.app.store.sign_up(*self.form.values()))
        except AccountError as e:
            self.error = str(e)

    def handle(self, event):
        if self.show.clicked(event):
            self.fields[3].reveal = self.show.on
        elif self.switch.clicked(event):
            self.app.go(LoginScreen(self.app))
        elif self.submit.clicked(event) or pressed_enter(event):
            self.attempt()
        elif pressed_escape(event):
            self.app.go(LoginScreen(self.app))
        else:
            self.form.handle(event)

    def update(self, dt):
        self.form.update(dt)

    def draw(self, screen):
        ui.background(screen)
        ui.card_with_art(screen, (310, 36, 340, 568), 112)
        ui.text(screen, 'KARZ', 30, ui.WHITE, (480, 84), bold=True, anchor='center', tracking=8)
        ui.text(screen, 'Create account', 26, ui.NAVY, (350, 170), bold=True)
        ui.text(screen, 'Save your progress across devices.', 13, ui.MUTED, (350, 206))
        self.form.draw(screen)
        self.show.draw(screen)
        if self.error:
            ui.text(screen, self.error, 13, ui.ERROR, (480, 486), anchor='center')
        self.submit.draw(screen)
        self.switch.draw(screen)


class HomeScreen:
    def __init__(self, app):
        self.app = app
        self.settings = Button((888, 22, 46, 46), '', 'ghost', 'gear')
        self.play = Button((370, 318, 220, 64), 'Play', 'hero')

    def handle(self, event):
        if self.settings.clicked(event):
            self.app.go(SettingsScreen(self.app))
        elif self.play.clicked(event) or pressed_enter(event):
            self.app.go(MapSelectScreen(self.app))

    def update(self, dt):
        pass

    def draw(self, screen, interactive=True):
        ui.background(screen)
        ui.text(screen, 'KARZ', 18, ui.ON_BG, (28, 26), bold=True, tracking=5)
        ui.text(screen, f'Signed in as {self.app.account.name}', 13, ui.ON_BG_SOFT, (28, 50))
        ui.text(screen, 'KARZ', 84, ui.ON_BG, (480, 200), bold=True, anchor='center', tracking=22)
        ui.text(screen, 'TOWER DEFENSE', 16, ui.ON_BG_SOFT, (480, 258), anchor='center', tracking=8)
        self.settings.draw(screen, None if interactive else False)
        self.play.draw(screen, None if interactive else False)


class SettingsScreen:
    def __init__(self, app):
        self.app = app
        self.home = HomeScreen(app)
        account = app.account
        self.name = TextInput((340, 136, 280, 42), 'Name', 'user', value=account.name)
        self.username = TextInput((340, 188, 280, 42), 'Username', 'at', value=account.username)
        self.email = TextInput((340, 240, 280, 42), 'Email', 'mail', value=account.email)
        self.new_password = TextInput((340, 292, 280, 42), 'New password (optional)', 'lock', secret=True)
        self.current_password = TextInput((340, 344, 280, 42), 'Current password', 'lock', secret=True)
        self.form = Form([self.name, self.username, self.email, self.new_password, self.current_password])
        self.cancel = Button((340, 432, 134, 44), 'Cancel', 'secondary')
        self.save = Button((486, 432, 134, 44), 'Save')
        self.logout = Button((340, 516, 280, 30), 'Log out', 'link')
        self.message, self.message_color = '', ui.ERROR

    def attempt(self):
        try:
            self.app.account = self.app.store.update(
                self.app.account.id, self.current_password.value, self.name.value,
                self.username.value, self.email.value, self.new_password.value)
            self.message, self.message_color = 'Changes saved.', ui.SUCCESS
            self.new_password.value = self.current_password.value = ''
        except AccountError as e:
            self.message, self.message_color = str(e), ui.ERROR

    def handle(self, event):
        if self.cancel.clicked(event) or pressed_escape(event):
            self.app.go(HomeScreen(self.app))
        elif self.save.clicked(event) or pressed_enter(event):
            self.attempt()
        elif self.logout.clicked(event):
            self.app.log_out()
        else:
            self.form.handle(event)

    def update(self, dt):
        self.form.update(dt)

    def draw(self, screen):
        self.home.draw(screen, interactive=False)
        ui.dim(screen, (70, 40, 10, 80))
        ui.card(screen, (300, 40, 360, 524))
        ui.text(screen, 'Account settings', 24, ui.NAVY, (340, 68), bold=True)
        ui.text(screen, 'Enter your current password to save changes.', 13, ui.MUTED, (340, 102))
        self.form.draw(screen)
        if self.message:
            ui.text(screen, self.message, 13, self.message_color, (480, 410), anchor='center')
        self.cancel.draw(screen)
        self.save.draw(screen)
        ui.line(screen, (236, 222, 196), (340, 500), (620, 500))
        self.logout.draw(screen)


class MapSelectScreen:
    def __init__(self, app):
        self.app = app
        self.back = Button((24, 22, 46, 46), '', 'ghost', 'back')
        self.cards = [pygame.Rect(44+i*224, 168, 200, 280) for i in range(len(DIFFICULTIES))]
        self.thumb = ui.load_image(MAP_IMAGE, (176, 106), radius=8)

    def handle(self, event):
        if self.back.clicked(event) or pressed_escape(event):
            self.app.go(HomeScreen(self.app))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, difficulty in zip(self.cards, DIFFICULTIES):
                if rect.collidepoint(event.pos):
                    self.app.play(difficulty)

    def update(self, dt):
        pass

    def draw(self, screen):
        ui.background(screen)
        self.back.draw(screen)
        ui.text(screen, 'Choose a difficulty', 32, ui.ON_BG, (480, 74), bold=True, anchor='center')
        ui.text(screen, 'Every difficulty uses the Desert Highway map for now.', 14, ui.ON_BG_SOFT, (480, 112), anchor='center')
        mouse = pygame.mouse.get_pos()
        for rect, difficulty in zip(self.cards, DIFFICULTIES):
            hover = rect.collidepoint(mouse)
            r = rect.move(0, -6) if hover else rect
            ui.card(screen, r, 12)
            ui.blit(screen, self.thumb, (r.x+12, r.y+12))
            ui.chip(screen, difficulty['name'].upper(), difficulty['color'], (r.x+16, r.y+134))
            ui.text(screen, 'Desert Highway', 17, ui.NAVY, (r.x+16, r.y+168), bold=True)
            for i, line in enumerate(ui.wrap(difficulty['blurb'], 13, 168)):
                ui.text(screen, line, 13, ui.MUTED, (r.x+16, r.y+196+i*18))
            Button((r.x+16, r.y+234, 168, 32), 'Play', 'primary' if hover else 'secondary').draw(screen, hover)