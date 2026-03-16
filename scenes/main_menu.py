import pygame

from scenes.scene_base import SceneBase

class MainMenu(SceneBase):
    def __init__(self):
        super().__init__()
        self.title_text = "Project TriSweep"
        self.background_color = (245, 248, 252)
        self.title_color = (30, 41, 59)
        self.button_color = (99, 102, 241)
        self.button_hover_color = (79, 70, 229)
        self.button_text_color = (255, 255, 255)

        self.title_font = pygame.font.SysFont("arial", 56, bold=True)
        self.button_font = pygame.font.SysFont("arial", 32, bold=True)

        self.button_size = (240, 58)
        self.button_gap = 16
        self.button_order = [("play", "Play"), ("setting", "Setting")]

        self.title_surface = None
        self.title_rect = pygame.Rect(0, 0, 0, 0)
        self.button_rects = {
            "play": pygame.Rect(0, 0, 0, 0),
            "setting": pygame.Rect(0, 0, 0, 0),
        }
        self.hovered_button = None
        self.layout_size = (0, 0)

    def _build_layout(self, width, height):
        self.layout_size = (width, height)

        self.title_surface = self.title_font.render(self.title_text, True, self.title_color)
        self.title_rect = self.title_surface.get_rect(centerx=width // 2, y=int(height * 0.18))

        button_w, button_h = self.button_size
        start_y = self.title_rect.bottom + 40

        for index, (key, _) in enumerate(self.button_order):
            y = start_y + index * (button_h + self.button_gap)
            self.button_rects[key] = pygame.Rect((width - button_w) // 2, y, button_w, button_h)

    def _button_at_position(self, mouse_pos):
        for key, _ in self.button_order:
            if self.button_rects[key].collidepoint(mouse_pos):
                return key
        return None

    def _activate_button(self, key):
        if key == "play":
            # Placeholder action until a gameplay scene is wired in.
            print("Play button clicked")
        elif key == "setting":
            # Placeholder action until a settings scene is wired in.
            print("Setting button clicked")

    def ProcessInput(self, events):
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.hovered_button = self._button_at_position(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = self._button_at_position(event.pos)
                if clicked is not None:
                    self._activate_button(clicked)

    def Update(self):
        pass

    def Render(self, screen):
        width, height = screen.get_size()
        if (width, height) != self.layout_size:
            self._build_layout(width, height)

        self.hovered_button = self._button_at_position(pygame.mouse.get_pos())

        screen.fill(self.background_color)
        screen.blit(self.title_surface, self.title_rect)

        for key, label in self.button_order:
            rect = self.button_rects[key]
            color = self.button_hover_color if key == self.hovered_button else self.button_color

            pygame.draw.rect(screen, color, rect, border_radius=10)

            text_surface = self.button_font.render(label, True, self.button_text_color)
            text_rect = text_surface.get_rect(center=rect.center)
            screen.blit(text_surface, text_rect)
