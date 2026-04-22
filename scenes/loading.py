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

		self._min_display_ms = 2500
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

	@staticmethod
	def _format_duration(seconds):
		try:
			total_seconds = max(0, int(round(float(seconds))))
		except (TypeError, ValueError):
			return "0:00"

		minutes = total_seconds // 60
		remaining_seconds = total_seconds % 60
		return f"{minutes}:{remaining_seconds:02d}"

	def _draw_card(self, screen, rect, title=None, accent_color=None):
		pygame.draw.rect(screen, self._panel_color, rect, border_radius=14)
		pygame.draw.rect(screen, (73, 86, 114), rect, width=2, border_radius=14)

		if accent_color is not None:
			top_border = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, 6)
			pygame.draw.rect(screen, accent_color, top_border, border_radius=8)

		if title:
			title_surface = self._meta_font.render(title, True, self._text_color)
			screen.blit(title_surface, (rect.x + 16, rect.y + 14))

	def _draw_label_value(self, screen, card_rect, row_index, label, value, value_color=None):
		left_x = card_rect.x + 16
		top_y = card_rect.y + 54 + (row_index * 28)
		label_surface = self._small_font.render(label, True, self._subtle_text_color)
		value_surface = self._small_font.render(str(value), True, value_color or self._text_color)
		screen.blit(label_surface, (left_x, top_y))
		screen.blit(value_surface, value_surface.get_rect(topright=(card_rect.right - 16, top_y)))

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
		dashboard_width = min(980, max(420, width - 72))
		dashboard_height = min(640, max(360, height - 72))
		dashboard = pygame.Rect(
			(width - dashboard_width) // 2,
			(height - dashboard_height) // 2,
			dashboard_width,
			dashboard_height,
		)

		pygame.draw.rect(screen, (21, 27, 38), dashboard, border_radius=18)
		pygame.draw.rect(screen, (78, 92, 122), dashboard, width=2, border_radius=18)

		padding = 16
		gap = 12
		header_card = pygame.Rect(dashboard.x + padding, dashboard.y + padding, dashboard.width - (padding * 2), 82)
		footer_card = pygame.Rect(dashboard.x + padding, dashboard.bottom - padding - 84, dashboard.width - (padding * 2), 84)
		content_top = header_card.bottom + gap
		content_bottom = footer_card.y - gap
		content_height = max(120, content_bottom - content_top)

		left_column_width = max(180, int((dashboard.width - (padding * 2) - gap) * 0.34))
		left_card = pygame.Rect(dashboard.x + padding, content_top, left_column_width, content_height)
		right_column_width = dashboard.width - (padding * 2) - gap - left_column_width
		right_x = left_card.right + gap
		top_right_height = int((content_height - gap) * 0.52)
		top_right_card = pygame.Rect(right_x, content_top, right_column_width, top_right_height)
		bottom_right_card = pygame.Rect(right_x, top_right_card.bottom + gap, right_column_width, content_height - top_right_height - gap)

		self._draw_card(screen, header_card, title="", accent_color=self._difficulty_color)
		self._draw_card(screen, left_card, title="", accent_color=self._difficulty_color)
		self._draw_card(screen, top_right_card, title="Song", accent_color=(89, 198, 255))
		self._draw_card(screen, bottom_right_card, title="Chart", accent_color=(153, 225, 132))
		self._draw_card(screen, footer_card, title="Status", accent_color=(255, 190, 106))

		title_surface = self._title_font.render("Loading", True, self._text_color)
		screen.blit(title_surface, (header_card.x + 16, header_card.y + 28))
		diff_surface = self._meta_font.render(
			f"{self._chart.name}  Lv.{self._format_level(self._chart.level)}",
			True,
			self._difficulty_color,
		)
		screen.blit(diff_surface, diff_surface.get_rect(midright=(header_card.right - 20, header_card.y + 42)))

		jacket_size = min(left_card.width - 36, left_card.height - 78)
		jacket_size = max(64, jacket_size)
		jacket_surface = self._load_image(self._song.jacket_path, (jacket_size, jacket_size))
		jacket_rect = jacket_surface.get_rect(center=(left_card.centerx, left_card.y + 38 + (jacket_size // 2)))
		screen.blit(jacket_surface, jacket_rect)
		frame_rect = jacket_rect.inflate(10, 10)
		pygame.draw.rect(screen, self._difficulty_color, frame_rect, width=4, border_radius=10)

		self._draw_label_value(screen, top_right_card, 0, "Title", self._song.title)
		self._draw_label_value(screen, top_right_card, 1, "Artist", self._song.artist)
		self._draw_label_value(screen, top_right_card, 2, "BPM", f"{self._song.bpm:g}")
		self._draw_label_value(screen, top_right_card, 3, "Duration", self._format_duration(self._song.length))

		note_count = len(self._chart.notes)
		obstacle_count = len(self._chart.obstacles)
		speed_source = "Forced" if self._chart.forced_note_speed is not None else "Config"
		speed_value = self._chart.forced_note_speed if self._chart.forced_note_speed is not None else "-"
		self._draw_label_value(screen, bottom_right_card, 0, "Chart Designer", self._chart.chart_author)
		self._draw_label_value(screen, bottom_right_card, 1, "Objects", f"{note_count + obstacle_count}")
		self._draw_label_value(screen, bottom_right_card, 2, "Notes / Obstacles", f"{note_count} / {obstacle_count}")
		self._draw_label_value(screen, bottom_right_card, 3, "Speed Source", speed_source)
		self._draw_label_value(screen, bottom_right_card, 4, "Forced Speed", speed_value)

		elapsed_ms = max(0, pygame.time.get_ticks() - self._started_ms)
		progress_ratio = min(1.0, elapsed_ms / max(1, self._min_display_ms))
		bar_rect = pygame.Rect(footer_card.x + 16, footer_card.bottom - 28, footer_card.width - 32, 10)
		pygame.draw.rect(screen, (49, 58, 79), bar_rect, border_radius=6)
		filled_width = max(4, int(bar_rect.width * progress_ratio))
		filled_rect = pygame.Rect(bar_rect.x, bar_rect.y, min(bar_rect.width, filled_width), bar_rect.height)
		pygame.draw.rect(screen, self._difficulty_color, filled_rect, border_radius=6)

		status_surface = self._small_font.render("Preparing gameplay...", True, self._text_color)
		screen.blit(status_surface, (footer_card.x + 16, footer_card.y + 42))
		hint_surface = self._small_font.render("Press ESC to return", True, self._subtle_text_color)
		screen.blit(hint_surface, hint_surface.get_rect(topright=(footer_card.right - 16, footer_card.y + 42)))

