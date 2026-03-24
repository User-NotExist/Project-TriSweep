from components.obstacles.obstacle_base import ObstacleBase
import pygame


class CollectObstacle(ObstacleBase):
    def __init__(self, start_stamp, end_stamp, lane, color_override):
        super().__init__(start_stamp, end_stamp, lane, 4, color_override)
        self.base_score = 100
        if self.end_time != -1:
            self.base_score = 200

    def draw_obstacle(self, width, note_speed, **kwargs):
        obstacle_width = max(1, int(width))
        min_height = max(1, int(kwargs.get("min_height", 18)))
        obstacle_speed_px_per_ms = abs(float(note_speed)) / 1000.0

        if self.is_long:
            duration_height = int(self.duration_ms * obstacle_speed_px_per_ms)
            obstacle_height = max(min_height, duration_height)
        else:
            obstacle_height = max(min_height, int(kwargs.get("obstacle_height", self.TAP_OBSTACLE_HEIGHT)))

        obstacle_surface = pygame.Surface((obstacle_width, obstacle_height), pygame.SRCALPHA)
        capsule_rect = obstacle_surface.get_rect()
        capsule_radius = max(1, min(capsule_rect.width, capsule_rect.height) // 2)

        pygame.draw.rect(
            obstacle_surface,
            self.resolved_color(),
            capsule_rect,
            border_radius=capsule_radius,
        )
        pygame.draw.rect(
            obstacle_surface,
            self.OBSTACLE_BORDER_COLOR,
            capsule_rect,
            width=max(1, int(self.OBSTACLE_BORDER_WIDTH)),
            border_radius=capsule_radius,
        )

        return obstacle_surface
