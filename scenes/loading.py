from pathlib import Path

import pygame

from components.game_manager import GameManager
from components.scene_base import SceneBase
from scenes.play_space import PlaySpace


class Loading(SceneBase):
	def __init__(self, song, chart, difficulty_color):
		super().__init__()
		self._song = song
		self._chart = chart
		self._difficulty_color = difficulty_color or (194, 200, 214)

		self._background_color = (18, 22, 31)
		self._panel_color = (26, 31, 43)
		self._text_color = (240, 244, 252)
		self._subtle_text_color = (167, 176, 197)

		self._title_font = self._create_font(34, bold=True)
		self._name_font = self._create_font(22, bold=True)
		self._meta_font = self._create_font(18)
		self._small_font = self._create_font(14)

		self._min_display_ms = 1000
		self._started_ms = pygame.time.get_ticks()
		self._game_manager = GameManager(
			self._song,
			self._chart,
			self._chart.notes,
			self._chart.obstacles,
		)

	def _create_font(self, size, bold=False):
		candidates = [
			"meiryo",
			"yu gothic ui",
			"yugothic",
			"ms gothic",
			"msgothic",
			"noto sans cjk jp",
			"arial unicode ms",
			"segoe ui",
			"arial",
		]
		for name in candidates:
			font_path = pygame.font.match_font(name)
			if font_path:
				font = pygame.font.Font(font_path, size)
				font.set_bold(bold)
				return font

		fallback = pygame.font.SysFont(None, size)
		fallback.set_bold(bold)
		return fallback

	def _load_image(self, image_path, size):
		surface = pygame.Surface(size)
		surface.fill((56, 64, 86))
		pygame.draw.rect(surface, (89, 99, 127), surface.get_rect(), width=2)

		try:
			if image_path and Path(image_path).is_file():
				loaded = pygame.image.load(str(image_path)).convert_alpha()
				surface = pygame.transform.smoothscale(loaded, size)
		except Exception as error:
			print(f"Warning: Failed to load jacket image '{image_path}': {error}")

		return surface

	@staticmethod
	def _format_level(level):
		return f"{level:g}" if isinstance(level, (int, float)) else str(level)

	def process_input(self, events):
		for event in events:
			if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
				from scenes.song_select import SongSelect

				self.switch_to_scene(SongSelect())

	def update(self):
		if pygame.time.get_ticks() - self._started_ms >= self._min_display_ms:
			self.switch_to_scene(PlaySpace(self._game_manager))


	def render(self, screen):
		screen.fill(self._background_color)

		width, height = screen.get_size()
		panel_width = min(760, max(320, width - 80))
		panel_height = min(500, max(280, height - 80))
		panel = pygame.Rect(
			(width - panel_width) // 2,
			(height - panel_height) // 2,
			panel_width,
			panel_height,
		)

		pygame.draw.rect(screen, self._panel_color, panel, border_radius=16)
		pygame.draw.rect(screen, (73, 86, 114), panel, width=2, border_radius=16)

		title_surface = self._title_font.render("Loading", True, self._text_color)
		screen.blit(title_surface, title_surface.get_rect(midtop=(panel.centerx, panel.y + 18)))

		jacket_size = min(220, panel_height - 180)
		jacket_surface = self._load_image(self._song.jacket_path, (jacket_size, jacket_size))
		jacket_rect = jacket_surface.get_rect(left=panel.x + 30, top=panel.y + 90)
		screen.blit(jacket_surface, jacket_rect)

		frame_rect = jacket_rect.inflate(12, 12)
		pygame.draw.rect(screen, self._difficulty_color, frame_rect, width=5, border_radius=10)

		text_left = frame_rect.right + 28
		text_width = panel.right - text_left - 24

		name_surface = self._name_font.render(self._song.title, True, self._text_color)
		name_clip = pygame.Rect(text_left, jacket_rect.y + 10, text_width, self._name_font.get_height())
		prev_clip = screen.get_clip()
		screen.set_clip(name_clip)
		screen.blit(name_surface, (name_clip.x, name_clip.y))
		screen.set_clip(prev_clip)

		artist_surface = self._meta_font.render(f"Artist: {self._song.artist}", True, self._subtle_text_color)
		screen.blit(artist_surface, (text_left, name_clip.bottom + 16))

		chart_surface = self._meta_font.render(
			f"Chart Designer: {self._chart.chart_author}",
			True,
			self._subtle_text_color,
		)
		screen.blit(chart_surface, (text_left, name_clip.bottom + 48))

		diff_surface = self._meta_font.render(
			f"Difficulty: {self._chart.name} Lv.{self._format_level(self._chart.level)}",
			True,
			self._difficulty_color,
		)
		screen.blit(diff_surface, (text_left, name_clip.bottom + 80))

		hint_surface = self._small_font.render("Press ESC to return", True, self._subtle_text_color)
		screen.blit(hint_surface, hint_surface.get_rect(bottomright=(panel.right - 20, panel.bottom - 16)))

