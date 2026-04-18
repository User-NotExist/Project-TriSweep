import pygame

from components.scene_base import SceneBase


class MainMenu(SceneBase):
    def __init__(self):
        super().__init__()
        self.title_text = "Project TriSweep"

        self.background_color = (18, 22, 31)
        self.panel_color = (26, 31, 43)
        self.panel_border_color = (73, 86, 114)
        self.title_color = (240, 244, 252)
        self.subtitle_color = (167, 176, 197)
        self.button_color = (39, 47, 64)
        self.button_hover_color = (71, 128, 245)
        self.button_border_color = (95, 110, 142)
        self.button_text_color = (240, 244, 252)

        self.title_font = self._create_font(56, bold=True)
        self.subtitle_font = self._create_font(20)
        self.button_font = self._create_font(30, bold=True)

        self.button_size = (320, 62)
        self.button_gap = 14
        self.button_order = [("play", "Play"), ("setting", "Setting"), ("exit", "Exit")]

        self.title_surface = None
        self.subtitle_surface = None
        self.title_rect = pygame.Rect(0, 0, 0, 0)
        self.subtitle_rect = pygame.Rect(0, 0, 0, 0)
        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.button_rects = {
            "play": pygame.Rect(0, 0, 0, 0),
            "setting": pygame.Rect(0, 0, 0, 0),
            "exit": pygame.Rect(0, 0, 0, 0),
        }
        self.hovered_button = None
        self.layout_size = (0, 0)

    def _create_font(self, size, bold=False):
        candidates = [
            "meiryo",
            "yu gothic ui",
            "yugothic",
            "ms gothic",
            "msgothic",
            "noto sans cjk jp",
            "arial unicode ms",
            "segoe ui",
            "arial",
        ]
        for name in candidates:
            font_path = pygame.font.match_font(name)
            if font_path:
                font = pygame.font.Font(font_path, size)
                font.set_bold(bold)
                return font

        fallback = pygame.font.SysFont(None, size)
        fallback.set_bold(bold)
        return fallback

    def _build_layout(self, width, height):
        self.layout_size = (width, height)

        panel_width = min(740, max(420, width - 120))
        panel_height = min(540, max(360, height - 120))
        self.panel_rect = pygame.Rect(
            (width - panel_width) // 2,
            (height - panel_height) // 2,
            panel_width,
            panel_height,
        )

        self.title_surface = self.title_font.render(self.title_text, True, self.title_color)
        self.title_rect = self.title_surface.get_rect(centerx=self.panel_rect.centerx, y=self.panel_rect.y + 56)

        self.subtitle_surface = self.subtitle_font.render(
            "3 lane VSRG thing",
            True,
            self.subtitle_color,
        )
        self.subtitle_rect = self.subtitle_surface.get_rect(centerx=self.panel_rect.centerx, y=self.title_rect.bottom + 10)

        button_w, button_h = self.button_size
        total_buttons_height = (len(self.button_order) * button_h) + ((len(self.button_order) - 1) * self.button_gap)
        start_y = self.panel_rect.y + self.panel_rect.height - total_buttons_height - 64

        for index, (key, _) in enumerate(self.button_order):
            y = start_y + index * (button_h + self.button_gap)
            self.button_rects[key] = pygame.Rect((self.panel_rect.centerx - (button_w // 2)), y, button_w, button_h)

    def _button_at_position(self, mouse_pos):
        for key, _ in self.button_order:
            if self.button_rects[key].collidepoint(mouse_pos):
                return key
        return None

    def _activate_button(self, key):
        if key == "play":
            from scenes.song_select import SongSelect

            self.switch_to_scene(SongSelect())
        elif key == "setting":
            from scenes.setting import Setting

            self.switch_to_scene(Setting())
        elif key == "exit":
            print("Goodbye!")
            self.switch_to_scene(None)

    def process_input(self, events):
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.hovered_button = self._button_at_position(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = self._button_at_position(event.pos)
                if clicked is not None:
                    self._activate_button(clicked)

    def update(self):
        pass

    def render(self, screen):
        width, height = screen.get_size()
        if (width, height) != self.layout_size:
            self._build_layout(width, height)

        self.hovered_button = self._button_at_position(pygame.mouse.get_pos())

        screen.fill(self.background_color)

        # Draw soft radial lights so the menu matches the rest of the game's neon-dark style.
        left_glow = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.circle(left_glow, (57, 120, 255, 40), (int(width * 0.2), int(height * 0.18)), 220)
        pygame.draw.circle(left_glow, (133, 85, 255, 28), (int(width * 0.8), int(height * 0.75)), 260)
        screen.blit(left_glow, (0, 0))

        pygame.draw.rect(screen, self.panel_color, self.panel_rect, border_radius=18)
        pygame.draw.rect(screen, self.panel_border_color, self.panel_rect, width=2, border_radius=18)

        accent_bar = pygame.Rect(self.panel_rect.x + 2, self.panel_rect.y + 2, self.panel_rect.width - 4, 7)
        pygame.draw.rect(screen, self.button_hover_color, accent_bar, border_radius=8)

        screen.blit(self.title_surface, self.title_rect)
        screen.blit(self.subtitle_surface, self.subtitle_rect)

        for key, label in self.button_order:
            rect = self.button_rects[key]
            color = self.button_hover_color if key == self.hovered_button else self.button_color

            pygame.draw.rect(screen, color, rect, border_radius=10)
            pygame.draw.rect(screen, self.button_border_color, rect, width=2, border_radius=10)

            text_surface = self.button_font.render(label, True, self.button_text_color)
            text_rect = text_surface.get_rect(center=rect.center)
            screen.blit(text_surface, text_rect)
