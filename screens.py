import pygame

import ui
from backend import DIFFICULTY_NAMES, LEADERBOARD_SIZE, AccessDenied, AccountError
from game_screen import DIFFICULTIES, DIFFICULTY_STYLE, MAP_IMAGE, GameScreen
from game_session import format_time
from ui import Button, Form, TextInput, Toggle


def pressed_enter(event):
    return event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)


def pressed_escape(event):
    return event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE


class App:
    def __init__(self, backend):
        self.screen, self.present = ui.setup_display('KARZ Tower Defense')
        pygame.key.set_repeat(350, 35)
        pygame.key.start_text_input()
        self.clock = pygame.time.Clock()
        self.backend = backend
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

    def play(self, difficulty, sandbox=False):
        record = None if sandbox else (lambda result: self.backend.record_run(self.account, result))
        self.go(GameScreen(difficulty, on_exit=lambda: self.go(MapSelectScreen(self)), on_finish=record, sandbox=sandbox))

    def run(self, frames=None):
        count = 0
        while self.running and (frames is None or count < frames):
            dt = min(self.clock.tick(60)/1000, 0.05)
            for event in pygame.event.get():
                ui.track_mouse(event)
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
            self.app.log_in(self.app.backend.log_in(self.email.value, self.password.value))
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
            self.app.log_in(self.app.backend.sign_up(*self.form.values()))
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
        self.play = Button((370, 312, 220, 64), 'Play', 'hero')
        self.leaderboard = Button((370, 396, 220, 44), 'Leaderboard', 'secondary')
        self.accounts = Button((370, 452, 220, 44), 'All accounts', 'secondary') if app.account.is_admin else None

    def handle(self, event):
        if self.settings.clicked(event):
            self.app.go(SettingsScreen(self.app))
        elif self.play.clicked(event) or pressed_enter(event):
            self.app.go(MapSelectScreen(self.app))
        elif self.leaderboard.clicked(event):
            self.app.go(LeaderboardScreen(self.app))
        elif self.accounts is not None and self.accounts.clicked(event):
            self.app.go(AdminScreen(self.app))

    def update(self, dt):
        pass

    def draw(self, screen, interactive=True):
        ui.background(screen)
        ui.text(screen, 'KARZ', 18, ui.ON_BG, (28, 26), bold=True, tracking=5)
        signed_in = ui.text(screen, f'Signed in as {self.app.account.name}', 13, ui.ON_BG_SOFT, (28, 50))
        if self.app.account.is_admin:
            ui.chip(screen, 'ADMIN', ui.BUTTON, (signed_in.right/ui.S+8, 47))
        ui.text(screen, 'KARZ', 84, ui.ON_BG, (480, 194), bold=True, anchor='center', tracking=22)
        ui.text(screen, 'TOWER DEFENSE', 16, ui.ON_BG_SOFT, (480, 252), anchor='center', tracking=8)
        hover = None if interactive else False
        for button in (self.settings, self.play, self.leaderboard, self.accounts):
            if button is not None:
                button.draw(screen, hover)


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
            self.app.account = self.app.backend.update_account(
                self.app.account, self.current_password.value, self.name.value,
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
        self.unlocked = app.backend.unlocked_difficulties(app.account)
        self.thumb = ui.load_image(MAP_IMAGE, (176, 106), radius=8)
        self.locked_thumb = self.thumb.copy()
        self.locked_thumb.fill((120, 110, 100, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.hint = ''

    def is_open(self, difficulty):
        return difficulty['name'] in self.unlocked

    @staticmethod
    def buttons(rect):
        return pygame.Rect(rect.x+16, rect.y+234, 80, 32), pygame.Rect(rect.x+104, rect.y+234, 80, 32)

    def handle(self, event):
        if self.back.clicked(event) or pressed_escape(event):
            self.app.go(HomeScreen(self.app))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, (rect, difficulty) in enumerate(zip(self.cards, DIFFICULTIES)):
                if not rect.collidepoint(event.pos):
                    continue
                if not self.is_open(difficulty):
                    self.hint = f'Beat {DIFFICULTY_NAMES[i-1]} to unlock {difficulty["name"]}.'
                    return
                play, sandbox = self.buttons(rect.move(0, -6))
                if play.collidepoint(event.pos):
                    self.app.play(difficulty)
                elif sandbox.collidepoint(event.pos):
                    self.app.play(difficulty, sandbox=True)

    def update(self, dt):
        pass

    def draw(self, screen):
        ui.background(screen)
        self.back.draw(screen)
        ui.text(screen, 'Choose a difficulty', 32, ui.ON_BG, (480, 74), bold=True, anchor='center')
        if self.app.account.is_admin:
            subtitle = 'Admin: every difficulty is unlocked.'
        else:
            subtitle = self.hint or 'Beat a difficulty to unlock the next one and its sandbox.'
        ui.text(screen, subtitle, 14, ui.ON_BG_SOFT, (480, 112), anchor='center')
        mouse = ui.mouse_pos()
        for i, (rect, difficulty) in enumerate(zip(self.cards, DIFFICULTIES)):
            open_ = self.is_open(difficulty)
            hover = open_ and rect.collidepoint(mouse)
            r = rect.move(0, -6) if hover else rect
            ui.card(screen, r, 12)
            ui.blit(screen, self.thumb if open_ else self.locked_thumb, (r.x+12, r.y+12))
            if not open_:
                ui.circle(screen, (r.x+100, r.y+65), 22, (255, 250, 240))
                ui.icon(screen, 'lock', ui.INK, 22, (r.x+100, r.y+64))
            ui.chip(screen, difficulty['name'].upper(), difficulty['color'] if open_ else (178, 166, 150), (r.x+16, r.y+134))
            ui.text(screen, 'Desert Highway', 17, ui.NAVY if open_ else (150, 136, 118), (r.x+16, r.y+168), bold=True)
            blurb = difficulty['blurb'] if open_ else f'Beat {DIFFICULTY_NAMES[i-1]} to unlock.'
            for j, line in enumerate(ui.wrap(blurb, 13, 168)):
                ui.text(screen, line, 13, ui.MUTED, (r.x+16, r.y+196+j*18))
            if open_:
                play, sandbox = self.buttons(r)
                Button(play, 'Play').draw(screen)
                Button(sandbox, 'Sandbox', 'secondary').draw(screen)
            else:
                Button((r.x+16, r.y+234, 168, 32), 'Locked', 'disabled').draw(screen, False)


BOARD_TABS = (('score', 'Top score'), ('time', 'Best time'), ('lives', 'Fewest lives lost'))
BOARD_COLUMN = {'score': 'Score', 'time': 'Time', 'lives': 'Lives lost'}
MEDALS = ((222, 172, 48), (168, 172, 180), (196, 128, 72))


class LeaderboardScreen:
    def __init__(self, app):
        self.app = app
        self.back = Button((24, 22, 46, 46), '', 'ghost', 'back')
        self.tabs = [pygame.Rect(240+i*164, 96, 156, 36) for i in range(len(BOARD_TABS))]
        self.filters = [pygame.Rect(270+i*86, 144, 78, 26) for i in range(len(DIFFICULTY_NAMES)+1)]
        self.kind, self.difficulty = 'score', None
        self.load()

    def load(self):
        self.entries = self.app.backend.leaderboard(self.kind, self.difficulty)

    def handle(self, event):
        if self.back.clicked(event) or pressed_escape(event):
            self.app.go(HomeScreen(self.app))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, (kind, _) in zip(self.tabs, BOARD_TABS):
                if rect.collidepoint(event.pos):
                    self.kind = kind
                    self.load()
            for rect, difficulty in zip(self.filters, (None,)+DIFFICULTY_NAMES):
                if rect.collidepoint(event.pos):
                    self.difficulty = difficulty
                    self.load()

    def update(self, dt):
        pass

    def value(self, entry):
        if self.kind == 'score':
            return f'{int(entry.value):,}'
        if self.kind == 'time':
            return format_time(entry.value)
        return str(int(entry.value))

    def draw(self, screen):
        ui.background(screen)
        self.back.draw(screen)
        ui.text(screen, 'Leaderboard', 30, ui.ON_BG, (480, 58), bold=True, anchor='center')
        mouse = ui.mouse_pos()
        for rect, (kind, label) in zip(self.tabs, BOARD_TABS):
            active = kind == self.kind
            fill = ui.BUTTON if active else (ui.PAPER_HOVER if rect.collidepoint(mouse) else ui.PAPER)
            ui.rounded(screen, rect, fill, 18, None if active else ui.PAPER_EDGE, 0 if active else 1)
            ui.text(screen, label, 14, ui.WHITE if active else ui.INK, rect.center, bold=True, anchor='center')
        for rect, difficulty in zip(self.filters, (None,)+DIFFICULTY_NAMES):
            active = difficulty == self.difficulty
            color = DIFFICULTY_STYLE[difficulty][0] if difficulty else ui.BUTTON
            ui.rounded(screen, rect, color if active else (255, 250, 240, 200), 13, None if active else color, 0 if active else 1)
            ui.text(screen, difficulty or 'All', 12, ui.WHITE if active else color, rect.center, bold=True, anchor='center')
        card = pygame.Rect(150, 182, 660, 446)
        ui.card(screen, card, 12)
        columns = ((174, '#'), (214, 'Player'), (470, BOARD_COLUMN[self.kind]), (586, 'Difficulty'), (700, 'Date'))
        for x, label in columns:
            ui.text(screen, label.upper(), 11, ui.MUTED, (x, 194), bold=True, tracking=1)
        ui.line(screen, ui.PAPER_EDGE, (166, 214), (794, 214))
        if not self.entries:
            message = 'No games yet. Play one to get on the board!' if self.kind == 'score' else 'No wins yet. Beat a level to get on the board!'
            ui.text(screen, message, 15, ui.MUTED, (480, 400), anchor='center')
        for i, entry in enumerate(self.entries):
            y = 220+i*16.2
            mine = entry.username == self.app.account.username
            if mine:
                ui.rounded(screen, (162, y-1, 636, 16), (228, 236, 250), 6)
            if entry.rank <= 3:
                ui.circle(screen, (180, y+7), 7, MEDALS[entry.rank-1])
                ui.text(screen, str(entry.rank), 10, ui.WHITE, (180, y+7), bold=True, anchor='center')
            else:
                ui.text(screen, str(entry.rank), 12, ui.MUTED, (180, y+7), anchor='center')
            ui.text(screen, entry.username, 12, ui.NAVY, (214, y), bold=mine)
            ui.text(screen, self.value(entry), 12, ui.NAVY, (470, y), bold=True)
            ui.text(screen, entry.difficulty, 12, DIFFICULTY_STYLE[entry.difficulty][0], (586, y), bold=True)
            ui.text(screen, entry.played_at[:10], 12, ui.MUTED, (700, y))
        ui.text(screen, f'Top {LEADERBOARD_SIZE} players, best result each', 11, ui.MUTED, (794, 612), anchor='topright')


class AdminScreen:
    ROW = 30
    VISIBLE = 13

    def __init__(self, app):
        self.app = app
        self.back = Button((24, 22, 46, 46), '', 'ghost', 'back')
        self.scroll = 0
        self.message, self.message_color = '', ui.ERROR
        self.load()

    def load(self):
        try:
            self.summaries = self.app.backend.list_accounts(self.app.account)
        except AccessDenied as e:
            self.summaries = []
            self.message = str(e)
        self.scroll = max(0, min(self.scroll, len(self.summaries)-self.VISIBLE))

    def row_button(self, index):
        y = 172+(index-self.scroll)*self.ROW
        return pygame.Rect(812, y+2, 98, 24)

    def handle(self, event):
        if self.back.clicked(event) or pressed_escape(event):
            self.app.go(HomeScreen(self.app))
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.scroll-event.y, max(0, len(self.summaries)-self.VISIBLE)))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(self.scroll, min(len(self.summaries), self.scroll+self.VISIBLE)):
                summary = self.summaries[i]
                if summary.account.id != self.app.account.id and self.row_button(i).collidepoint(event.pos):
                    new_role = 'user' if summary.account.is_admin else 'admin'
                    try:
                        updated = self.app.backend.set_role(self.app.account, summary.account.id, new_role)
                        self.message, self.message_color = f'{updated.username} is now {"an admin" if updated.is_admin else "a user"}.', ui.SUCCESS
                    except (AccessDenied, AccountError) as e:
                        self.message, self.message_color = str(e), ui.ERROR
                    self.load()
                    return

    def update(self, dt):
        pass

    def draw(self, screen):
        ui.background(screen)
        self.back.draw(screen)
        ui.text(screen, 'All accounts', 30, ui.ON_BG, (480, 58), bold=True, anchor='center')
        admins = sum(s.account.is_admin for s in self.summaries)
        ui.text(screen, f'{len(self.summaries)} accounts · {admins} admin{"s" if admins != 1 else ""}', 14, ui.ON_BG_SOFT, (480, 94), anchor='center')
        ui.card(screen, (30, 122, 900, 488), 12)
        columns = ((48, 'Name'), (196, 'Username'), (330, 'Email'), (530, 'Role'), (602, 'Unlocked'), (692, 'Best'), (756, 'Games'), (812, ''))
        for x, label in columns:
            ui.text(screen, label.upper(), 11, ui.MUTED, (x, 136), bold=True, tracking=1)
        ui.line(screen, ui.PAPER_EDGE, (44, 160), (916, 160))
        mouse = ui.mouse_pos()
        for i in range(self.scroll, min(len(self.summaries), self.scroll+self.VISIBLE)):
            s, a = self.summaries[i], self.summaries[i].account
            y = 172+(i-self.scroll)*self.ROW
            me = a.id == self.app.account.id
            if me:
                ui.rounded(screen, (40, y-2, 880, 28), (228, 236, 250), 8)
            ui.text(screen, self.fit(a.name, 13, 140), 13, ui.NAVY, (48, y+6), bold=True)
            ui.text(screen, self.fit(a.username, 13, 126), 13, ui.INK, (196, y+6))
            ui.text(screen, self.fit(a.email, 13, 192), 13, ui.INK, (330, y+6))
            ui.chip(screen, 'ADMIN' if a.is_admin else 'USER', ui.BUTTON if a.is_admin else (150, 140, 126), (530, y+3))
            top = s.unlocked[-1]
            ui.text(screen, top, 13, DIFFICULTY_STYLE[top][0], (602, y+6), bold=True)
            ui.text(screen, f'{s.best_score:,}', 13, ui.INK, (692, y+6))
            ui.text(screen, str(s.games_played), 13, ui.INK, (756, y+6))
            if me:
                ui.text(screen, 'You', 12, ui.MUTED, (861, y+8), anchor='midtop')
            else:
                button = Button(self.row_button(i), 'Make user' if a.is_admin else 'Make admin', 'small')
                button.draw(screen, button.rect.collidepoint(mouse))
        if len(self.summaries) > self.VISIBLE:
            shown = f'{self.scroll+1}-{min(len(self.summaries), self.scroll+self.VISIBLE)} of {len(self.summaries)} · scroll for more'
            ui.text(screen, shown, 12, ui.MUTED, (916, 590), anchor='topright')
        if self.message:
            ui.text(screen, self.message, 13, self.message_color, (48, 590))

    @staticmethod
    def fit(value, size, width):
        if ui.text_width(value, size) <= width:
            return value
        while value and ui.text_width(value+'…', size) > width:
            value = value[:-1]
        return value+'…'
