import pygame

from components.scene_base import SceneBase
from components.play_data import PlayData
from components.local_enum.judgement_level import JudgementLevel


class Result(SceneBase):
	GRADE_CRITERIA = [
		("SSS", 100.5000),
		("SS", 99.5000),
		("S", 98.0000),
		("A", 95.0000),
		("B", 90.0000),
		("C", 80.0000),
		("D", 0.0000),
	]

	GRADE_COLORS = {
		"SSS": (255, 235, 120),
		"SS": (255, 215, 95),
		"S": (255, 193, 84),
		"A": (133, 234, 137),
		"B": (108, 179, 255),
		"C": (198, 168, 255),
		"D": (255, 112, 112),
	}

	JUDGEMENT_KEYS = [
		JudgementLevel.CRITPERFECT.name,
		JudgementLevel.PERFECT.name,
		JudgementLevel.GREAT.name,
		JudgementLevel.GOOD.name,
		JudgementLevel.MISS.name,
	]

	JUDGEMENT_COLORS = {
		JudgementLevel.CRITPERFECT.name: (247, 255, 120),
		JudgementLevel.PERFECT.name: (126, 241, 132),
		JudgementLevel.GREAT.name: (103, 171, 255),
		JudgementLevel.GOOD.name: (255, 191, 98),
		JudgementLevel.MISS.name: (255, 94, 94),
	}

	def __init__(self, play_data: PlayData):
		super().__init__()
		self._play_data = play_data
		self._result_file_path = self._play_data.save_to_json()
		self._song = self._play_data.song
		self._chart = self._play_data.chart
		self._serialized = self._play_data.to_serializable_dict()

		self._background_color = (18, 22, 31)
		self._panel_color = (26, 31, 43)
		self._panel_border_color = (73, 86, 114)
		self._text_color = (240, 244, 252)
		self._subtle_text_color = (167, 176, 197)
		self._accent_color = self._difficulty_color(getattr(self._chart, "name", ""))

		self._button_color = (55, 66, 90)
		self._button_hover_color = (77, 97, 132)
		self._button_border_color = (110, 131, 170)

		self._title_font = self._create_font(40, bold=True)
		self._heading_font = self._create_font(22, bold=True)
		self._body_font = self._create_font(18)
		self._small_font = self._create_font(15)
		self._button_font = self._create_font(22, bold=True)
		self._grade_font = self._create_font(54, bold=True)
		self._tab_font = self._create_font(18, bold=True)

		self._retry_button_rect = pygame.Rect(0, 0, 0, 0)
		self._back_button_rect = pygame.Rect(0, 0, 0, 0)
		self._tab_rects = []
		self._tabs = ["Overview", "Timing", "Movement"]
		self._active_tab_index = 0


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

	@staticmethod
	def _safe_int(value, fallback=0):
		try:
			return int(value)
		except (TypeError, ValueError):
			return fallback

	def _extract_metrics(self):
		total_score = self._safe_int(self._serialized.get("total_score"), self._safe_int(self._play_data.current_score))
		max_score = sum(PlayData.PERCENTAGE_WEIGHT.values())
		score_ratio = (float(total_score) / float(max_score)) if max_score > 0 else 0.0
		overall_score = float(total_score) / 10000.0

		grade = "D"
		for grade_name, threshold in self.GRADE_CRITERIA:
			if overall_score >= threshold:
				grade = grade_name
				break

		note_hits = self._serialized.get("recorded_note_hit", [])
		judgement_count = {key: 0 for key in self.JUDGEMENT_KEYS}
		fast_count = 0
		late_count = 0
		hit_errors = []

		for entry in note_hits:
			judgement_name = str(entry.get("judgement_level", "MISS")).upper()
			if judgement_name in judgement_count:
				judgement_count[judgement_name] += 1

			hit_error = self._safe_int(entry.get("hit_error"), 0)
			if hit_error < 0:
				fast_count += 1
			elif hit_error > 0:
				late_count += 1
			if judgement_name != JudgementLevel.MISS.name:
				hit_errors.append(abs(hit_error))

		total_notes = len(note_hits)
		non_miss = total_notes - judgement_count[JudgementLevel.MISS.name]
		clear_rate = (float(non_miss) / float(total_notes) * 100.0) if total_notes > 0 else 0.0
		avg_hit_error = (sum(hit_errors) / len(hit_errors)) if hit_errors else 0.0

		highest_combo = self._safe_int(self._serialized.get("highest_combo"), self._safe_int(self._play_data.highest_combo))
		max_combo = self._safe_int(self._serialized.get("max_combo"), self._safe_int(self._play_data.max_combo))
		combo_rate = (float(highest_combo) / float(max_combo) * 100.0) if max_combo > 0 else 0.0

		return {
			"total_score": total_score,
			"max_score": max_score,
			"score_ratio": score_ratio,
			"overall_score": overall_score,
			"grade": grade,
			"judgement_count": judgement_count,
			"total_notes": total_notes,
			"clear_rate": clear_rate,
			"highest_combo": highest_combo,
			"max_combo": max_combo,
			"combo_rate": combo_rate,
			"avg_hit_error": avg_hit_error,
			"fast_count": fast_count,
			"late_count": late_count,
		}

	def process_input(self, events):
		for event in events:
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					self._go_to_song_select()
					continue
				if event.key == pygame.K_r:
					self._retry_chart()
					continue
				if event.key == pygame.K_LEFT:
					self._active_tab_index = max(0, self._active_tab_index - 1)
					continue
				if event.key == pygame.K_RIGHT:
					self._active_tab_index = min(len(self._tabs) - 1, self._active_tab_index + 1)
					continue

			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				for tab_index, tab_rect in enumerate(self._tab_rects):
					if tab_rect.collidepoint(event.pos):
						self._active_tab_index = tab_index
						break

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

	def _draw_tabs(self, screen, panel: pygame.Rect):
		tab_height = 38
		tab_y = panel.y + 78
		tab_gap = 8
		tab_left = panel.x + 24
		tab_width = 160

		self._tab_rects = []
		for i, tab_name in enumerate(self._tabs):
			rect = pygame.Rect(tab_left + i * (tab_width + tab_gap), tab_y, tab_width, tab_height)
			self._tab_rects.append(rect)
			is_active = i == self._active_tab_index
			fill = (58, 80, 126) if is_active else (34, 42, 59)
			border = (117, 160, 255) if is_active else self._panel_border_color
			pygame.draw.rect(screen, fill, rect, border_radius=8)
			pygame.draw.rect(screen, border, rect, width=2, border_radius=8)
			label = self._tab_font.render(tab_name, True, self._text_color)
			screen.blit(label, label.get_rect(center=rect.center))

	def _draw_overview_tab(self, screen, panel: pygame.Rect, metrics: dict):
		content_rect = pygame.Rect(panel.x + 24, panel.y + 132, panel.width - 48, panel.height - 240)
		grade_color = self.GRADE_COLORS.get(metrics["grade"], self._accent_color)

		left_card = pygame.Rect(content_rect.x, content_rect.y, int(content_rect.width * 0.44), 188)
		right_card = pygame.Rect(left_card.right + 16, content_rect.y, content_rect.width - left_card.width - 16, 188)
		bottom_card = pygame.Rect(content_rect.x, left_card.bottom + 16, content_rect.width, content_rect.height - left_card.height - 16)

		for card in (left_card, right_card, bottom_card):
			pygame.draw.rect(screen, (31, 38, 54), card, border_radius=12)
			pygame.draw.rect(screen, (72, 85, 113), card, width=2, border_radius=12)

		score_title = self._heading_font.render("Overall Score", True, self._subtle_text_color)
		score_value = self._grade_font.render(f"{metrics['overall_score']:.4f}%", True, grade_color)
		screen.blit(score_title, (left_card.x + 16, left_card.y + 16))
		screen.blit(score_value, (left_card.x + 16, left_card.y + 52))

		grade_title = self._heading_font.render("Grade", True, self._subtle_text_color)
		grade_value = self._grade_font.render(metrics["grade"], True, grade_color)
		combo_line = self._body_font.render(
			f"Combo {metrics['highest_combo']} / {metrics['max_combo']} ({metrics['combo_rate']:.1f}%)",
			True,
			self._text_color,
		)
		screen.blit(grade_title, (right_card.x + 16, right_card.y + 16))
		screen.blit(grade_value, (right_card.x + 16, right_card.y + 40))
		screen.blit(combo_line, (right_card.x + 16, right_card.y + 136))

		breakdown_title = self._heading_font.render("Judgement Breakdown", True, self._subtle_text_color)
		screen.blit(breakdown_title, (bottom_card.x + 16, bottom_card.y + 14))

		row_y = bottom_card.y + 52
		for key in self.JUDGEMENT_KEYS:
			count_value = metrics["judgement_count"].get(key, 0)
			label = self._body_font.render(f"{key}", True, self.JUDGEMENT_COLORS.get(key, self._text_color))
			value = self._body_font.render(str(count_value), True, self._text_color)
			screen.blit(label, (bottom_card.x + 16, row_y))
			screen.blit(value, value.get_rect(topright=(bottom_card.x + 190, row_y)))
			row_y += 34

		extra_lines = [
			f"Clear Rate: {metrics['clear_rate']:.2f}%",
			f"Avg |Hit Error|: {metrics['avg_hit_error']:.1f} ms",
			f"Fast / Late: {metrics['fast_count']} / {metrics['late_count']}",
			f"Play No.: {self._serialized.get('play_number', 1)}",
		]
		extra_y = bottom_card.y + 52
		extra_x = bottom_card.x + 250
		for line in extra_lines:
			text = self._body_font.render(line, True, self._text_color)
			screen.blit(text, (extra_x, extra_y))
			extra_y += 34

	def _draw_placeholder_tab(self, screen, panel: pygame.Rect):
		content_rect = pygame.Rect(panel.x + 24, panel.y + 132, panel.width - 48, panel.height - 240)
		pygame.draw.rect(screen, (31, 38, 54), content_rect, border_radius=12)
		pygame.draw.rect(screen, (72, 85, 113), content_rect, width=2, border_radius=12)
		label = self._heading_font.render("Placeholder tab for future metrics", True, self._subtle_text_color)
		hint = self._body_font.render("Use LEFT/RIGHT or click tabs to switch views.", True, self._text_color)
		screen.blit(label, label.get_rect(center=(content_rect.centerx, content_rect.centery - 16)))
		screen.blit(hint, hint.get_rect(center=(content_rect.centerx, content_rect.centery + 20)))

	def render(self, screen):
		screen.fill(self._background_color)

		width, height = screen.get_size()
		panel = pygame.Rect(0, 0, width, height)

		title = self._title_font.render("Result Dashboard", True, self._text_color)
		screen.blit(title, title.get_rect(midtop=(panel.centerx, panel.y + 18)))

		song_title = getattr(self._song, "title", "Unknown Song")
		chart_name = getattr(self._chart, "name", "Unknown Chart")
		subtitle = self._small_font.render(f"{song_title}  |  {chart_name}", True, self._subtle_text_color)
		screen.blit(subtitle, subtitle.get_rect(midtop=(panel.centerx, panel.y + 58)))

		self._draw_tabs(screen, panel)
		metrics = self._extract_metrics()

		if self._active_tab_index == 0:
			self._draw_overview_tab(screen, panel, metrics)
		else:
			self._draw_placeholder_tab(screen, panel)

		footnote = self._small_font.render(f"Saved: {self._result_file_path.name}", True, self._subtle_text_color)
		screen.blit(footnote, (24, panel.bottom - 84))

		button_width = 220
		button_height = 56
		button_gap = 24
		buttons_total_width = (button_width * 2) + button_gap
		button_start_x = panel.centerx - (buttons_total_width // 2)
		button_y = panel.bottom - button_height - 20

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

