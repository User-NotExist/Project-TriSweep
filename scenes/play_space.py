from components.scene_base import SceneBase
from components.player import Player
from config import Config
import pygame

LANE_0_KEY = [pygame.K_a, pygame.K_KP_4]
LANE_1_KEY = [pygame.K_s, pygame.K_KP_5]
LANE_2_KEY = [pygame.K_d, pygame.K_KP_6]

class PlaySpace(SceneBase):
    def __init__(self):
        super().__init__()

        # Visual constants for the lane field.
        self._lane_count = 3
        self._lane_width = 150
        self._lane_gap = 6

        self._background_color = (0, 0, 0)
        self._lane_color = (26, 26, 26)
        self._lane_border_color = (62, 76, 102)
        self._judgement_line_color = (255, 255, 255)
        self._player_space_line_color = (80, 220, 120)
        self._judgement_line_width = 5
        self._lane_glow_color = (120, 255, 180)
        self._lane_glow_radius = 180
        self._lane_glow_peak_alpha = 95
        # Offset from bottom to the TOP edge of the judgement line.
        self._judgement_line_y_pos = 150
        self._player = Player()
        self._is_player_x_initialized = False
        self._lane_keys = [LANE_0_KEY, LANE_1_KEY, LANE_2_KEY]
        self._lane_pressed = [False, False, False]
        self._lane_held_keys = [set() for _ in range(self._lane_count)]

        #pygame.mouse.set_visible(False)
        #pygame.event.set_grab(True)

    def process_input(self, events):
        surface = pygame.display.get_surface()
        if surface is None:
            return

        screen_width, _ = surface.get_size()
        total_width = self._lane_count * self._lane_width + (self._lane_count - 1) * self._lane_gap
        start_x = (screen_width - total_width) // 2
        player_half_width = int(self._lane_width * Player.SPRITE_WIDTH_RATIO) / 2

        self._player.set_movement_bounds(start_x + player_half_width, start_x + total_width - player_half_width)
        if not self._is_player_x_initialized:
            self._player.set_x_position(start_x + (total_width // 2))
            self._is_player_x_initialized = True

        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self._player.apply_mouse_delta(event.rel[0], Config.PLAYER_MOVE_SPEED)
            elif event.type == pygame.KEYDOWN:
                for lane_index, lane_key_group in enumerate(self._lane_keys):
                    for lane_key in lane_key_group:
                        if event.key != lane_key:
                            continue
                        self._lane_held_keys[lane_index].add(lane_key)
                        self._lane_pressed[lane_index] = bool(self._lane_held_keys[lane_index])
                        break
            elif event.type == pygame.KEYUP:
                for lane_index, lane_key_group in enumerate(self._lane_keys):
                    for lane_key in lane_key_group:
                        if event.key != lane_key:
                            continue
                        self._lane_held_keys[lane_index].discard(lane_key)
                        self._lane_pressed[lane_index] = bool(self._lane_held_keys[lane_index])
                        break

    def update(self):
        pass

    def _draw_lane_glow(self, screen, lane_x, lane_width, judgement_y):
        glow_surface = pygame.Surface((lane_width, screen.get_height()), pygame.SRCALPHA)

        for distance in range(self._lane_glow_radius):
            glow_y = judgement_y - distance
            if glow_y < 0:
                break

            alpha = int(self._lane_glow_peak_alpha * (1 - (distance / self._lane_glow_radius)))
            if alpha <= 0:
                continue

            glow_color = (*self._lane_glow_color, alpha)
            pygame.draw.line(glow_surface, glow_color, (0, glow_y), (lane_width - 1, glow_y), 1)

        screen.blit(glow_surface, (lane_x, 0))

    def render(self, screen):
        screen.fill(self._background_color)

        screen_width, screen_height = screen.get_size()
        total_width = self._lane_count * self._lane_width + (self._lane_count - 1) * self._lane_gap
        start_x = (screen_width - total_width) // 2
        judgement_top = screen_height - self._judgement_line_y_pos
        judgement_y = judgement_top + (self._judgement_line_width // 2)

        for lane_index in range(self._lane_count):
            lane_x = start_x + lane_index * (self._lane_width + self._lane_gap)
            lane_rect = pygame.Rect(lane_x, 0, self._lane_width, screen_height)
            pygame.draw.rect(screen, self._lane_color, lane_rect)
            if self._lane_pressed[lane_index]:
                self._draw_lane_glow(screen, lane_x, self._lane_width, judgement_y)
            pygame.draw.rect(screen, self._lane_border_color, lane_rect, 2)

        pygame.draw.line(
            screen,
            self._judgement_line_color,
            (start_x, judgement_y),
            (start_x + total_width, judgement_y),
            self._judgement_line_width,
        )

        player_half_width = int(self._lane_width * Player.SPRITE_WIDTH_RATIO) / 2
        self._player.set_movement_bounds(start_x + player_half_width, start_x + total_width - player_half_width)
        if not self._is_player_x_initialized:
            self._player.set_x_position(start_x + (total_width // 2))
            self._is_player_x_initialized = True

        sprite_width_px = self._player.sprite_pixel_size[0]
        player_center_x = int(self._player.x_position)
        player_space_start_x = player_center_x - (sprite_width_px // 2)
        player_space_end_x = player_space_start_x + sprite_width_px
        pygame.draw.line(
            screen,
            self._player_space_line_color,
            (player_space_start_x, judgement_y),
            (player_space_end_x, judgement_y),
            self._judgement_line_width,
        )

        self._player.render(screen, self._lane_width, judgement_y + (self._player.sprite_pixel_size[0] // 2))


    def on_scene_exit(self):
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)