from config import Config
from pathlib import Path
import pygame


class Player:
    SPRITE_WIDTH_RATIO = 0.7

    def __init__(self):
        self._path_to_img = Path(Config.PLAYER_IMAGE_PATH)
        self._base_surface = None
        self._scaled_cache = {}
        self._load_base_surface()

    def _load_base_surface(self):
        image_path = self._path_to_img
        if not image_path.is_absolute():
            image_path = (Config.BASE_DIR / image_path).resolve()

        try:
            self._base_surface = pygame.image.load(str(image_path)).convert_alpha()
        except Exception:
            self._base_surface = None

    def _get_scaled_surface(self, target_width: int):
        if self._base_surface is None or target_width <= 0:
            return None

        target_width = int(target_width)
        if target_width in self._scaled_cache:
            return self._scaled_cache[target_width]

        source_width, source_height = self._base_surface.get_size()
        if source_width <= 0 or source_height <= 0:
            return None

        scale_ratio = target_width / source_width
        target_height = max(1, int(source_height * scale_ratio))
        scaled_surface = pygame.transform.smoothscale(self._base_surface, (target_width, target_height))
        self._scaled_cache[target_width] = scaled_surface
        return scaled_surface

    def render(self, screen, lane_center_x: int, lane_width: int, judgement_line_y: int):
        target_width = int(lane_width * self.SPRITE_WIDTH_RATIO)
        sprite = self._get_scaled_surface(target_width)
        if sprite is None:
            return

        sprite_rect = sprite.get_rect()
        sprite_rect.centerx = lane_center_x
        sprite_rect.centery = judgement_line_y
        screen.blit(sprite, sprite_rect)
