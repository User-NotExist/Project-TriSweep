from config import Config
from pathlib import Path
import pygame


class Player:
    SPRITE_WIDTH_RATIO = 0.7
    _DAMAGE_FLASH_DURATION_MS = 140
    _DAMAGE_FLASH_MAX_ALPHA = 135

    def __init__(self):
        self._path_to_img = Path(Config.PLAYER_IMAGE_PATH)
        self._base_surface = None
        self._scaled_cache = {}
        self._x_position = 0.0
        self._min_x = 0.0
        self._max_x = 0.0
        self._sprite_pixel_size = (0, 0)
        self._load_base_surface()
        self._health = 100
        self._damage_flash_end_ms = 0

    @property
    def x_position(self) -> float:
        return self._x_position

    @property
    def sprite_pixel_size(self):
        return self._sprite_pixel_size

    def set_x_position(self, x_position: float):
        self._x_position = max(self._min_x, min(float(x_position), self._max_x))

    def set_movement_bounds(self, min_x: float, max_x: float):
        self._min_x = float(min_x)
        self._max_x = float(max_x)
        if self._min_x > self._max_x:
            self._min_x, self._max_x = self._max_x, self._min_x
        self.set_x_position(self._x_position)

    def apply_mouse_delta(self, mouse_delta_x: float, speed_multiplier: float = 1.0):
        next_x = self._x_position + (float(mouse_delta_x) * float(speed_multiplier))
        self.set_x_position(next_x)

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
            self._sprite_pixel_size = (0, 0)
            return None

        target_width = int(target_width)
        if target_width in self._scaled_cache:
            self._sprite_pixel_size = self._scaled_cache[target_width].get_size()
            return self._scaled_cache[target_width]

        source_width, source_height = self._base_surface.get_size()
        if source_width <= 0 or source_height <= 0:
            return None

        scale_ratio = target_width / source_width
        target_height = max(1, int(source_height * scale_ratio))
        scaled_surface = pygame.transform.smoothscale(self._base_surface, (target_width, target_height))
        self._scaled_cache[target_width] = scaled_surface
        self._sprite_pixel_size = scaled_surface.get_size()
        return scaled_surface

    def render(self, screen, lane_width: int, judgement_line_y: int):
        target_width = int(lane_width * self.SPRITE_WIDTH_RATIO)
        sprite = self._get_scaled_surface(target_width)
        if sprite is None:
            return

        flash_alpha = self._get_damage_flash_alpha()
        if flash_alpha > 0:
            # Overlay a short red tint when damage is taken.
            tinted_sprite = sprite.copy()
            tinted_sprite.fill((255, 0, 0, int(flash_alpha)), special_flags=pygame.BLEND_RGBA_ADD)
            sprite = tinted_sprite

        sprite_rect = sprite.get_rect()
        sprite_rect.centerx = int(self._x_position)
        sprite_rect.centery = judgement_line_y
        screen.blit(sprite, sprite_rect)

    def apply_damage(self, damage: int):
        self._health -= damage

        if int(damage) > 0:
            self._damage_flash_end_ms = pygame.time.get_ticks() + self._DAMAGE_FLASH_DURATION_MS

        if self._health < 0:
            self._health = 0

    def apply_heal(self, heal: int):
        self._health += heal

        if self._health > 100:
            self._health = 100

    @property
    def health(self) -> int:
        return self._health

    def _get_damage_flash_alpha(self):
        remaining_ms = int(self._damage_flash_end_ms) - pygame.time.get_ticks()
        if remaining_ms <= 0:
            return 0

        ratio = max(0.0, min(1.0, remaining_ms / float(self._DAMAGE_FLASH_DURATION_MS)))
        return int(self._DAMAGE_FLASH_MAX_ALPHA * ratio)
