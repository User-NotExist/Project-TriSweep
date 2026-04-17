import pygame
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import math
import random

from components.scene_base import SceneBase
from components.play_data import PlayData
from components.local_enum.judgement_level import JudgementLevel
from pathlib import Path


class Result(SceneBase):
	GRADE_CRITERIA = [
        ("SSS+", 100.5000),
		("SSS", 100.0000),
        ("SS+", 99.5000),
		("SS", 99.0000),
        ("S+", 98.0000),
		("S", 97.0000),
        ("AAA", 95.0000),
        ("AA", 90.0000),
		("A", 80.0000),
		("B", 70.0000),
		("C", 60.0000),
		("D", 0.0000),
	]

	GRADE_COLORS = {
        "SSS+": (173, 242, 44),
		"SSS": (173, 242, 44),
		"SS+": (249, 255, 66),
        "SS": (249, 255, 66),
        "S+": (245, 197, 86),
		"S": (245, 197, 86),
		"AAA": (230, 101, 225),
        "AA": (230, 101, 225),
        "A": (230, 101, 225),
		"B": (39, 221, 227),
		"C": (39, 221, 227),
		"D": (39, 221, 227),
	}

	END_STATUS_COLORS = {
		"CLEAR": (110, 224, 130),
		"NOT CLEAR": (255, 184, 94),
		"DIED": (255, 106, 106),
		"SKIP": (164, 174, 192),
	}

	JUDGEMENT_KEYS = [
		JudgementLevel.CRITPERFECT.name,
		JudgementLevel.PERFECT.name,
		JudgementLevel.GREAT.name,
		JudgementLevel.GOOD.name,
		JudgementLevel.MISS.name,
	]

	JUDGEMENT_COLORS = {
		JudgementLevel.CRITPERFECT.name: (252, 227, 3),
		JudgementLevel.PERFECT.name: (222, 159, 22),
		JudgementLevel.GREAT.name: (234, 72, 240),
		JudgementLevel.GOOD.name: (84, 227, 27),
		JudgementLevel.MISS.name: (255, 110, 110),
	}

	NOTE_TYPE_NAMES = {
		1: "Normal",
		2: "Break",
		3: "Damage Obstacle",
		4: "Collect Obstacle",
		5: "Normal Stripe",
		6: "Break Stripe",
	}

	def __init__(
		self,
		play_data: PlayData | None,
		serialized_record: dict | None = None,
		song=None,
		chart=None,
		result_file_path: str | None = None,
	):
		super().__init__()
		self._play_data = play_data
		self._is_loaded_from_json_record = self._play_data is None and serialized_record is not None

		if self._play_data is not None:
			self._result_file_path = self._play_data.save_to_json()
			self._song = self._play_data.song
			self._chart = self._play_data.chart
			self._serialized = self._play_data.to_serializable_dict()
		else:
			self._serialized = dict(serialized_record or {})
			self._song = song
			self._chart = chart
			self._result_file_path = Path(result_file_path) if result_file_path else None

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
		self._end_status_font = self._create_font(52, bold=True)
		self._tab_font = self._create_font(18, bold=True)

		self._retry_button_rect = pygame.Rect(0, 0, 0, 0)
		self._back_button_rect = pygame.Rect(0, 0, 0, 0)
		self._tab_rects = []
		self._tabs = ["Overview", "Timing", "Movement", "Combo", "Notes", "Side"]
		self._active_tab_index = 0
		self._timing_hist_surface = None
		self._timing_hist_cache_key = None
		self._movement_line_surface = None
		self._movement_line_cache_key = None
		self._combo_line_surface = None
		self._combo_line_cache_key = None
		self._notes_chart_surface = None
		self._notes_chart_cache_key = None
		self._side_chart_surface = None
		self._side_chart_cache_key = None


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

	def _display_song_title(self):
		if self._song is not None:
			return getattr(self._song, "title", "Unknown Song")
		return str(self._serialized.get("song_title", "Unknown Song"))

	def _display_chart_name(self):
		if self._chart is not None:
			return getattr(self._chart, "name", "Unknown Chart")
		return str(self._serialized.get("chart_name", "Unknown Chart"))

	def _go_to_song_select(self):
		from scenes.song_select import SongSelect

		self.switch_to_scene(SongSelect())

	def _retry_chart(self):
		if self._song is None or self._chart is None:
			return

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

	@staticmethod
	def _normalize_judgement_name(value):
		raw = str(value or "").strip().upper()
		if "." in raw:
			raw = raw.split(".")[-1]
		raw = raw.replace(" ", "").replace("-", "").replace("_", "")

		alias_map = {
			"CRITPERFECT": JudgementLevel.CRITPERFECT.name,
			"CRITICALPERFECT": JudgementLevel.CRITPERFECT.name,
			"PERFECT": JudgementLevel.PERFECT.name,
			"GREAT": JudgementLevel.GREAT.name,
			"GOOD": JudgementLevel.GOOD.name,
			"MISS": JudgementLevel.MISS.name,
		}
		return alias_map.get(raw, JudgementLevel.MISS.name)

	def _extract_metrics(self):
		fallback_score = self._safe_int(self._play_data.current_score) if self._play_data is not None else 0
		total_score = self._safe_int(self._serialized.get("total_score"), fallback_score)
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
			judgement_name = self._normalize_judgement_name(entry.get("judgement_level", "MISS"))
			if judgement_name in judgement_count:
				judgement_count[judgement_name] += 1

			hit_error = self._safe_int(entry.get("hit_error"), 0)
			if hit_error < 0:
				fast_count += 1
			elif hit_error > 0:
				late_count += 1
			if judgement_name != JudgementLevel.MISS.name:
				hit_errors.append(hit_error)

		total_notes = len(note_hits)
		non_miss = total_notes - judgement_count[JudgementLevel.MISS.name]
		clear_rate = (float(non_miss) / float(total_notes) * 100.0) if total_notes > 0 else 0.0
		mean_offset = (sum(hit_errors) / len(hit_errors)) if hit_errors else 0.0
		unstable_rate = (
			math.sqrt(sum((error - mean_offset) ** 2 for error in hit_errors) / len(hit_errors))
			if hit_errors
			else 0.0
		)

		fallback_highest_combo = self._safe_int(self._play_data.highest_combo) if self._play_data is not None else 0
		fallback_max_combo = self._safe_int(self._play_data.max_combo) if self._play_data is not None else 0
		highest_combo = self._safe_int(self._serialized.get("highest_combo"), fallback_highest_combo)
		max_combo = self._safe_int(self._serialized.get("max_combo"), fallback_max_combo)
		combo_rate = (float(highest_combo) / float(max_combo) * 100.0) if max_combo > 0 else 0.0

		round_end_reason = str(self._serialized.get("round_end_reason", "completed")).strip().lower()
		if round_end_reason == "died":
			end_status = "DIED"
		elif round_end_reason == "skipped":
			end_status = "SKIP"
		else:
			end_status = "CLEAR" if total_score >= 800000 else "NOT CLEAR"

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
			"mean_offset": mean_offset,
			"unstable_rate": unstable_rate,
			"fast_count": fast_count,
			"late_count": late_count,
			"end_status": end_status,
		}

	def process_input(self, events):
		for event in events:
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					self._go_to_song_select()
					continue
				if event.key == pygame.K_r and not self._is_loaded_from_json_record:
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

				if (not self._is_loaded_from_json_record) and self._retry_button_rect.collidepoint(event.pos):
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

	def _render_grade_surface(self, grade_text: str, fallback_color):
		if grade_text not in {"SSS", "SSS+"}:
			return self._grade_font.render(grade_text, True, fallback_color)

		# Keep rainbow color stable for 500 ms windows to avoid rapid flicker.
		color_bucket = pygame.time.get_ticks() // 500
		rng = random.Random((int(color_bucket) * 1009) + len(grade_text))

		glyph_surfaces = []
		total_width = 0
		max_height = 0
		for character in grade_text:
			random_color = (
				rng.randint(120, 255),
				rng.randint(120, 255),
				rng.randint(120, 255),
			)
			glyph = self._grade_font.render(character, True, random_color)
			glyph_surfaces.append(glyph)
			total_width += glyph.get_width()
			max_height = max(max_height, glyph.get_height())

		surface = pygame.Surface((max(1, total_width), max(1, max_height)), pygame.SRCALPHA)
		x_cursor = 0
		for glyph in glyph_surfaces:
			surface.blit(glyph, (x_cursor, 0))
			x_cursor += glyph.get_width()

		return surface

	def _draw_tabs(self, screen, panel: pygame.Rect):
		tab_height = 38
		tab_y = panel.y + 78
		tab_gap = 8
		tab_left = panel.x + 24
		available_width = max(160, panel.width - (tab_left * 2))
		tab_width = max(110, (available_width - (tab_gap * (len(self._tabs) - 1))) // len(self._tabs))

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
		end_status = str(metrics.get("end_status", "NOT CLEAR"))
		end_status_color = self.END_STATUS_COLORS.get(end_status, self._text_color)

		top_gap = 16
		left_card_w = int(content_rect.width * 0.42)
		top_remaining_w = content_rect.width - left_card_w - (top_gap * 2)
		right_card_w = max(180, top_remaining_w // 2)
		status_card_w = max(180, top_remaining_w - right_card_w)

		left_card = pygame.Rect(content_rect.x, content_rect.y, left_card_w, 188)
		right_card = pygame.Rect(left_card.right + top_gap, content_rect.y, right_card_w, 188)
		status_card = pygame.Rect(right_card.right + top_gap, content_rect.y, status_card_w, 188)
		lower_y = left_card.bottom + 16
		lower_h = content_rect.height - left_card.height - 16
		lower_gap = 16
		judgement_w = int(content_rect.width * 0.46)
		judgement_card = pygame.Rect(content_rect.x, lower_y, judgement_w, lower_h)
		others_card = pygame.Rect(
			judgement_card.right + lower_gap,
			lower_y,
			content_rect.width - judgement_card.width - lower_gap,
			lower_h,
		)

		for card in (left_card, right_card, status_card, judgement_card, others_card):
			pygame.draw.rect(screen, (31, 38, 54), card, border_radius=12)
			pygame.draw.rect(screen, (72, 85, 113), card, width=2, border_radius=12)

		score_title = self._heading_font.render("Overall Score", True, self._subtle_text_color)
		score_value = self._grade_font.render(f"{metrics['overall_score']:.4f}%", True, grade_color)
		screen.blit(score_title, (left_card.x + 16, left_card.y + 16))
		screen.blit(score_value, (left_card.x + 16, left_card.y + 52))

		grade_title = self._heading_font.render("Grade", True, self._subtle_text_color)
		grade_text = str(metrics["grade"])
		grade_value = self._render_grade_surface(grade_text, grade_color)
		combo_line = self._body_font.render(
			f"Combo {metrics['highest_combo']} / {metrics['max_combo']} ({metrics['combo_rate']:.1f}%)",
			True,
			self._text_color,
		)
		screen.blit(grade_title, (right_card.x + 16, right_card.y + 16))
		screen.blit(grade_value, (right_card.x + 16, right_card.y + 40))

		status_title = self._heading_font.render("End Status", True, self._subtle_text_color)
		status_max_width = max(1, status_card.width - 32)
		status_max_height = max(1, status_card.height - 88)
		status_font_size = 52
		status_font = self._end_status_font
		status_value = status_font.render(end_status, True, end_status_color)
		while (
			(status_value.get_width() > status_max_width or status_value.get_height() > status_max_height)
			and status_font_size > 24
		):
			status_font_size -= 2
			status_font = self._create_font(status_font_size, bold=True)
			status_value = status_font.render(end_status, True, end_status_color)
		screen.blit(status_title, (status_card.x + 16, status_card.y + 16))
		screen.blit(status_value, (status_card.x + 16, status_card.y + 54))

		screen.blit(combo_line, (right_card.x + 16, right_card.y + 136))

		breakdown_title = self._heading_font.render("Judgement Breakdown", True, self._subtle_text_color)
		screen.blit(breakdown_title, (judgement_card.x + 16, judgement_card.y + 14))

		row_y = judgement_card.y + 52
		for key in self.JUDGEMENT_KEYS:
			count_value = metrics["judgement_count"].get(key, 0)
			label = self._body_font.render(f"{key}", True, self.JUDGEMENT_COLORS.get(key, self._text_color))
			value = self._body_font.render(str(count_value), True, self._text_color)
			screen.blit(label, (judgement_card.x + 16, row_y))
			screen.blit(value, value.get_rect(topright=(judgement_card.x + 210, row_y)))
			row_y += 34

		others_title = self._heading_font.render("Others", True, self._subtle_text_color)
		screen.blit(others_title, (others_card.x + 16, others_card.y + 14))

		other_lines = [
			f"Clear Rate: {metrics['clear_rate']:.2f}%",
			f"Mean Offset: {metrics['mean_offset']:+.1f} ms",
			f"Unstable Rate: {metrics['unstable_rate']:.1f} ms",
			f"Fast / Late: {metrics['fast_count']} / {metrics['late_count']}",
			f"Play Number: {self._serialized.get('play_number', 1)}",
		]
		other_y = others_card.y + 52
		for line in other_lines:
			text = self._body_font.render(line, True, self._text_color)
			screen.blit(text, (others_card.x + 16, other_y))
			other_y += 34

	def _draw_placeholder_tab(self, screen, panel: pygame.Rect):
		content_rect = pygame.Rect(panel.x + 24, panel.y + 132, panel.width - 48, panel.height - 240)
		pygame.draw.rect(screen, (31, 38, 54), content_rect, border_radius=12)
		pygame.draw.rect(screen, (72, 85, 113), content_rect, width=2, border_radius=12)
		label = self._heading_font.render("Placeholder tab for future metrics", True, self._subtle_text_color)
		hint = self._body_font.render("Use LEFT/RIGHT or click tabs to switch views.", True, self._text_color)
		screen.blit(label, label.get_rect(center=(content_rect.centerx, content_rect.centery - 16)))
		screen.blit(hint, hint.get_rect(center=(content_rect.centerx, content_rect.centery + 20)))

	def _movement_samples(self):
		samples = []
		for entry in self._serialized.get("recorded_player_x", []):
			try:
				timestamp_ms = float(entry.get("timestamp_ms", 0))
				x_position = float(entry.get("x_position", 0.0))
			except (TypeError, ValueError, AttributeError):
				continue
			samples.append((timestamp_ms, x_position))

		if not samples:
			return []

		samples.sort(key=lambda item: item[0])
		start_ms = samples[0][0]
		return [((timestamp_ms - start_ms) / 1000.0, x_position) for timestamp_ms, x_position in samples]

	def _build_movement_line_surface(self, width: int, height: int):
		samples = self._movement_samples()
		cache_key = (width, height, tuple(samples))
		if cache_key == self._movement_line_cache_key and self._movement_line_surface is not None:
			return self._movement_line_surface

		figure = Figure(figsize=(max(1, width) / 100.0, max(1, height) / 100.0), dpi=100)
		figure.patch.set_facecolor((1.0, 1.0, 1.0))
		axis = figure.add_subplot(111)
		axis.set_facecolor((1.0, 1.0, 1.0))

		if samples:
			times_sec = [sample[0] for sample in samples]
			x_positions = [sample[1] for sample in samples]
			axis.plot(times_sec, x_positions, color="#3b82f6", linewidth=2.2)
			x_max = max(times_sec) if times_sec else 1.0
			axis.set_xlim(0, max(1.0, x_max))

			y_limit = max(1.0, max(abs(value) for value in x_positions))
			axis.set_ylim(-y_limit, y_limit)

		axis.set_title("Player Movement Over Time", color="#1f2937", fontsize=14)
		axis.set_xlabel("Time (s)", color="#1f2937")
		axis.set_ylabel("X Position", color="#1f2937")
		axis.tick_params(colors="#1f2937")
		axis.grid(color="#d1d5db", alpha=0.55, linewidth=0.7)
		for spine in axis.spines.values():
			spine.set_color("#6b7280")

		canvas = FigureCanvasAgg(figure)
		canvas.draw()
		renderer = canvas.get_renderer()
		raw_data = renderer.buffer_rgba()
		line_surface = pygame.image.frombuffer(raw_data, (width, height), "RGBA").convert_alpha()

		self._movement_line_cache_key = cache_key
		self._movement_line_surface = line_surface
		return line_surface

	def _combo_samples(self):
		samples = []
		for entry in self._serialized.get("recorded_note_hit", []):
			try:
				note_time_ms = float(entry.get("note_time", 0))
				combo_value = int(entry.get("current_combo", 0))
			except (TypeError, ValueError, AttributeError):
				continue
			samples.append((note_time_ms, max(0, combo_value)))

		if not samples:
			return []

		samples.sort(key=lambda item: item[0])
		start_ms = samples[0][0]
		return [((note_time_ms - start_ms) / 1000.0, combo_value) for note_time_ms, combo_value in samples]

	def _build_combo_line_surface(self, width: int, height: int):
		samples = self._combo_samples()
		cache_key = (width, height, tuple(samples))
		if cache_key == self._combo_line_cache_key and self._combo_line_surface is not None:
			return self._combo_line_surface

		figure = Figure(figsize=(max(1, width) / 100.0, max(1, height) / 100.0), dpi=100)
		figure.patch.set_facecolor((1.0, 1.0, 1.0))
		axis = figure.add_subplot(111)
		axis.set_facecolor((1.0, 1.0, 1.0))

		if samples:
			times_sec = [sample[0] for sample in samples]
			combos = [sample[1] for sample in samples]
			axis.step(times_sec, combos, where="post", color="#16a34a", linewidth=2.2)
			x_max = max(times_sec) if times_sec else 1.0
			y_max = max(combos) if combos else 1
			axis.set_xlim(0, max(1.0, x_max))
			axis.set_ylim(0, max(1, y_max + 1))

		axis.set_title("Combo Over Time", color="#1f2937", fontsize=14)
		axis.set_xlabel("Time (s)", color="#1f2937")
		axis.set_ylabel("Current Combo", color="#1f2937")
		axis.tick_params(colors="#1f2937")
		axis.grid(color="#d1d5db", alpha=0.55, linewidth=0.7)
		for spine in axis.spines.values():
			spine.set_color("#6b7280")

		canvas = FigureCanvasAgg(figure)
		canvas.draw()
		renderer = canvas.get_renderer()
		raw_data = renderer.buffer_rgba()
		combo_surface = pygame.image.frombuffer(raw_data, (width, height), "RGBA").convert_alpha()

		self._combo_line_cache_key = cache_key
		self._combo_line_surface = combo_surface
		return combo_surface

	@staticmethod
	def _rgb_to_hex(color):
		return "#{:02x}{:02x}{:02x}".format(int(color[0]), int(color[1]), int(color[2]))

	def _notes_stacked_rows(self):
		note_hits = self._serialized.get("recorded_note_hit", [])
		rows = {}

		for entry in note_hits:
			note_type = self._safe_int(entry.get("note_type"), -1)
			if note_type < 0:
				continue

			judgement_name = self._normalize_judgement_name(entry.get("judgement_level", "MISS"))
			if note_type not in rows:
				rows[note_type] = {key: 0 for key in self.JUDGEMENT_KEYS}
			rows[note_type][judgement_name] = rows[note_type].get(judgement_name, 0) + 1

		if not rows:
			return []

		ordered_types = sorted(rows.keys())
		result_rows = []
		for note_type in ordered_types:
			result_rows.append(
				{
					"note_type": note_type,
					"name": self.NOTE_TYPE_NAMES.get(note_type, f"Type {note_type}"),
					"counts": rows[note_type],
				}
			)
		return result_rows

	def _build_notes_chart_surface(self, width: int, height: int):
		rows = self._notes_stacked_rows()
		serialized_counts = tuple(
			(row["note_type"], tuple(row["counts"].get(key, 0) for key in self.JUDGEMENT_KEYS)) for row in rows
		)
		cache_key = (width, height, serialized_counts)
		if cache_key == self._notes_chart_cache_key and self._notes_chart_surface is not None:
			return self._notes_chart_surface

		figure = Figure(figsize=(max(1, width) / 100.0, max(1, height) / 100.0), dpi=100)
		figure.patch.set_facecolor((1.0, 1.0, 1.0))
		axis = figure.add_subplot(111)
		axis.set_facecolor((1.0, 1.0, 1.0))

		if rows:
			names = [row["name"] for row in rows]
			x_positions = list(range(len(rows)))
			bottom_values = [0 for _ in rows]

			for judgement_key in self.JUDGEMENT_KEYS:
				values = [row["counts"].get(judgement_key, 0) for row in rows]
				if not any(values):
					continue
				axis.bar(
					x_positions,
					values,
					bottom=bottom_values,
					label=judgement_key,
					color=self._rgb_to_hex(self.JUDGEMENT_COLORS.get(judgement_key, self._text_color)),
					edgecolor="#1f2937",
					linewidth=0.6,
				)
				bottom_values = [bottom_values[i] + values[i] for i in range(len(values))]

			axis.set_xticks(x_positions)
			axis.set_xticklabels(names, rotation=12, ha="right")
			axis.legend(loc="upper right", fontsize=9)

		axis.set_title("Judgement Distribution by Note Type", color="#1f2937", fontsize=14)
		axis.set_xlabel("Note Type", color="#1f2937")
		axis.set_ylabel("Count", color="#1f2937")
		axis.tick_params(colors="#1f2937")
		axis.grid(axis="y", color="#d1d5db", alpha=0.55, linewidth=0.7)
		for spine in axis.spines.values():
			spine.set_color("#6b7280")

		canvas = FigureCanvasAgg(figure)
		canvas.draw()
		renderer = canvas.get_renderer()
		raw_data = renderer.buffer_rgba()
		notes_surface = pygame.image.frombuffer(raw_data, (width, height), "RGBA").convert_alpha()

		self._notes_chart_cache_key = cache_key
		self._notes_chart_surface = notes_surface
		return notes_surface

	def _pressed_side_counts(self):
		counts = {
			-1: 0,
			0: 0,
			1: 0,
		}

		for entry in self._serialized.get("recorded_note_hit", []):
			side = self._safe_int(entry.get("pressed_side"), -1)
			if side not in counts:
				return None
			counts[side] += 1

		return counts

	def _build_side_chart_surface(self, width: int, height: int):
		side_counts = self._pressed_side_counts()
		if side_counts is None:
			return None

		cache_key = (width, height, side_counts[-1], side_counts[0], side_counts[1])
		if cache_key == self._side_chart_cache_key and self._side_chart_surface is not None:
			return self._side_chart_surface

		figure = Figure(figsize=(max(1, width) / 100.0, max(1, height) / 100.0), dpi=100)
		figure.patch.set_facecolor((1.0, 1.0, 1.0))
		axis = figure.add_subplot(111)
		axis.set_facecolor((1.0, 1.0, 1.0))

		labels = ["Left", "Right", "None"]
		values = [side_counts[0], side_counts[1], side_counts[-1]]
		colors = ["#60a5fa", "#f472b6", "#9ca3af"]

		non_zero_labels = []
		non_zero_values = []
		non_zero_colors = []
		for label, value, color in zip(labels, values, colors):
			if int(value) > 0:
				non_zero_labels.append(label)
				non_zero_values.append(int(value))
				non_zero_colors.append(color)

		if non_zero_values:
			axis.pie(
				non_zero_values,
				labels=non_zero_labels,
				colors=non_zero_colors,
				autopct="%1.1f%%",
				startangle=90,
				textprops={"color": "#1f2937", "fontsize": 11},
			)
			axis.axis("equal")

		axis.set_title("Pressed Side Distribution", color="#1f2937", fontsize=14)

		canvas = FigureCanvasAgg(figure)
		canvas.draw()
		renderer = canvas.get_renderer()
		raw_data = renderer.buffer_rgba()
		side_surface = pygame.image.frombuffer(raw_data, (width, height), "RGBA").convert_alpha()

		self._side_chart_cache_key = cache_key
		self._side_chart_surface = side_surface
		return side_surface

	def _timing_hit_errors(self):
		errors = []
		for entry in self._serialized.get("recorded_note_hit", []):
			hit_error = self._safe_int(entry.get("hit_error"), 0)
			if abs(hit_error) < 500:
				errors.append(hit_error)
		return errors

	def _build_timing_hist_surface(self, width: int, height: int):
		hit_errors = self._timing_hit_errors()
		cache_key = (width, height, tuple(hit_errors))
		if cache_key == self._timing_hist_cache_key and self._timing_hist_surface is not None:
			return self._timing_hist_surface

		figure = Figure(figsize=(max(1, width) / 100.0, max(1, height) / 100.0), dpi=100)
		figure.patch.set_facecolor((1.0, 1.0, 1.0))
		axis = figure.add_subplot(111)
		axis.set_facecolor((1.0, 1.0, 1.0))

		if hit_errors:
			range_limit = max(1, max(abs(error) for error in hit_errors))
			axis.hist(
				hit_errors,
				bins=40,
				range=(-range_limit, range_limit),
				color="#6bb3ff",
				edgecolor="#263247",
				alpha=0.95,
			)
			axis.set_xlim(-range_limit, range_limit)
		axis.set_title("Hit Error Histogram", color="#1f2937", fontsize=14)
		axis.set_xlabel("Hit Error (ms)", color="#1f2937")
		axis.set_ylabel("Count", color="#1f2937")
		axis.tick_params(colors="#1f2937")
		axis.grid(color="#d1d5db", alpha=0.55, linewidth=0.7)
		for spine in axis.spines.values():
			spine.set_color("#6b7280")

		canvas = FigureCanvasAgg(figure)
		canvas.draw()
		renderer = canvas.get_renderer()
		raw_data = renderer.buffer_rgba()
		hist_surface = pygame.image.frombuffer(raw_data, (width, height), "RGBA").convert_alpha()

		self._timing_hist_cache_key = cache_key
		self._timing_hist_surface = hist_surface
		return hist_surface

	def _draw_timing_tab(self, screen, panel: pygame.Rect):
		content_rect = pygame.Rect(panel.x + 24, panel.y + 132, panel.width - 48, panel.height - 240)
		pygame.draw.rect(screen, (31, 38, 54), content_rect, border_radius=12)
		pygame.draw.rect(screen, (72, 85, 113), content_rect, width=2, border_radius=12)

		hit_errors = self._timing_hit_errors()
		if not hit_errors:
			label = self._heading_font.render("No hit timing data available", True, self._subtle_text_color)
			hint = self._body_font.render("Play a chart to populate timing distribution.", True, self._text_color)
			screen.blit(label, label.get_rect(center=(content_rect.centerx, content_rect.centery - 14)))
			screen.blit(hint, hint.get_rect(center=(content_rect.centerx, content_rect.centery + 18)))
			return

		hist_margin = 16
		hist_rect = pygame.Rect(
			content_rect.x + hist_margin,
			content_rect.y + hist_margin,
			content_rect.width - hist_margin * 2,
			content_rect.height - hist_margin * 2,
		)
		hist_surface = self._build_timing_hist_surface(hist_rect.width, hist_rect.height)
		screen.blit(hist_surface, hist_rect.topleft)

	def _draw_movement_tab(self, screen, panel: pygame.Rect):
		content_rect = pygame.Rect(panel.x + 24, panel.y + 132, panel.width - 48, panel.height - 240)
		pygame.draw.rect(screen, (31, 38, 54), content_rect, border_radius=12)
		pygame.draw.rect(screen, (72, 85, 113), content_rect, width=2, border_radius=12)

		samples = self._movement_samples()
		if not samples:
			label = self._heading_font.render("No movement data available", True, self._subtle_text_color)
			hint = self._body_font.render("Play a chart to populate movement samples.", True, self._text_color)
			screen.blit(label, label.get_rect(center=(content_rect.centerx, content_rect.centery - 14)))
			screen.blit(hint, hint.get_rect(center=(content_rect.centerx, content_rect.centery + 18)))
			return

		line_margin = 16
		line_rect = pygame.Rect(
			content_rect.x + line_margin,
			content_rect.y + line_margin,
			content_rect.width - line_margin * 2,
			content_rect.height - line_margin * 2,
		)
		line_surface = self._build_movement_line_surface(line_rect.width, line_rect.height)
		screen.blit(line_surface, line_rect.topleft)

	def _draw_combo_tab(self, screen, panel: pygame.Rect):
		content_rect = pygame.Rect(panel.x + 24, panel.y + 132, panel.width - 48, panel.height - 240)
		pygame.draw.rect(screen, (31, 38, 54), content_rect, border_radius=12)
		pygame.draw.rect(screen, (72, 85, 113), content_rect, width=2, border_radius=12)

		samples = self._combo_samples()
		if not samples:
			label = self._heading_font.render("No combo data available", True, self._subtle_text_color)
			hint = self._body_font.render("Play a chart to populate combo history.", True, self._text_color)
			screen.blit(label, label.get_rect(center=(content_rect.centerx, content_rect.centery - 14)))
			screen.blit(hint, hint.get_rect(center=(content_rect.centerx, content_rect.centery + 18)))
			return

		chart_margin = 16
		chart_rect = pygame.Rect(
			content_rect.x + chart_margin,
			content_rect.y + chart_margin,
			content_rect.width - chart_margin * 2,
			content_rect.height - chart_margin * 2,
		)
		combo_surface = self._build_combo_line_surface(chart_rect.width, chart_rect.height)
		screen.blit(combo_surface, chart_rect.topleft)

	def _draw_notes_tab(self, screen, panel: pygame.Rect):
		content_rect = pygame.Rect(panel.x + 24, panel.y + 132, panel.width - 48, panel.height - 240)
		pygame.draw.rect(screen, (31, 38, 54), content_rect, border_radius=12)
		pygame.draw.rect(screen, (72, 85, 113), content_rect, width=2, border_radius=12)

		rows = self._notes_stacked_rows()
		if not rows:
			label = self._heading_font.render("No note judgement data available", True, self._subtle_text_color)
			hint = self._body_font.render("Play a chart to populate note judgement history.", True, self._text_color)
			screen.blit(label, label.get_rect(center=(content_rect.centerx, content_rect.centery - 14)))
			screen.blit(hint, hint.get_rect(center=(content_rect.centerx, content_rect.centery + 18)))
			return

		chart_margin = 16
		chart_rect = pygame.Rect(
			content_rect.x + chart_margin,
			content_rect.y + chart_margin,
			content_rect.width - chart_margin * 2,
			content_rect.height - chart_margin * 2,
		)
		notes_surface = self._build_notes_chart_surface(chart_rect.width, chart_rect.height)
		screen.blit(notes_surface, chart_rect.topleft)

	def _draw_side_tab(self, screen, panel: pygame.Rect):
		content_rect = pygame.Rect(panel.x + 24, panel.y + 132, panel.width - 48, panel.height - 240)
		pygame.draw.rect(screen, (31, 38, 54), content_rect, border_radius=12)
		pygame.draw.rect(screen, (72, 85, 113), content_rect, width=2, border_radius=12)

		side_counts = self._pressed_side_counts()
		if side_counts is None:
			label = self._heading_font.render("Invalid pressed_side value detected", True, self._subtle_text_color)
			hint = self._body_font.render("Skipping side chart because record data is invalid.", True, self._text_color)
			screen.blit(label, label.get_rect(center=(content_rect.centerx, content_rect.centery - 14)))
			screen.blit(hint, hint.get_rect(center=(content_rect.centerx, content_rect.centery + 18)))
			return

		if (side_counts[-1] + side_counts[0] + side_counts[1]) <= 0:
			label = self._heading_font.render("No side input data available", True, self._subtle_text_color)
			hint = self._body_font.render("Play a chart to populate pressed-side history.", True, self._text_color)
			screen.blit(label, label.get_rect(center=(content_rect.centerx, content_rect.centery - 14)))
			screen.blit(hint, hint.get_rect(center=(content_rect.centerx, content_rect.centery + 18)))
			return

		chart_margin = 16
		chart_rect = pygame.Rect(
			content_rect.x + chart_margin,
			content_rect.y + chart_margin,
			content_rect.width - chart_margin * 2,
			content_rect.height - chart_margin * 2,
		)
		side_surface = self._build_side_chart_surface(chart_rect.width, chart_rect.height)
		if side_surface is not None:
			screen.blit(side_surface, chart_rect.topleft)

	def render(self, screen):
		screen.fill(self._background_color)

		width, height = screen.get_size()
		panel = pygame.Rect(0, 0, width, height)

		title = self._title_font.render("Result Dashboard", True, self._text_color)
		screen.blit(title, title.get_rect(midtop=(panel.centerx, panel.y + 18)))

		song_title = self._display_song_title()
		chart_name = self._display_chart_name()
		subtitle = self._small_font.render(f"{song_title}  |  {chart_name}", True, self._subtle_text_color)
		screen.blit(subtitle, subtitle.get_rect(midtop=(panel.centerx, panel.y + 58)))

		self._draw_tabs(screen, panel)
		metrics = self._extract_metrics()

		if self._active_tab_index == 0:
			self._draw_overview_tab(screen, panel, metrics)
		elif self._active_tab_index == 1:
			self._draw_timing_tab(screen, panel)
		elif self._active_tab_index == 2:
			self._draw_movement_tab(screen, panel)
		elif self._active_tab_index == 3:
			self._draw_combo_tab(screen, panel)
		elif self._active_tab_index == 4:
			self._draw_notes_tab(screen, panel)
		elif self._active_tab_index == 5:
			self._draw_side_tab(screen, panel)
		else:
			self._draw_placeholder_tab(screen, panel)

		saved_name = self._result_file_path.name if self._result_file_path is not None else "Loaded from history"
		footnote = self._small_font.render(f"Saved: {saved_name}", True, self._subtle_text_color)
		screen.blit(footnote, (24, panel.bottom - 84))

		button_width = 220
		button_height = 56
		button_gap = 24
		button_y = panel.bottom - button_height - 20

		if self._is_loaded_from_json_record:
			self._retry_button_rect = pygame.Rect(0, 0, 0, 0)
			self._back_button_rect = pygame.Rect(
				panel.centerx - (button_width // 2),
				button_y,
				button_width,
				button_height,
			)
		else:
			buttons_total_width = (button_width * 2) + button_gap
			button_start_x = panel.centerx - (buttons_total_width // 2)
			self._retry_button_rect = pygame.Rect(button_start_x, button_y, button_width, button_height)
			self._back_button_rect = pygame.Rect(
				button_start_x + button_width + button_gap,
				button_y,
				button_width,
				button_height,
			)

		mouse_pos = pygame.mouse.get_pos()
		if not self._is_loaded_from_json_record:
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

