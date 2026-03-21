from components.scene_base import SceneBase
from components.game_manager import GameManager
from config import Config
import pygame

class PlaySpace(SceneBase):
    def __init__(self, game_manager: GameManager):
        super().__init__()
        self._game_manager = game_manager

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
        self._health_bar_width = 16
        self._health_bar_gap = 14
        self._health_bar_border_color = (215, 223, 235)
        self._health_bar_bg_color = (42, 48, 58)
        self._health_bar_green = (68, 224, 112)
        self._health_bar_yellow = (245, 210, 72)
        self._health_bar_red = (236, 78, 78)
        # Offset from bottom to the TOP edge of the judgement line.
        self._judgement_line_y_pos = 150
        self._is_player_x_initialized = False
        self._lane_keys = self._build_lane_key_groups()
        self._lane_key_to_lane_index = self._build_lane_key_map(self._lane_keys)
        self._lane_pressed = [False, False, False]
        self._lane_held_keys = [set() for _ in range(self._lane_count)]

        #pygame.mouse.set_visible(False)
        #pygame.event.set_grab(True)

    @staticmethod
    def _resolve_keycode(key_name, fallback_keycode):
        try:
            normalized = str(key_name).strip().lower()
            return pygame.key.key_code(normalized)
        except Exception:
            return fallback_keycode

    def _build_lane_key_groups(self):
        key_name_groups = [
            (Config.LANE_0_KEY_0, Config.LANE_0_KEY_1),
            (Config.LANE_1_KEY_0, Config.LANE_1_KEY_1),
            (Config.LANE_2_KEY_0, Config.LANE_2_KEY_1),
        ]
        fallback_groups = [
            (pygame.K_q, pygame.K_i),
            (pygame.K_w, pygame.K_o),
            (pygame.K_e, pygame.K_p),
        ]

        lane_key_groups = []
        for lane_index in range(self._lane_count):
            resolved_group = []
            for key_index in range(2):
                resolved_group.append(
                    self._resolve_keycode(
                        key_name_groups[lane_index][key_index],
                        fallback_groups[lane_index][key_index],
                    )
                )
            lane_key_groups.append(resolved_group)
        return lane_key_groups

    @staticmethod
    def _build_lane_key_map(lane_key_groups):
        key_to_lane = {}
        for lane_index, key_group in enumerate(lane_key_groups):
            for keycode in key_group:
                if keycode not in key_to_lane:
                    key_to_lane[keycode] = lane_index
        return key_to_lane

    def process_input(self, events):
        surface = pygame.display.get_surface()
        if surface is None:
            return

        screen_width, _ = surface.get_size()
        total_width = self._lane_count * self._lane_width + (self._lane_count - 1) * self._lane_gap
        start_x = (screen_width - total_width) // 2
        player = self._game_manager.player
        player_half_width = int(self._lane_width * player.SPRITE_WIDTH_RATIO) / 2

        player.set_movement_bounds(start_x + player_half_width, start_x + total_width - player_half_width)
        if not self._is_player_x_initialized:
            player.set_x_position(start_x + (total_width // 2))
            self._is_player_x_initialized = True

        for event in events:
            if event.type == pygame.MOUSEMOTION:
                player.apply_mouse_delta(event.rel[0], Config.PLAYER_MOVE_SPEED)
            elif event.type == pygame.KEYDOWN:
                lane_index = self._lane_key_to_lane_index.get(event.key)
                if lane_index is not None:
                    self._lane_held_keys[lane_index].add(event.key)
                    self._lane_pressed[lane_index] = bool(self._lane_held_keys[lane_index])
            elif event.type == pygame.KEYUP:
                lane_index = self._lane_key_to_lane_index.get(event.key)
                if lane_index is not None:
                    self._lane_held_keys[lane_index].discard(event.key)
                    self._lane_pressed[lane_index] = bool(self._lane_held_keys[lane_index])

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

    def _draw_health_bar(self, screen, start_x, player_health):
        bar_height = max(1, screen.get_height())
        bar_x = start_x - self._health_bar_gap - self._health_bar_width
        bar_rect = pygame.Rect(bar_x, 0, self._health_bar_width, bar_height)

        health_value = max(0, min(100, int(player_health)))
        fill_height = int((health_value / 100) * bar_height)
        fill_rect = pygame.Rect(bar_rect.x, bar_rect.bottom - fill_height, bar_rect.width, fill_height)

        if health_value > 60:
            fill_color = self._health_bar_green
        elif health_value > 30:
            fill_color = self._health_bar_yellow
        else:
            fill_color = self._health_bar_red

        pygame.draw.rect(screen, self._health_bar_bg_color, bar_rect)
        if fill_height > 0:
            pygame.draw.rect(screen, fill_color, fill_rect)
        pygame.draw.rect(screen, self._health_bar_border_color, bar_rect, 2)

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

        player = self._game_manager.player
        self._draw_health_bar(screen, start_x, player.health)
        player_half_width = int(self._lane_width * player.SPRITE_WIDTH_RATIO) / 2
        player.set_movement_bounds(start_x + player_half_width, start_x + total_width - player_half_width)
        if not self._is_player_x_initialized:
            player.set_x_position(start_x + (total_width // 2))
            self._is_player_x_initialized = True

        sprite_width_px = player.sprite_pixel_size[0]
        player_center_x = int(player.x_position)
        player_space_start_x = player_center_x - (sprite_width_px // 2)
        player_space_end_x = player_space_start_x + sprite_width_px
        pygame.draw.line(
            screen,
            self._player_space_line_color,
            (player_space_start_x, judgement_y),
            (player_space_end_x, judgement_y),
            self._judgement_line_width,
        )

        player.render(screen, self._lane_width, judgement_y + (player.sprite_pixel_size[0] // 2))


    def on_scene_exit(self):
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)