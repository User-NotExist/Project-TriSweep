from components.obstacles.obstacle_base import ObstacleBase
from components.song import Song
from components.chart import Chart
from components.player import Player
from components.notes.note_base import NoteBase
from components.play_data import PlayData
from components.obstacles.damage_obstacle import DamageObstacle
from typing import Optional
from pathlib import Path
import pygame

from config import Config


class GameManager:
    def __init__(self, song: Song, chart: Chart, notes : list[NoteBase], obstacles : list[ObstacleBase]):
        self._playing_song = song
        self._playing_chart = chart
        self._loaded_notes = notes.copy()
        self._loaded_obstacles = obstacles.copy()
        self._player = Player()
        self._is_playing = False
        self._play_data = PlayData(Config.PLAYER_NAME, self._playing_song, self._playing_chart)
        self._touch_damage_per_second = 20.0
        self._damage_accumulator = 0.0
        self._last_tick_ms = None

        self.__starting_ms = None

    @property
    def player(self) -> Player:
        return self._player

    def _start_song_music(self):
        music_path = getattr(self._playing_song, "music_path", None)
        if music_path is None:
            return

        try:
            resolved_path = Path(music_path)
            if not resolved_path.is_file():
                return

            pygame.mixer.music.load(str(resolved_path))
            pygame.mixer.music.set_volume(float(Config.MUSIC_VOLUME))
            pygame.mixer.music.play()
        except Exception as error:
            print(f"[GameManager] Failed to start music '{music_path}': {error}")

    def start_game(self):
        if self.__starting_ms is not None:
            return

        self.__starting_ms = pygame.time.get_ticks()
        self._is_playing = True
        self._last_tick_ms = self.__starting_ms
        self._start_song_music()

    def update_game(
        self,
        screen,
        lane_start_x: int,
        lane_width: int,
        lane_gap: int,
        judgement_y: int,
    ):
        if not self._is_playing or self.__starting_ms is None:
            self.start_game()

        now_ms = pygame.time.get_ticks()
        elapsed_ms = now_ms - self.__starting_ms
        if self._last_tick_ms is None:
            delta_ms = 0
        else:
            delta_ms = max(0, now_ms - self._last_tick_ms)
        self._last_tick_ms = now_ms

        # Config value is a gameplay scalar; convert to practical px/s for visible scrolling.
        note_speed = max(1.0, float(Config.PLAYER_LANE_SPEED)) * 100.0
        # Keep timing units consistent with NoteBase.draw_note (pixels/second -> pixels/ms).
        note_speed_px_per_ms = note_speed / 1000.0
        screen_height = screen.get_height()
        player = self._player
        player_width = max(player.sprite_pixel_size[0], int(lane_width * player.SPRITE_WIDTH_RATIO))
        player_left_x = int(player.x_position) - (player_width // 2)
        player_right_x = player_left_x + player_width

        for note in self._loaded_notes.copy():
            note_surface = note.draw_note(lane_width, note_speed)
            note_height = note_surface.get_height()

            note_bottom_y = int(judgement_y - ((note.start_time - elapsed_ms) * note_speed_px_per_ms))
            note_top_y = note_bottom_y - note_height

            # Drop notes that have fully passed below the screen.
            if note_top_y > screen_height:
                self._loaded_notes.remove(note)
                continue

            if note_bottom_y < 0 or note_top_y > screen_height:
                continue

            lane_x = lane_start_x + (int(note.lane) * (lane_width + lane_gap))
            screen.blit(note_surface, (lane_x, note_top_y))

        simultaneous_lane_map = {}
        for note in self._loaded_notes:
            simultaneous_lane_map.setdefault(note.start_time, set()).add(int(note.lane))

        full_lane_width = (3 * lane_width) + (2 * lane_gap)
        for start_time, lanes in simultaneous_lane_map.items():
            if len(lanes) < 2:
                continue

            line_y = int(judgement_y - ((start_time - elapsed_ms) * note_speed_px_per_ms))
            if 0 <= line_y <= screen_height:
                pygame.draw.line(
                    screen,
                    (138, 137, 136),
                    (lane_start_x, line_y),
                    (lane_start_x + full_lane_width, line_y),
                    3,
                )

        for obstacle in self._loaded_obstacles.copy():
            obstacle_surface = obstacle.draw_obstacle(lane_width, note_speed)
            obstacle_height = obstacle_surface.get_height()

            obstacle_bottom_y = int(
                judgement_y - ((obstacle.start_time - elapsed_ms) * note_speed_px_per_ms)
            )
            obstacle_top_y = obstacle_bottom_y - obstacle_height

            if obstacle_top_y > screen_height:
                self._loaded_obstacles.remove(obstacle)
                continue

            if obstacle_bottom_y < 0 or obstacle_top_y > screen_height:
                continue

            lane_x = lane_start_x + (int(obstacle.lane) * (lane_width + lane_gap))
            screen.blit(obstacle_surface, (lane_x, obstacle_top_y))

            if not isinstance(obstacle, DamageObstacle):
                continue

            intersects_judgement_line = obstacle_top_y <= judgement_y <= obstacle_bottom_y
            if not intersects_judgement_line:
                continue

            obstacle_left_x = lane_x
            obstacle_right_x = lane_x + obstacle_surface.get_width()
            intersects_player_span = (
                player_left_x < obstacle_right_x and player_right_x > obstacle_left_x
            )
            if intersects_player_span:
                self._damage_accumulator += (delta_ms / 1000.0) * self._touch_damage_per_second

        if self._damage_accumulator >= 1.0:
            damage_to_apply = int(self._damage_accumulator)
            self._damage_accumulator -= damage_to_apply
            player.apply_damage(damage_to_apply)

