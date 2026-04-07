from components.local_enum.judgement_level import JudgementLevel
from config import Config
import pygame
from typing import Optional


class NoteBase:
    """
    Lightweight note model consumed by PlaySpace drawing code.

    IMPORTANT: chart files use the CSV column name `type`, but program code uses
    `note_type` to avoid confusion with Python's built-in `type`.
    """

    VALID_LANES = {0, 1, 2}
    VALID_NOTE_TYPES = {1, 2, 3, 4, 5, 6}

    # Fixed default color per note type.
    NOTE_TYPE_DEFAULT_COLORS = {
        1: (109, 199, 255),
        2: (255, 165, 0),
        5: (109, 199, 255),
        6: (255, 165, 0),
    }
    NORMAL_LANE_COLORS = {
        0: (255, 125, 227),
        1: (232, 232, 232),
        2: (255, 125, 227),
    }
    FALLBACK_COLOR = (220, 220, 220)
    NOTE_BORDER_COLOR = (24, 28, 36)
    NOTE_BORDER_WIDTH = 2
    TAP_NOTE_HEIGHT = 24

    def __init__(self, start_stamp, end_stamp, lane, note_type, color_override):
        self.validation_errors = []

        self.start_time = self._coerce_int(start_stamp, "start_stamp")
        self.end_time = self._coerce_int(end_stamp, "end_stamp")
        self.lane = self._coerce_int(lane, "lane")
        self.note_type = self._coerce_int(note_type, "note_type")

        self._validate_lane()
        self._validate_note_type()
        self._validate_time_range()

        self.color_override = self._coerce_color_override(color_override)

        self.base_score = 0
        self.bonus_score = 0

    @property
    def is_valid(self):
        return not self.validation_errors

    @property
    def validation_error(self):
        return "; ".join(self.validation_errors)

    @property
    def is_long(self):
        # Per chart contract, long note is any note where end_time is not -1.
        return self.end_time != -1

    @property
    def duration_ms(self):
        if not self.is_long:
            return 0
        return max(0, self.end_time - self.start_time)

    def default_color(self):
        if self.note_type in {1, 5}:
            return self.NORMAL_LANE_COLORS.get(self.lane, self.FALLBACK_COLOR)
        return self.NOTE_TYPE_DEFAULT_COLORS.get(self.note_type, self.FALLBACK_COLOR)

    def resolved_color(self):
        if self.color_override is not None:
            return self.color_override
        return self.default_color()

    def _coerce_int(self, value, field_name):
        try:
            return int(value)
        except Exception:
            self.validation_errors.append(f"Invalid {field_name}: {value}")
            return 0

    def _validate_lane(self):
        if self.lane not in self.VALID_LANES:
            self.validation_errors.append(f"Invalid lane: {self.lane}")

    def _validate_note_type(self):
        if self.note_type not in self.VALID_NOTE_TYPES:
            self.validation_errors.append(f"Invalid note_type: {self.note_type}")

    def _validate_time_range(self):
        if self.end_time != -1 and self.end_time < self.start_time:
            self.validation_errors.append(
                f"Invalid note timing: end_stamp({self.end_time}) < start_stamp({self.start_time})"
            )

    @staticmethod
    def _is_rgb_triplet(values):
        if not isinstance(values, (tuple, list)) or len(values) != 3:
            return False
        return all(isinstance(channel, int) and 0 <= channel <= 255 for channel in values)

    def _coerce_color_override(self, color_override):
        # Chart value -1 means "use type default color".
        if color_override in (-1, "-1", None, ""):
            return None

        if self._is_rgb_triplet(color_override):
            return tuple(color_override)

        if isinstance(color_override, str):
            text = color_override.strip()
            if text.startswith("#") and len(text) == 7:
                try:
                    return (
                        int(text[1:3], 16),
                        int(text[3:5], 16),
                        int(text[5:7], 16),
                    )
                except ValueError:
                    pass

            if "," in text:
                parts = [part.strip() for part in text.split(",")]
                if len(parts) == 3:
                    try:
                        rgb = tuple(int(part) for part in parts)
                        if self._is_rgb_triplet(rgb):
                            return rgb
                    except ValueError:
                        pass

        self.validation_errors.append(f"Invalid color_override: {color_override}; using default color")
        return None

    @staticmethod
    def timing_label(hit_error_ms: int):
        if hit_error_ms < 0:
            return "early"
        if hit_error_ms > 0:
            return "late"
        return "perfect"

    @staticmethod
    def find_closest_note(candidates, target_ms):
        if not candidates:
            return None
        return min(candidates, key=lambda note: abs(int(note.start_time) - int(target_ms)))

    def hit_error_ms(self, now_elapsed_ms: int):
        return int(now_elapsed_ms - int(self.start_time))

    def is_within_hit_window(self, now_elapsed_ms: int, hit_window_ms: int):
        return abs(self.hit_error_ms(now_elapsed_ms)) <= int(hit_window_ms)

    def judge_input(self, hit_error_ms: int, hold_ratio: Optional[float] = None):
        if self.is_long and hold_ratio is not None:
            return JudgementLevel.CRITPERFECT if hold_ratio >= 0.8 else JudgementLevel.GOOD

        abs_error_ms = abs(int(hit_error_ms))
        if int(getattr(self, "note_type", -1)) in {5, 6}:
            if abs_error_ms <= int(Config.GOOD_TIMING):
                return JudgementLevel.CRITPERFECT
            return JudgementLevel.MISS

        if abs_error_ms <= int(Config.CRITICAL_PERFECT_TIMING):
            return JudgementLevel.CRITPERFECT
        if abs_error_ms <= int(Config.PERFECT_TIMING):
            return JudgementLevel.PERFECT
        if abs_error_ms <= int(Config.GREAT_TIMING):
            return JudgementLevel.GREAT
        if abs_error_ms <= int(Config.GOOD_TIMING):
            return JudgementLevel.GOOD
        return JudgementLevel.MISS

    def build_payload(
        self,
        lane_index: int,
        hit_error_ms: int,
        judgement=None,
        hold_ratio: Optional[float] = None,
    ):
        resolved_judgement = judgement
        if resolved_judgement is None:
            resolved_judgement = self.judge_input(hit_error_ms, hold_ratio=hold_ratio)

        return {
            "lane": int(lane_index),
            "note": self,
            "is_long": bool(self.is_long),
            "hit_error_ms": int(hit_error_ms),
            "timing": self.timing_label(int(hit_error_ms)),
            "judgement": resolved_judgement,
            "hold_ratio": hold_ratio,
        }

    def build_miss_payload(self, lane_index: int, now_elapsed_ms: int):
        return self.build_payload(
            lane_index=lane_index,
            hit_error_ms=self.hit_error_ms(now_elapsed_ms),
            judgement=JudgementLevel.MISS,
            hold_ratio=0.0 if self.is_long else None,
        )

    def begin_long_hold(self, now_elapsed_ms: int, hit_error_ms: int):
        return {
            "note": self,
            "held_ms": 0,
            "last_sample_ms": int(now_elapsed_ms),
            "is_holding": True,
            "start_error_ms": int(hit_error_ms),
        }

    def update_long_hold(self, hold_state: dict, now_elapsed_ms: int, lane_is_pressed: bool):
        note_end_ms = int(self.end_time)
        if bool(hold_state.get("is_holding")) and lane_is_pressed:
            from_ms = max(int(hold_state.get("last_sample_ms", now_elapsed_ms)), int(self.start_time))
            to_ms = min(int(now_elapsed_ms), note_end_ms)
            if to_ms > from_ms:
                hold_state["held_ms"] = int(hold_state.get("held_ms", 0)) + (to_ms - from_ms)
            hold_state["last_sample_ms"] = int(now_elapsed_ms)

        if not lane_is_pressed and bool(hold_state.get("is_holding")):
            hold_state["is_holding"] = False

    def should_finalize_long_hold(self, now_elapsed_ms: int, lane_is_pressed: bool):
        return int(now_elapsed_ms) >= int(self.end_time) or not lane_is_pressed

    def finalize_long_hold(self, hold_state: dict, lane_index: int, now_elapsed_ms: int):
        if bool(hold_state.get("is_holding")):
            from_ms = max(int(hold_state.get("last_sample_ms", now_elapsed_ms)), int(self.start_time))
            to_ms = min(int(now_elapsed_ms), int(self.end_time))
            if to_ms > from_ms:
                hold_state["held_ms"] = int(hold_state.get("held_ms", 0)) + (to_ms - from_ms)

        duration_ms = max(1, int(self.duration_ms))
        hold_ratio = max(0.0, min(1.0, int(hold_state.get("held_ms", 0)) / duration_ms))
        return self.build_payload(
            lane_index=lane_index,
            hit_error_ms=int(hold_state.get("start_error_ms", 0)),
            hold_ratio=hold_ratio,
        )

    @classmethod
    def process_lane_input(
        cls,
        lane_index: int,
        lane_notes,
        lane_is_pressed: bool,
        trigger_count: int,
        now_elapsed_ms: int,
        hit_window_ms: int,
        active_hold,
    ):
        lane_notes = list(lane_notes)
        consumed_notes = []
        results = []
        hold_state = active_hold

        for _ in range(max(0, int(trigger_count))):
            closest_note = cls.find_closest_note(lane_notes, now_elapsed_ms)
            if closest_note is None:
                break

            hit_error_ms = closest_note.hit_error_ms(now_elapsed_ms)
            if abs(hit_error_ms) > int(hit_window_ms):
                break

            if closest_note.is_long:
                if hold_state is not None and bool(hold_state.get("is_holding")):
                    continue

                hold_state = closest_note.begin_long_hold(now_elapsed_ms, hit_error_ms)
                results.append(
                    closest_note.build_payload(
                        lane_index=lane_index,
                        hit_error_ms=hit_error_ms,
                        hold_ratio=None,
                    )
                )
                continue

            lane_notes.remove(closest_note)
            consumed_notes.append(closest_note)
            results.append(
                closest_note.build_payload(
                    lane_index=lane_index,
                    hit_error_ms=hit_error_ms,
                    hold_ratio=None,
                )
            )

        if hold_state is not None:
            held_note = hold_state.get("note")
            if held_note is not None:
                held_note.update_long_hold(hold_state, now_elapsed_ms, lane_is_pressed)
                if held_note.should_finalize_long_hold(now_elapsed_ms, lane_is_pressed):
                    results.append(held_note.finalize_long_hold(hold_state, lane_index, now_elapsed_ms))
                    consumed_notes.append(held_note)
                    hold_state = None

        return {
            "results": results,
            "consumed_notes": consumed_notes,
            "active_hold": hold_state,
        }

    def draw_note(self, width, note_speed, **kwargs):
        """
                Return a solid rectangle note surface.

                Parameters
                ----------
                width: int
                    Render width in pixels, typically lane width.
                note_speed: float
                    Reserved for cross-note API consistency.
                kwargs:
                    note_height (int): explicit note height in px.
                    min_height (int): floor for computed height.
                    height_scale (float): multiplier for speed-based height.
                """
        note_width = max(1, int(width))
        min_height = max(1, int(kwargs.get("min_height", 18)))
        note_speed_px_per_ms = abs(float(note_speed)) / 1000.0

        if self.is_long:
            # Bottom is aligned to start_stamp by PlaySpace, so long-note top reaches end_stamp.
            duration_height = int(self.duration_ms * note_speed_px_per_ms)
            note_height = max(min_height, duration_height)
        else:
            explicit_height = kwargs.get("note_height", self.TAP_NOTE_HEIGHT)
            note_height = max(min_height, int(explicit_height))

        note_surface = pygame.Surface((note_width, note_height), pygame.SRCALPHA)
        note_surface.fill(self.resolved_color())
        self._draw_note_border(note_surface)
        return note_surface

    def _draw_note_border(self, note_surface):
        border_width = int(self.NOTE_BORDER_WIDTH)
        if border_width <= 0:
            return

        width, height = note_surface.get_size()
        if width <= 1 or height <= 1:
            return

        pygame.draw.rect(
            note_surface,
            self.NOTE_BORDER_COLOR,
            note_surface.get_rect(),
            width=min(border_width, max(1, min(width, height) // 2)),
        )

    def get_score(self, judgement: JudgementLevel, **kwargs):
        match judgement:
            case JudgementLevel.CRITPERFECT:
                return (self.base_score * Config.CRITICAL_PERFECT_SCORE) , self.bonus_score
            case JudgementLevel.PERFECT:
                return (self.base_score * Config.PERFECT_SCORE), 0
            case JudgementLevel.GREAT:
                return (self.base_score * Config.GREAT_SCORE), 0
            case JudgementLevel.GOOD:
                return (self.base_score * Config.GOOD_SCORE), 0
            case JudgementLevel.MISS:
                return 0, 0