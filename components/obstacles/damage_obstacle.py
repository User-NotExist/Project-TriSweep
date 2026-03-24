from components.obstacles.obstacle_base import ObstacleBase
import pygame


class DamageObstacle(ObstacleBase):
    def __init__(self, start_stamp, end_stamp, lane, color_override):
        super().__init__(start_stamp, end_stamp, lane, 3, color_override)
        self.base_score = 100

    def draw_obstacle(self, width, note_speed, **kwargs):
        return super().draw_obstacle(width, note_speed, **kwargs)
