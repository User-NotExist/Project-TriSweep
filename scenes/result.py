import pygame

from components.scene_base import SceneBase
from components.play_data import PlayData


class Result(SceneBase):
	def __init__(self, play_data: PlayData):
		super().__init__()
		self._play_data = play_data
		self._result_file_path = self._play_data.save_to_json()
		self._song = self._play_data.song
		self._chart = self._play_data.chart

		self._background_color = (18, 22, 31)
		self._panel_color = (26, 31, 43)
		self._panel_border_color = (73, 86, 114)
		self._text_color = (240, 244, 252)
		self._subtle_text_color = (167, 176, 197)
		self._accent_color = self._difficulty_color(getattr(self._chart, "name", ""))

		self._button_color = (55, 66, 90)
		self._button_hover_color = (77, 97, 132)
		self._button_border_color = (110, 131, 170)

		self._title_font = self._create_font(44, bold=True)
		self._heading_font = self._create_font(28, bold=True)
		self._body_font = self._create_font(22)
		self._button_font = self._create_font(24, bold=True)

		self._retry_button_rect = pygame.Rect(0, 0, 0, 0)
		self._back_button_rect = pygame.Rect(0, 0, 0, 0)


	@staticmethod
	def _create_font(size, bold=False):
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

	@staticmethod
	def _difficulty_color(name):
		key = str(name or "").strip().lower()
		color_map = {
			"easy": (52, 235, 58),
			"advanced": (250, 165, 37),
			"expert": (250, 41, 37),
			"master": (237, 71, 255),
		}
		return color_map.get(key, (194, 200, 214))

	def _go_to_song_select(self):
		from scenes.song_select import SongSelect

		self.switch_to_scene(SongSelect())

	def _retry_chart(self):
		from scenes.loading import Loading

		self.switch_to_scene(
			Loading(
				self._song,
				self._chart,
				self._difficulty_color(getattr(self._chart, "name", "")),
			)
		)

	def process_input(self, events):
		for event in events:
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					self._go_to_song_select()
					continue
				if event.key == pygame.K_r:
					self._retry_chart()
					continue

			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				if self._retry_button_rect.collidepoint(event.pos):
					self._retry_chart()
					continue
				if self._back_button_rect.collidepoint(event.pos):
					self._go_to_song_select()

	def update(self):
		pass

	def _draw_button(self, screen, rect: pygame.Rect, text: str, hovered: bool):
		fill_color = self._button_hover_color if hovered else self._button_color
		pygame.draw.rect(screen, fill_color, rect, border_radius=10)
		pygame.draw.rect(screen, self._button_border_color, rect, width=2, border_radius=10)

		label = self._button_font.render(text, True, self._text_color)
		screen.blit(label, label.get_rect(center=rect.center))

	def render(self, screen):
		screen.fill(self._background_color)

		width, height = screen.get_size()
		panel_width = min(900, max(460, width - 120))
		panel_height = min(620, max(380, height - 100))
		panel = pygame.Rect(
			(width - panel_width) // 2,
			(height - panel_height) // 2,
			panel_width,
			panel_height,
		)

		pygame.draw.rect(screen, self._panel_color, panel, border_radius=16)
		pygame.draw.rect(screen, self._panel_border_color, panel, width=2, border_radius=16)

		title = self._title_font.render("Result", True, self._text_color)
		screen.blit(title, title.get_rect(midtop=(panel.centerx, panel.y + 20)))

		score_pct = f"{self._play_data.current_score / 10000:.4f}%"
		score_title = self._heading_font.render("Final Score", True, self._subtle_text_color)
		score_value = self._heading_font.render(score_pct, True, self._accent_color)
		screen.blit(score_title, score_title.get_rect(midtop=(panel.centerx, panel.y + 92)))
		screen.blit(score_value, score_value.get_rect(midtop=(panel.centerx, panel.y + 128)))

		song_title = getattr(self._song, "title", "Unknown Song")
		artist_name = getattr(self._song, "artist", "Unknown Artist")
		chart_name = getattr(self._chart, "name", "Unknown Chart")
		chart_author = getattr(self._chart, "chart_author", "Unknown")

		detail_lines = [
			f"Song: {song_title}",
			f"Artist: {artist_name}",
			f"Chart: {chart_name} / {chart_author}",
			f"Max Combo: {self._play_data.highest_combo} / {self._play_data.max_combo}",
			"R: Retry    ESC: Back to Song Select",
		]

		current_y = panel.y + 196
		for index, line in enumerate(detail_lines):
			color = self._subtle_text_color if index < len(detail_lines) - 1 else self._text_color
			line_surface = self._body_font.render(line, True, color)
			screen.blit(line_surface, line_surface.get_rect(midtop=(panel.centerx, current_y)))
			current_y += 40

		button_width = 220
		button_height = 56
		button_gap = 24
		buttons_total_width = (button_width * 2) + button_gap
		button_start_x = panel.centerx - (buttons_total_width // 2)
		button_y = panel.bottom - button_height - 28

		self._retry_button_rect = pygame.Rect(button_start_x, button_y, button_width, button_height)
		self._back_button_rect = pygame.Rect(
			button_start_x + button_width + button_gap,
			button_y,
			button_width,
			button_height,
		)

		mouse_pos = pygame.mouse.get_pos()
		self._draw_button(
			screen,
			self._retry_button_rect,
			"Retry",
			self._retry_button_rect.collidepoint(mouse_pos),
		)
		self._draw_button(
			screen,
			self._back_button_rect,
			"Song Select",
			self._back_button_rect.collidepoint(mouse_pos),
		)

