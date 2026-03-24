from components.local_enum.judgement_level import JudgementLevel
from config import Config
import pygame
import math


class ObstacleBase:
    """
    Lightweight obstacle model consumed by PlaySpace drawing code.

    IMPORTANT: chart files use the CSV column name `type`, but program code uses
    `obstacle_type` to avoid confusion with Python's built-in `type`.
    """

    VALID_LANES = {0, 1, 2}
    VALID_OBSTACLE_TYPES = {1, 2, 3, 4, 5, 6}

    # Fixed default color per obstacle type.
    OBSTACLE_TYPE_DEFAULT_COLORS = {
        3: (255, 0, 0),
        4: (0, 255, 0),
    }
    FALLBACK_COLOR = (220, 220, 220)
    OBSTACLE_BORDER_COLOR = (24, 28, 36)
    OBSTACLE_BORDER_WIDTH = 2
    TAP_OBSTACLE_HEIGHT = 24

    def __init__(self, start_stamp, end_stamp, lane, obstacle_type, color_override):
        self.validation_errors = []

        self.start_time = self._coerce_int(start_stamp, "start_stamp")
        self.end_time = self._coerce_int(end_stamp, "end_stamp")
        self.lane = self._coerce_int(lane, "lane")
        self.obstacle_type = self._coerce_int(obstacle_type, "obstacle_type")

        self._validate_lane()
        self._validate_obstacle_type()
        self._validate_time_range()

        self.color_override = self._coerce_color_override(color_override)

        self.base_score = 0

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
        return self.OBSTACLE_TYPE_DEFAULT_COLORS.get(self.obstacle_type, self.FALLBACK_COLOR)

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

    def _validate_obstacle_type(self):
        if self.obstacle_type not in self.VALID_OBSTACLE_TYPES:
            self.validation_errors.append(f"Invalid obstacle_type: {self.obstacle_type}")

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

    def draw_obstacle(self, width, obstacle_speed, **kwargs):
        """
                Return an obstacle surface composed of repeated circles.

                Parameters
                ----------
                width: int
                    Render width in pixels, typically lane width.
                obstacle_speed: float
                    Scroll speed in pixels per second.
                kwargs:
                    obstacle_height (int): explicit obstacle height in px.
                    min_height (int): floor for computed height.
                    circle_radius (int): radius for each circle.
                    circle_gap (int): spacing between circles.
                """
        obstacle_width = max(1, int(width))
        min_height = max(1, int(kwargs.get("min_height", 18)))
        obstacle_speed_px_per_ms = abs(float(obstacle_speed)) / 1000.0

        if self.is_long:
            duration_height = int(self.duration_ms * obstacle_speed_px_per_ms)
            obstacle_height = max(min_height, duration_height)
        else:
            explicit_height = kwargs.get("obstacle_height", self.TAP_OBSTACLE_HEIGHT)
            obstacle_height = max(min_height, int(explicit_height))

        obstacle_surface = pygame.Surface((obstacle_width, obstacle_height), pygame.SRCALPHA)

        # Build one horizontal line of touching circles that fully covers lane width.
        target_circle_size = max(2, int(kwargs.get("circle_size", max(8, obstacle_width // 10))))
        circle_count = max(1, math.ceil(obstacle_width / target_circle_size))
        circle_diameter = max(2, math.ceil(obstacle_width / circle_count))
        circle_radius = max(1, circle_diameter // 2)

        x_positions = []
        x_center = circle_radius
        while x_center < obstacle_width:
            x_positions.append(x_center)
            x_center += circle_diameter

        if not x_positions:
            x_positions = [obstacle_width // 2]
        elif x_positions[-1] + circle_radius < obstacle_width:
            x_positions.append(obstacle_width - circle_radius)

        if self.is_long:
            y_positions = []
            y_center = circle_radius
            while y_center < obstacle_height:
                y_positions.append(y_center)
                y_center += circle_diameter

            if not y_positions:
                y_positions = [obstacle_height // 2]
            elif y_positions[-1] + circle_radius < obstacle_height:
                y_positions.append(obstacle_height - circle_radius)
        else:
            y_positions = [obstacle_height // 2]

        fill_color = self.resolved_color()
        for center_y in y_positions:
            for center_x in x_positions:
                pygame.draw.circle(obstacle_surface, fill_color, (center_x, center_y), circle_radius)
                pygame.draw.circle(
                    obstacle_surface,
                    self.OBSTACLE_BORDER_COLOR,
                    (center_x, center_y),
                    circle_radius,
                    width=max(1, int(self.OBSTACLE_BORDER_WIDTH)),
                )

        return obstacle_surface

    def get_score(self, judgement: JudgementLevel, **kwargs):
        match judgement:
            case JudgementLevel.CRITPERFECT:
                return self.base_score * Config.CRITICAL_PERFECT_SCORE
            case JudgementLevel.MISS:
                return 0