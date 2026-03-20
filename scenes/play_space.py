from components.scene_base import SceneBase
from components.player import Player
import pygame


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
        self._judgement_line_color = (244, 229, 140)
        self._player_space_line_color = (80, 220, 120)
        self._judgement_line_width = 5
        # Offset from bottom to the TOP edge of the judgement line.
        self._judgement_line_y_pos = 150
        self._player_lane_index = 1
        self._player = Player()

        #pygame.mouse.set_visible(False)
        #pygame.event.set_grab(True)

    def process_input(self, events):
        pass

    def update(self):
        pass

    def render(self, screen):
        screen.fill(self._background_color)

        screen_width, screen_height = screen.get_size()
        total_width = self._lane_count * self._lane_width + (self._lane_count - 1) * self._lane_gap
        start_x = (screen_width - total_width) // 2

        for lane_index in range(self._lane_count):
            lane_x = start_x + lane_index * (self._lane_width + self._lane_gap)
            lane_rect = pygame.Rect(lane_x, 0, self._lane_width, screen_height)
            pygame.draw.rect(screen, self._lane_color, lane_rect)
            pygame.draw.rect(screen, self._lane_border_color, lane_rect, 2)

        judgement_top = screen_height - self._judgement_line_y_pos
        judgement_y = judgement_top + (self._judgement_line_width // 2)
        pygame.draw.line(
            screen,
            self._judgement_line_color,
            (start_x, judgement_y),
            (start_x + total_width, judgement_y),
            self._judgement_line_width,
        )

        player_lane_x = start_x + self._player_lane_index * (self._lane_width + self._lane_gap)
        player_lane_center_x = player_lane_x + (self._lane_width // 2)
        player_space_width = int(self._lane_width * Player.SPRITE_WIDTH_RATIO)
        player_space_start_x = player_lane_center_x - (player_space_width // 2)
        player_space_end_x = player_space_start_x + player_space_width
        pygame.draw.line(
            screen,
            self._player_space_line_color,
            (player_space_start_x, judgement_y),
            (player_space_end_x, judgement_y),
            self._judgement_line_width,
        )

        self._player.render(screen, player_lane_center_x, self._lane_width, judgement_y)

    def on_scene_exit(self):
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)