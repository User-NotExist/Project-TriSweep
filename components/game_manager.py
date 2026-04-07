from components.obstacles.obstacle_base import ObstacleBase
from components.song import Song
from components.chart import Chart
from components.player import Player
from components.notes.note_base import NoteBase
from components.play_data import PlayData
from components.obstacles.damage_obstacle import DamageObstacle
from components.obstacles.collect_obstacle import CollectObstacle
from components.local_enum.judgement_level import JudgementLevel
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
        self._touch_damage_per_second = 40.0
        self._damage_accumulator = 0.0
        self._last_tick_ms = None
        self._hit_window_ms = Config.MISS_TIMING
        self._previous_lane_pressed = [False, False, False]
        self._active_long_holds = {}
        self._active_collect_holds = {}
        self._collect_hit_window_ms = 100
        self._last_judgement_payload = None
        self._music_start_due_ms = None
        self._music_has_started = False
        self._music_fade_delay_ms = 500
        self._music_fade_duration_ms = 1500
        self._music_fade_due_ms = None
        self._music_fade_started = False

        self.__starting_ms = None

    def _publish_judgement(self, payload: dict):
        self._last_judgement_payload = {
            "source": payload.get("source", "unknown"),
            "judgement": payload.get("judgement"),
            "hit_error_ms": payload.get("hit_error_ms"),
            "timing": payload.get("timing"),
            "hold_ratio": payload.get("hold_ratio"),
            "is_long": payload.get("is_long", False),
        }

    def _record_note_judgement(self, note_payload: dict):
        note = note_payload.get("note")
        if note is None:
            return

        judgement = note_payload.get("judgement", JudgementLevel.MISS)
        hit_error_ms = int(note_payload.get("hit_error_ms", 0))
        lane_index = int(note_payload.get("lane", -1))
        self._play_data.record_note(note, hit_error_ms, judgement, lane_index)

        self._publish_judgement(
            {
                "source": "note",
                "judgement": judgement,
                "hit_error_ms": hit_error_ms,
                "timing": note_payload.get("timing"),
                "hold_ratio": note_payload.get("hold_ratio"),
                "is_long": bool(note_payload.get("is_long", False)),
            }
        )

    def _expire_missed_notes(self, now_elapsed_ms: int):
        missed_payloads = []
        active_hold_notes = {
            hold_state.get("note")
            for hold_state in self._active_long_holds.values()
            if hold_state is not None
        }

        for note in self._loaded_notes.copy():
            if note in active_hold_notes:
                continue

            hit_error_ms = note.hit_error_ms(now_elapsed_ms)
            if hit_error_ms <= int(self._hit_window_ms):
                continue

            miss_payload = note.build_miss_payload(int(note.lane), now_elapsed_ms)
            missed_payloads.append(miss_payload)
            self._record_note_judgement(miss_payload)
            self._loaded_notes.remove(note)

        return missed_payloads

    def _record_obstacle_judgement(self, obstacle_payload: dict):
        obstacle = obstacle_payload.get("obstacle")
        if obstacle is None:
            return

        judgement = obstacle_payload.get("judgement", JudgementLevel.MISS)
        self._play_data.record_obstacle(obstacle, judgement)
        self._publish_judgement(
            {
                "source": "obstacle",
                "judgement": judgement,
                "hit_error_ms": obstacle_payload.get("hit_error_ms"),
                "timing": obstacle_payload.get("timing"),
                "hold_ratio": obstacle_payload.get("hold_ratio"),
                "is_long": bool(obstacle_payload.get("is_long", False)),
            }
        )

    def _remove_obstacle_instance(self, obstacle: ObstacleBase):
        # Remove by object identity so resolved collect obstacles cannot linger in render/update loops.
        self._active_collect_holds.pop(id(obstacle), None)
        self._loaded_obstacles = [obj for obj in self._loaded_obstacles if obj is not obstacle]

    def _judge_obstacle(
        self,
        obstacle: ObstacleBase,
        elapsed_ms: int,
        is_player_in_lane: bool,
        hold_ratio: Optional[float] = None,
    ):
        if isinstance(obstacle, CollectObstacle):
            if obstacle.is_long and hold_ratio is not None:
                # Current design: started long-collect resolves as CRITPERFECT with ratio payload.
                return JudgementLevel.CRITPERFECT

            hit_error_ms = int(elapsed_ms - int(obstacle.start_time))
            if is_player_in_lane and abs(hit_error_ms) <= self._collect_hit_window_ms:
                return JudgementLevel.CRITPERFECT
            return JudgementLevel.MISS

        return JudgementLevel.MISS

    def _finalize_collect_obstacle(
        self,
        obstacle: CollectObstacle,
        judgement,
        obstacle_judgements,
        hit_error_ms: Optional[int] = None,
    ):
        payload = {
            "obstacle": obstacle,
            "judgement": judgement,
            "is_long": False,
            "hit_error_ms": hit_error_ms,
            "timing": self._timing_label(int(hit_error_ms)) if hit_error_ms is not None else None,
            "hold_ratio": None,
        }
        if judgement == JudgementLevel.CRITPERFECT:
            self.player.apply_heal(2)

        obstacle_judgements.append(payload)
        self._record_obstacle_judgement(payload)
        self._remove_obstacle_instance(obstacle)

    def _finalize_long_collect_hold(
        self,
        obstacle: CollectObstacle,
        obstacle_judgements,
        now_elapsed_ms: int,
        forced_judgement: Optional[JudgementLevel] = None,
    ):
        hold_state = self._active_collect_holds.get(id(obstacle))
        held_ms = 0
        start_error_ms = 0

        if hold_state is not None:
            start_error_ms = int(hold_state.get("start_error_ms", 0))
            held_ms = int(hold_state.get("held_ms", 0))
            if bool(hold_state.get("is_in_lane", hold_state.get("is_touching", False))):
                from_ms = max(int(hold_state.get("last_sample_ms", now_elapsed_ms)), int(obstacle.start_time))
                to_ms = min(int(now_elapsed_ms), int(obstacle.end_time))
                if to_ms > from_ms:
                    held_ms += to_ms - from_ms

        duration_ms = max(1, int(obstacle.duration_ms))
        hold_ratio = max(0.0, min(1.0, held_ms / duration_ms))

        judgement = forced_judgement
        if judgement is None:
            judgement = self._judge_obstacle(
                obstacle,
                now_elapsed_ms,
                is_player_in_lane=True,
                hold_ratio=hold_ratio,
            )

        payload = {
            "obstacle": obstacle,
            "judgement": judgement,
            "is_long": True,
            "hit_error_ms": start_error_ms,
            "timing": self._timing_label(start_error_ms),
            "hold_ratio": hold_ratio,
        }
        if judgement == JudgementLevel.CRITPERFECT:
            self.player.apply_heal(5 * hold_ratio)
        obstacle_judgements.append(payload)
        self._record_obstacle_judgement(payload)
        self._remove_obstacle_instance(obstacle)

    def _get_elapsed_ms(self, now_ms: Optional[int] = None):
        if self.__starting_ms is None:
            return None
        current_tick = pygame.time.get_ticks() if now_ms is None else int(now_ms)
        return max(0, current_tick - self.__starting_ms)

    @staticmethod
    def _get_input_offset_ms():
        return int(getattr(Config, "OFFSET_INPUT", 0))

    def _get_adjusted_input_elapsed_ms(self, now_ms: Optional[int] = None):
        elapsed_ms = self._get_elapsed_ms(now_ms)
        if elapsed_ms is None:
            return None
        return int(elapsed_ms) + self._get_input_offset_ms()

    @staticmethod
    def _timing_label(hit_error_ms: int):
        if hit_error_ms < 0:
            return "early"
        if hit_error_ms > 0:
            return "late"
        return "perfect"

    @staticmethod
    def _lane_index_from_x(
        x_position: int,
        lane_start_x: int,
        lane_width: int,
        lane_gap: int,
        lane_count: int = 3,
    ):
        lane_span = int(lane_width + lane_gap)
        if lane_span <= 0:
            return -1

        relative_x = int(x_position) - int(lane_start_x)
        if relative_x < 0:
            return -1

        lane_index = relative_x // lane_span
        if lane_index < 0 or lane_index >= int(lane_count):
            return -1

        lane_local_x = relative_x - (lane_index * lane_span)
        if lane_local_x >= int(lane_width):
            return -1

        return int(lane_index)

    def _is_note_in_active_long_hold(self, note: NoteBase):
        for hold_state in self._active_long_holds.values():
            if hold_state is None:
                continue
            if hold_state.get("note") is note:
                return True
        return False

    @staticmethod
    def _blit_vertical_slice(screen, surface, lane_x, source_top_y, visible_top_y, visible_bottom_y):
        visible_height = int(visible_bottom_y - visible_top_y)
        if visible_height <= 0:
            return

        source_y = int(visible_top_y - source_top_y)
        source_rect = pygame.Rect(0, source_y, surface.get_width(), visible_height)
        screen.blit(surface, (lane_x, int(visible_top_y)), source_rect)

    @property
    def current_score(self):
        return int(self._play_data.current_score)

    @property
    def decreasing_display_score(self):
        return int(self._play_data.decreasing_display_score)

    @property
    def current_combo(self):
        return int(self._play_data.current_combo)

    @property
    def play_data(self):
        return self._play_data

    @property
    def playing_song(self):
        return self._playing_song

    @property
    def playing_chart(self):
        return self._playing_chart

    @property
    def is_round_finished(self):
        if not self._is_playing or self.__starting_ms is None:
            return False

        has_pending_notes = bool(self._loaded_notes) or bool(self._active_long_holds)
        has_pending_obstacles = bool(self._loaded_obstacles) or bool(self._active_collect_holds)
        return not (has_pending_notes or has_pending_obstacles)

    @property
    def last_judgement_payload(self):
        if self._last_judgement_payload is None:
            return None
        return dict(self._last_judgement_payload)

    def force_complete_round_as_miss(self, now_ms: Optional[int] = None):
        if self.__starting_ms is None:
            return

        now_elapsed_ms = self._get_adjusted_input_elapsed_ms(now_ms)
        if now_elapsed_ms is None:
            now_elapsed_ms = 0

        # Resolve active long-note holds as MISS first so they do not duplicate with remaining notes.
        for lane_index in list(self._active_long_holds.keys()):
            hold_state = self._active_long_holds.get(lane_index)
            if hold_state is None:
                continue

            note = hold_state.get("note")
            if note is None:
                self._active_long_holds.pop(lane_index, None)
                continue

            miss_payload = note.build_payload(
                lane_index=int(lane_index),
                hit_error_ms=note.hit_error_ms(now_elapsed_ms),
                judgement=JudgementLevel.MISS,
                hold_ratio=0.0,
            )
            self._active_long_holds.pop(lane_index, None)
            if note in self._loaded_notes:
                self._loaded_notes.remove(note)
            self._record_note_judgement(miss_payload)

        for note in self._loaded_notes.copy():
            miss_payload = note.build_miss_payload(int(note.lane), now_elapsed_ms)
            self._loaded_notes.remove(note)
            self._record_note_judgement(miss_payload)

        # Resolve active long collect holds as MISS through existing finalize path.
        for obstacle in self._loaded_obstacles.copy():
            if not isinstance(obstacle, CollectObstacle) or not obstacle.is_long:
                continue
            if id(obstacle) not in self._active_collect_holds:
                continue
            self._finalize_long_collect_hold(
                obstacle,
                [],
                now_elapsed_ms,
                forced_judgement=JudgementLevel.MISS,
            )

        for obstacle in self._loaded_obstacles.copy():
            if isinstance(obstacle, CollectObstacle):
                if obstacle.is_long:
                    self._finalize_long_collect_hold(
                        obstacle,
                        [],
                        now_elapsed_ms,
                        forced_judgement=JudgementLevel.MISS,
                    )
                else:
                    self._finalize_collect_obstacle(
                        obstacle,
                        JudgementLevel.MISS,
                        [],
                        hit_error_ms=int(now_elapsed_ms - int(obstacle.start_time)),
                    )
                continue

            payload = {
                "obstacle": obstacle,
                "judgement": JudgementLevel.MISS,
                "is_long": bool(getattr(obstacle, "is_long", False)),
                "hit_error_ms": int(now_elapsed_ms - int(getattr(obstacle, "start_time", 0))),
                "timing": self._timing_label(int(now_elapsed_ms - int(getattr(obstacle, "start_time", 0)))),
                "hold_ratio": 0.0 if bool(getattr(obstacle, "is_long", False)) else None,
            }
            self._record_obstacle_judgement(payload)
            self._remove_obstacle_instance(obstacle)

    def process_input(self, lane_pressed, lane_held_keys, lane_trigger_counts=None, now_ms: Optional[int] = None):
        """
        Evaluate lane input against the closest note on each lane.

        Returns a list of judgement payloads:
        - tap note: includes signed `hit_error_ms` and `timing` (early/late/perfect)
        - long note: start timing plus `hold_ratio` once released or when end is reached
        """
        if not self._is_playing or self.__starting_ms is None:
            return []

        now_elapsed_ms = self._get_adjusted_input_elapsed_ms(now_ms)
        if now_elapsed_ms is None:
            return []

        results = self._expire_missed_notes(now_elapsed_ms)

        lane_count = min(len(lane_pressed), len(self._previous_lane_pressed))
        if lane_trigger_counts is None:
            lane_trigger_counts = [0 for _ in range(lane_count)]
            for lane_index in range(lane_count):
                lane_is_pressed = bool(lane_pressed[lane_index])
                was_pressed = bool(self._previous_lane_pressed[lane_index])
                lane_trigger_counts[lane_index] = 1 if (lane_is_pressed and not was_pressed) else 0

        for lane_index in range(lane_count):
            lane_is_pressed = bool(lane_pressed[lane_index])
            lane_notes = [note for note in self._loaded_notes if int(note.lane) == lane_index]
            lane_input_result = NoteBase.process_lane_input(
                lane_index=lane_index,
                lane_notes=lane_notes,
                lane_is_pressed=lane_is_pressed,
                trigger_count=max(0, int(lane_trigger_counts[lane_index])),
                now_elapsed_ms=now_elapsed_ms,
                hit_window_ms=int(self._hit_window_ms),
                active_hold=self._active_long_holds.get(lane_index),
            )

            new_hold_state = lane_input_result.get("active_hold")
            if new_hold_state is None:
                self._active_long_holds.pop(lane_index, None)
            else:
                self._active_long_holds[lane_index] = new_hold_state

            for consumed_note in lane_input_result.get("consumed_notes", []):
                if consumed_note in self._loaded_notes:
                    self._loaded_notes.remove(consumed_note)

            for note_payload in lane_input_result.get("results", []):
                results.append(note_payload)

                # Start-long events are preview payloads for HUD timing feedback, not final scoring.
                should_record = not (
                    bool(note_payload.get("is_long")) and note_payload.get("hold_ratio") is None
                )
                if should_record:
                    self._record_note_judgement(note_payload)

            self._previous_lane_pressed[lane_index] = lane_is_pressed

        return results

    @property
    def player(self) -> Player:
        return self._player

    def _start_song_music(self):
        if self._music_has_started:
            return

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
            self._music_has_started = True
        except Exception as error:
            print(f"[GameManager] Failed to start music '{music_path}': {error}")

    def _update_music_start(self, now_ms: int):
        if self._music_has_started:
            return
        if self._music_start_due_ms is None:
            return
        if int(now_ms) < int(self._music_start_due_ms):
            return
        self._start_song_music()

    def _update_round_end_music(self, now_ms: int):
        if self._music_fade_started:
            return

        if not self.is_round_finished:
            return

        # If music was never started (large OFFSET_MUSIC + short chart), prevent late auto-start.
        if not self._music_has_started:
            self._music_start_due_ms = None
            self._music_fade_started = True
            return

        if self._music_fade_due_ms is None:
            self._music_fade_due_ms = int(now_ms) + int(self._music_fade_delay_ms)
            return

        if int(now_ms) < int(self._music_fade_due_ms):
            return

        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(int(self._music_fade_duration_ms))
        except Exception:
            pass

        self._music_fade_started = True
        self._music_start_due_ms = None

    def stop_song_music(self):
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
        except Exception:
            pass

    def start_game(self):
        if self.__starting_ms is not None:
            return

        self.__starting_ms = pygame.time.get_ticks()
        self._is_playing = True
        self._last_tick_ms = self.__starting_ms
        self._music_fade_due_ms = None
        self._music_fade_started = False
        music_delay_ms = max(0, int(getattr(Config, "OFFSET_MUSIC", 0)))
        if music_delay_ms == 0:
            self._music_start_due_ms = self.__starting_ms
            self._start_song_music()
        else:
            self._music_start_due_ms = self.__starting_ms + music_delay_ms

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
        self._update_music_start(now_ms)
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
        self._play_data.record_player_x(
            player_x=player.x_position,
            timestamp_ms=elapsed_ms,
            center_x=(screen.get_width() / 2.0),
        )
        player_width = max(player.sprite_pixel_size[0], int(lane_width * player.SPRITE_WIDTH_RATIO))
        player_left_x = int(player.x_position) - (player_width // 2)
        player_right_x = player_left_x + player_width
        player_lane_index = self._lane_index_from_x(
            int(player.x_position),
            lane_start_x,
            lane_width,
            lane_gap,
        )
        obstacle_judgements = []

        for note in self._loaded_notes.copy():
            note_surface = note.draw_note(lane_width, note_speed)
            note_height = note_surface.get_height()

            note_bottom_y = int(judgement_y - ((note.start_time - elapsed_ms) * note_speed_px_per_ms))
            note_top_y = note_bottom_y - note_height

            # Drop notes that have fully passed below the screen.
            if note_top_y > screen_height:
                if self._is_note_in_active_long_hold(note):
                    continue

                late_ms = int(elapsed_ms - int(note.start_time))
                if late_ms > self._hit_window_ms:
                    miss_payload = note.build_miss_payload(int(note.lane), elapsed_ms)
                    self._record_note_judgement(miss_payload)
                    self._loaded_notes.remove(note)
                continue

            if note_bottom_y < 0 or note_top_y > screen_height:
                continue

            lane_x = lane_start_x + (int(note.lane) * (lane_width + lane_gap))
            hold_state = self._active_long_holds.get(int(note.lane))
            is_active_held_long = (
                note.is_long
                and hold_state is not None
                and hold_state.get("note") is note
                and bool(hold_state.get("is_holding"))
            )

            visible_top_y = max(0, note_top_y)
            visible_bottom_y = min(screen_height, note_bottom_y)
            if is_active_held_long:
                # While holding a long note, hide any portion below the judgement line.
                visible_bottom_y = min(visible_bottom_y, judgement_y)

            self._blit_vertical_slice(
                screen,
                note_surface,
                lane_x,
                note_top_y,
                visible_top_y,
                visible_bottom_y,
            )

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

            lane_x = lane_start_x + (int(obstacle.lane) * (lane_width + lane_gap))
            intersects_judgement_line = obstacle_top_y <= judgement_y <= obstacle_bottom_y
            obstacle_left_x = lane_x
            obstacle_right_x = lane_x + obstacle_surface.get_width()
            intersects_player_span = (
                player_left_x < obstacle_right_x and player_right_x > obstacle_left_x
            )
            is_touching_player = intersects_judgement_line and intersects_player_span
            is_player_in_obstacle_lane = player_lane_index == int(obstacle.lane)
            collect_hold_state = self._active_collect_holds.get(id(obstacle))
            collect_hit_error_ms = int(elapsed_ms - int(obstacle.start_time))
            within_collect_window = abs(collect_hit_error_ms) <= self._collect_hit_window_ms

            if isinstance(obstacle, CollectObstacle) and obstacle.is_long:
                if collect_hold_state is not None:
                    is_in_lane_state = bool(
                        collect_hold_state.get("is_in_lane", collect_hold_state.get("is_touching", False))
                    )
                    if is_in_lane_state and is_player_in_obstacle_lane:
                        from_ms = max(collect_hold_state["last_sample_ms"], int(obstacle.start_time))
                        to_ms = min(elapsed_ms, int(obstacle.end_time))
                        if to_ms > from_ms:
                            collect_hold_state["held_ms"] += to_ms - from_ms
                        collect_hold_state["last_sample_ms"] = elapsed_ms

                    if not is_player_in_obstacle_lane and is_in_lane_state:
                        collect_hold_state["is_in_lane"] = False

                    if not bool(collect_hold_state.get("is_in_lane", is_in_lane_state)):
                        self._finalize_long_collect_hold(
                            obstacle,
                            obstacle_judgements,
                            elapsed_ms,
                            forced_judgement=JudgementLevel.CRITPERFECT,
                        )
                        continue

                    if elapsed_ms >= int(obstacle.end_time):
                        self._finalize_long_collect_hold(obstacle, obstacle_judgements, elapsed_ms)
                        continue

                elif is_player_in_obstacle_lane and within_collect_window:
                    self._active_collect_holds[id(obstacle)] = {
                        "is_in_lane": True,
                        "last_sample_ms": elapsed_ms,
                        "held_ms": 0,
                        "start_error_ms": collect_hit_error_ms,
                    }

                elif collect_hit_error_ms > self._collect_hit_window_ms:
                    self._finalize_long_collect_hold(
                        obstacle,
                        obstacle_judgements,
                        elapsed_ms,
                        forced_judgement=JudgementLevel.MISS,
                    )
                    continue

            if obstacle_top_y > screen_height:
                # Resolve collect obstacles as MISS instead of silently dropping them.
                if isinstance(obstacle, CollectObstacle):
                    if obstacle.is_long:
                        self._finalize_long_collect_hold(
                            obstacle,
                            obstacle_judgements,
                            elapsed_ms,
                            forced_judgement=JudgementLevel.MISS,
                        )
                    else:
                        self._finalize_collect_obstacle(
                            obstacle,
                            JudgementLevel.MISS,
                            obstacle_judgements,
                            hit_error_ms=int(elapsed_ms - int(obstacle.start_time)),
                        )
                else:
                    self._active_collect_holds.pop(id(obstacle), None)
                    self._loaded_obstacles.remove(obstacle)
                continue

            if obstacle_bottom_y < 0 or obstacle_top_y > screen_height:
                continue

            if isinstance(obstacle, CollectObstacle) and obstacle.is_long:
                visible_top_y = max(0, obstacle_top_y)
                visible_bottom_y = min(screen_height, obstacle_bottom_y)
                active_hold = self._active_collect_holds.get(id(obstacle))
                if active_hold is not None and bool(
                    active_hold.get("is_in_lane", active_hold.get("is_touching", False))
                ):
                    # Mirror long-note behavior: hide portion below judgement while actively in-lane.
                    visible_bottom_y = min(visible_bottom_y, judgement_y)

                self._blit_vertical_slice(
                    screen,
                    obstacle_surface,
                    lane_x,
                    obstacle_top_y,
                    visible_top_y,
                    visible_bottom_y,
                )
            else:
                screen.blit(obstacle_surface, (lane_x, obstacle_top_y))

            if isinstance(obstacle, CollectObstacle) and not obstacle.is_long:
                if is_player_in_obstacle_lane and within_collect_window:
                    self._finalize_collect_obstacle(
                        obstacle,
                        JudgementLevel.CRITPERFECT,
                        obstacle_judgements,
                        hit_error_ms=collect_hit_error_ms,
                    )
                elif collect_hit_error_ms > self._collect_hit_window_ms:
                    self._finalize_collect_obstacle(
                        obstacle,
                        JudgementLevel.MISS,
                        obstacle_judgements,
                        hit_error_ms=collect_hit_error_ms,
                    )
                continue

            if not isinstance(obstacle, DamageObstacle):
                continue

            if not intersects_judgement_line:
                continue

            if intersects_player_span:
                self._damage_accumulator += (delta_ms / 1000.0) * self._touch_damage_per_second

        if self._damage_accumulator >= 1.0:
            damage_to_apply = int(self._damage_accumulator)
            self._damage_accumulator -= damage_to_apply
            player.apply_damage(damage_to_apply)

        self._update_round_end_music(now_ms)

        return obstacle_judgements

