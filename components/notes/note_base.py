from components.local_enum.judgement_level import JudgementLevel
from config import Config


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
        2: (255, 178, 94),
        3: (164, 245, 124),
        4: (255, 140, 190),
        5: (201, 161, 255),
        6: (255, 102, 102),
    }
    FALLBACK_COLOR = (220, 220, 220)

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
            explicit_height = kwargs.get("note_height")
            if explicit_height is not None:
                note_height = max(1, int(explicit_height))
            else:
                height_scale = float(kwargs.get("height_scale", 0.2))
                computed_height = int(abs(float(note_speed)) * height_scale)
                note_height = max(min_height, computed_height)

        note_surface = pygame.Surface((note_width, note_height), pygame.SRCALPHA)
        note_surface.fill(self.resolved_color())
        return note_surface

    def get_score(self, judgement: JudgementLevel, **kwargs):
        match judgement:
            case JudgementLevel.CRITPERFECT:
                return (self.base_score * Config.CRITICAL_PERFECT_SCORE) + self.bonus_score
            case JudgementLevel.PERFECT:
                return (self.base_score * Config.PERFECT_SCORE)
            case JudgementLevel.GREAT:
                return (self.base_score * Config.GREAT_SCORE)
            case JudgementLevel.GOOD:
                return (self.base_score * Config.GOOD_SCORE)
