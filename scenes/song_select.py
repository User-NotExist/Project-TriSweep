import pygame
import math
import json

from pathlib import Path
from components.song import Song
from config import Config
from components.scene_base import SceneBase

EASY_COLOR = (52, 235, 58)
ADVANCED_COLOR = (250, 165, 37)
EXPERT_COLOR = (250, 41, 37)
MASTER_COLOR = (237, 71, 255)
FALLBACK_DIFF_COLOR = (194, 200, 214)

SONG_ASSET_PATH = Path("./data/songs/")

DIFFICULTY_COLORS = {
    "easy": EASY_COLOR,
    "advanced": ADVANCED_COLOR,
    "expert": EXPERT_COLOR,
    "master": MASTER_COLOR,
}


class SongSelect(SceneBase):
    def __init__(self):
        super().__init__()

        self.background_color = (18, 22, 31)
        self.sidebar_color = (26, 31, 43)
        self.card_color = (39, 47, 64)
        self.card_selected_color = (71, 128, 245)
        self.text_color = (240, 244, 252)
        self.subtle_text_color = (167, 176, 197)

        self.margin = 20
        self.columns = 1
        self.sidebar_width = 300
        self.card_size = (180, 220)
        self.card_gap = 16
        self.thumb_size = (160, 160)
        self.min_card_width = 180
        self.max_card_width = 220
        self.max_columns = 6
        self.grid_content_top = self.margin + 52

        self.sort_key_options = [
            ("name", "Name"),
            ("artist", "Artist"),
            ("bpm", "BPM"),
            ("duration", "Duration"),
        ]
        self.sort_order_options = [
            ("asc", "Ascending"),
            ("desc", "Descending"),
        ]
        self.sort_key = "name"
        self.sort_order = "asc"
        self.sort_key_open = False
        self.sort_order_open = False
        self.sort_key_rect = pygame.Rect(0, 0, 0, 0)
        self.sort_order_rect = pygame.Rect(0, 0, 0, 0)
        self.sort_key_option_rects = []
        self.sort_order_option_rects = []

        self.selected_index = 0
        self.selected_difficulty_index = 0
        self.scroll_y = 0
        self.max_scroll = 0

        self.title_font = self._create_font(28, bold=True)
        self.song_title_font = self._create_font(18, bold=True)
        self.song_artist_font = self._create_font(14)
        self.small_font = self._create_font(12)
        self.sidebar_title_font = self._create_font(26, bold=True)
        self.sidebar_artist_font = self._create_font(18)
        self.diff_font = self._create_font(16, bold=True)
        self.record_title_font = self._create_font(26, bold=True)
        self.record_header_font = self._create_font(15, bold=True)
        self.record_row_font = self._create_font(14)

        self.marquee_speed_px_per_sec = 45
        self.marquee_gap_px = 60

        self.song_card_rects = []
        self.diff_card_rects = []
        self.start_button_rect = pygame.Rect(0, 0, 0, 0)
        self.layout_size = (0, 0)
        self.grid_area = pygame.Rect(0, 0, 0, 0)
        self.sidebar_area = pygame.Rect(0, 0, 0, 0)

        self._preview_song_index = None
        self._preview_started_ms = 0
        self._preview_start_sec = 0.0
        self._preview_duration_sec = 0.0
        self._preview_loaded_path = None
        self._preview_enabled = True
        self._preview_is_fading_out = False

        self.show_play_records = False
        self._play_record_cache_key = None
        self._selected_play_records = []
        self._record_sort_key = None
        self._record_sort_order = "desc"
        self._record_header_hitboxes = []
        self._record_row_hitboxes = []
        self._record_columns = [
            ("player_name", "Player", 0.38, False),
            ("play_number", "Play", 0.18, True),
            ("total_score", "Total Score", 0.24, True),
            ("highest_combo", "Highest Combo", 0.20, True),
        ]

        self.preview_fade_in_ms = 250
        self.preview_fade_out_ms = 250

        self.songs = []
        self._thumb_cache = {}
        self._large_cache = {}

        self._load_songs()
        if self.songs:
            self._start_selected_preview()

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

    def _draw_looping_text(self, surface, text, font, color, rect):
        text = text or ""
        text_surface = font.render(text, True, color)
        text_w = text_surface.get_width()

        if text_w <= rect.width:
            surface.blit(text_surface, (rect.x, rect.y))
            return

        now_ms = pygame.time.get_ticks()
        offset = int((now_ms / 1000.0) * self.marquee_speed_px_per_sec)
        loop_distance = text_w + self.marquee_gap_px
        scroll_x = offset % loop_distance

        previous_clip = surface.get_clip()
        surface.set_clip(rect)
        draw_x = rect.x - scroll_x
        surface.blit(text_surface, (draw_x, rect.y))
        surface.blit(text_surface, (draw_x + loop_distance, rect.y))
        surface.set_clip(previous_clip)

    @staticmethod
    def _format_level(level):
        return f"{level:g}" if isinstance(level, (int, float)) else str(level)

    @staticmethod
    def _format_level_simple(level):
        if not isinstance(level, (int, float)):
            return SongSelect._format_level(level)

        return f"{math.floor(level)}{'+' if level - math.floor(level) >= 0.5 else ''}"

    @staticmethod
    def _format_bpm(bpm):
        try:
            bpm_value = float(bpm)
        except (TypeError, ValueError):
            return "BPM --"

        if bpm_value <= 0:
            return "BPM --"
        return f"BPM {bpm_value:g}"

    @staticmethod
    def _format_duration(seconds):
        try:
            total_seconds = int(float(seconds))
        except (TypeError, ValueError):
            return "--:--"

        if total_seconds <= 0:
            return "--:--"

        minutes, secs = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02}:{secs:02}"
        return f"{minutes}:{secs:02}"

    def _load_songs(self):
        if not SONG_ASSET_PATH.exists():
            print(f"Warning: Song asset path not found: {SONG_ASSET_PATH}")
            return

        songs_folder = sorted(f for f in SONG_ASSET_PATH.iterdir() if f.is_dir())
        for folder in songs_folder:
            meta_path = folder / "meta.jsonc"
            if not meta_path.exists():
                print(f"Warning: meta.jsonc not found in {folder}, skipping...")
                continue

            song = Song(folder)
            if not song.hidden:
                self.songs.append(song)

        self._apply_sort()

    @staticmethod
    def _safe_int(value, fallback=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _get_selected_song_and_chart(self):
        if not self.songs:
            return None, None

        song = self.songs[max(0, min(self.selected_index, len(self.songs) - 1))]
        charts = song.difficulty
        if not charts:
            return song, None

        chart_index = max(0, min(self.selected_difficulty_index, len(charts) - 1))
        return song, charts[chart_index]

    def _load_selected_play_records(self, force=False):
        song, chart = self._get_selected_song_and_chart()
        cache_key = None if song is None or chart is None else (str(song.folder_path), chart.name)

        if not force and cache_key == self._play_record_cache_key:
            return

        self._play_record_cache_key = cache_key
        self._selected_play_records = []

        if song is None or chart is None:
            return

        record_dir = song.folder_path / chart.name
        if not record_dir.exists() or not record_dir.is_dir():
            return

        try:
            record_files = sorted(record_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        except OSError:
            return

        for record_path in record_files:
            try:
                with open(record_path, "r", encoding="utf-8") as record_file:
                    payload = json.load(record_file)
            except Exception as error:
                print(f"Warning: Failed to read play record '{record_path}': {error}")
                continue

            total_score = payload.get("total_score", payload.get("current_score", 0))
            self._selected_play_records.append(
                {
                    "player_name": str(payload.get("player_name", "UNKNOWN")),
                    "play_number": self._safe_int(payload.get("play_number"), 0),
                    "total_score": self._safe_int(total_score, 0),
                    "highest_combo": self._safe_int(payload.get("highest_combo"), 0),
                    "_record_payload": payload,
                    "_record_path": str(record_path),
                }
            )

        if self._record_sort_key is None:
            self._selected_play_records.sort(
                key=lambda row: (row["play_number"], row["total_score"], row["highest_combo"]),
                reverse=True,
            )
        else:
            self._sort_selected_play_records()

    def _sort_selected_play_records(self):
        if not self._selected_play_records or not self._record_sort_key:
            return

        reverse = self._record_sort_order == "desc"
        if self._record_sort_key == "player_name":
            self._selected_play_records.sort(
                key=lambda row: str(row.get("player_name", "")).casefold(),
                reverse=reverse,
            )
            return

        self._selected_play_records.sort(
            key=lambda row: self._safe_int(row.get(self._record_sort_key), 0),
            reverse=reverse,
        )

    def _handle_record_table_click(self, pos):
        for key, rect in self._record_header_hitboxes:
            if rect.collidepoint(pos):
                if self._record_sort_key == key:
                    self._record_sort_order = "asc" if self._record_sort_order == "desc" else "desc"
                else:
                    self._record_sort_key = key
                    self._record_sort_order = "desc"
                self._sort_selected_play_records()
                return True

        for row_rect, row in self._record_row_hitboxes:
            if row_rect.collidepoint(pos):
                payload = row.get("_record_payload")
                if isinstance(payload, dict):
                    song, chart = self._get_selected_song_and_chart()
                    if song is None or chart is None:
                        return True

                    from scenes.result import Result

                    self.switch_to_scene(
                        Result(
                            None,
                            serialized_record=payload,
                            song=song,
                            chart=chart,
                            result_file_path=row.get("_record_path"),
                        )
                    )
                    return True
        return False

    def _sort_label(self, options, value):
        for option_value, option_label in options:
            if option_value == value:
                return option_label
        return value

    @staticmethod
    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _numeric_sort_value(self, song, key_name):
        meta = song.raw_meta()
        if key_name == "bpm":
            value = self._safe_float(meta.get("bpm"))
        elif key_name == "duration":
            value = self._safe_float(meta.get("length"))
        else:
            return None

        if value is None or value <= 0:
            return None
        return value

    def _apply_sort(self):
        if not self.songs:
            return

        selected_song = self.songs[self.selected_index] if 0 <= self.selected_index < len(self.songs) else None

        if self.sort_key in ("name", "artist"):
            if self.sort_key == "name":
                self.songs.sort(key=lambda song: song.title.casefold(), reverse=self.sort_order == "desc")
            else:
                self.songs.sort(key=lambda song: song.artist.casefold(), reverse=self.sort_order == "desc")
        else:
            if self.sort_order == "desc":
                self.songs.sort(
                    key=lambda song: (
                        self._numeric_sort_value(song, self.sort_key) is None,
                        -self._numeric_sort_value(song, self.sort_key)
                        if self._numeric_sort_value(song, self.sort_key) is not None
                        else 0.0,
                    )
                )
            else:
                self.songs.sort(
                    key=lambda song: (
                        self._numeric_sort_value(song, self.sort_key) is None,
                        self._numeric_sort_value(song, self.sort_key)
                        if self._numeric_sort_value(song, self.sort_key) is not None
                        else 0.0,
                    )
                )

        if selected_song in self.songs:
            self.selected_index = self.songs.index(selected_song)
        else:
            self.selected_index = max(0, min(self.selected_index, len(self.songs) - 1))

        self.selected_difficulty_index = 0
        self._ensure_selection_visible()

    def _set_sort_key(self, key_name):
        if key_name == self.sort_key:
            return
        self.sort_key = key_name
        self._apply_sort()
        self._start_selected_preview()

    def _set_sort_order(self, order_name):
        if order_name == self.sort_order:
            return
        self.sort_order = order_name
        self._apply_sort()
        self._start_selected_preview()

    def _handle_sort_click(self, pos):
        if self.sort_key_rect.collidepoint(pos):
            self.sort_key_open = not self.sort_key_open
            self.sort_order_open = False
            return True

        if self.sort_order_rect.collidepoint(pos):
            self.sort_order_open = not self.sort_order_open
            self.sort_key_open = False
            return True

        if self.sort_key_open:
            for option_index, option_rect in enumerate(self.sort_key_option_rects):
                if option_rect.collidepoint(pos):
                    self._set_sort_key(self.sort_key_options[option_index][0])
                    self.sort_key_open = False
                    return True

        if self.sort_order_open:
            for option_index, option_rect in enumerate(self.sort_order_option_rects):
                if option_rect.collidepoint(pos):
                    self._set_sort_order(self.sort_order_options[option_index][0])
                    self.sort_order_open = False
                    return True

        had_open_dropdown = self.sort_key_open or self.sort_order_open
        self.sort_key_open = False
        self.sort_order_open = False
        return had_open_dropdown

    def _load_image(self, image_path, size):
        cache_key = (str(image_path), size)

        if size == self.thumb_size and cache_key in self._thumb_cache:
            return self._thumb_cache[cache_key]
        if size != self.thumb_size and cache_key in self._large_cache:
            return self._large_cache[cache_key]

        surface = pygame.Surface(size)
        surface.fill((56, 64, 86))
        pygame.draw.rect(surface, (89, 99, 127), surface.get_rect(), width=2)

        try:
            if image_path and Path(image_path).is_file():
                loaded = pygame.image.load(str(image_path)).convert_alpha()
                surface = pygame.transform.smoothscale(loaded, size)
        except Exception as error:
            print(f"Warning: Failed to load jacket image '{image_path}': {error}")

        if size == self.thumb_size:
            self._thumb_cache[cache_key] = surface
        else:
            self._large_cache[cache_key] = surface

        return surface

    def _build_layout(self, width, height):
        self.layout_size = (width, height)

        # Keep sidebar visible, but don't let it consume the full window on narrow sizes.
        min_grid_width = self.margin * 2 + 1
        max_sidebar_width = max(0, width - min_grid_width)
        sidebar_width = min(self.sidebar_width, max_sidebar_width)

        self.sidebar_area = pygame.Rect(width - sidebar_width, 0, sidebar_width, height)
        self.grid_area = pygame.Rect(0, 0, width - sidebar_width, height)

        inner_grid_width = max(1, self.grid_area.width - (self.margin * 2))
        columns_that_fit = (inner_grid_width + self.card_gap) // (self.min_card_width + self.card_gap)
        self.columns = max(1, min(self.max_columns, columns_that_fit))

        available_w = inner_grid_width - (self.card_gap * (self.columns - 1))
        card_w = min(self.max_card_width, max(1, available_w // self.columns))
        card_h = int(card_w * 1.6)
        self.card_size = (card_w, card_h)
        self.thumb_size = (max(1, card_w - 20), max(1, card_w - 20))

        controls_top = self.margin + self.title_font.get_height() + 10
        control_height = 30
        control_gap = 10
        controls_width = max(1, self.grid_area.width - (self.margin * 2))

        if controls_width >= 280:
            order_w = min(160, max(110, controls_width // 3))
            key_w = max(120, controls_width - order_w - control_gap)
            self.sort_key_rect = pygame.Rect(self.margin, controls_top, key_w, control_height)
            self.sort_order_rect = pygame.Rect(self.sort_key_rect.right + control_gap, controls_top, order_w, control_height)
            controls_bottom = self.sort_key_rect.bottom
        else:
            self.sort_key_rect = pygame.Rect(self.margin, controls_top, controls_width, control_height)
            self.sort_order_rect = pygame.Rect(
                self.margin,
                self.sort_key_rect.bottom + control_gap,
                controls_width,
                control_height,
            )
            controls_bottom = self.sort_order_rect.bottom

        self.sort_key_option_rects = [
            pygame.Rect(
                self.sort_key_rect.x,
                self.sort_key_rect.bottom + (option_index * control_height),
                self.sort_key_rect.width,
                control_height,
            )
            for option_index, _ in enumerate(self.sort_key_options)
        ]
        self.sort_order_option_rects = [
            pygame.Rect(
                self.sort_order_rect.x,
                self.sort_order_rect.bottom + (option_index * control_height),
                self.sort_order_rect.width,
                control_height,
            )
            for option_index, _ in enumerate(self.sort_order_options)
        ]

        self.grid_content_top = controls_bottom + 12

        self.song_card_rects = []
        top_y = self.grid_content_top - self.scroll_y
        for i, _song in enumerate(self.songs):
            col = i % self.columns
            row = i // self.columns
            x = self.margin + col * (self.card_size[0] + self.card_gap)
            y = top_y + row * (self.card_size[1] + self.card_gap)
            self.song_card_rects.append(pygame.Rect(x, y, self.card_size[0], self.card_size[1]))

        row_count = (len(self.songs) + self.columns - 1) // self.columns
        content_height = self.grid_content_top + row_count * (self.card_size[1] + self.card_gap)
        self.max_scroll = max(0, content_height - self.grid_area.height + self.margin)
        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))

    def _rebuild_for_scroll(self):
        if self.layout_size != (0, 0):
            self._build_layout(*self.layout_size)

    def _card_at_pos(self, pos):
        if not self.grid_area.collidepoint(pos):
            return None
        for i, rect in enumerate(self.song_card_rects):
            if rect.collidepoint(pos):
                return i
        return None

    def _difficulty_card_at_pos(self, pos):
        for i, rect in enumerate(self.diff_card_rects):
            if rect.collidepoint(pos):
                return i
        return None

    def _ensure_selection_visible(self):
        if not self.songs or not self.song_card_rects:
            return

        selected_rect = self.song_card_rects[self.selected_index]
        top_limit = self.grid_content_top
        bottom_limit = self.grid_area.height - self.margin

        if selected_rect.top < top_limit:
            self.scroll_y = max(0, self.scroll_y - (top_limit - selected_rect.top))
            self._rebuild_for_scroll()
        elif selected_rect.bottom > bottom_limit:
            self.scroll_y = min(self.max_scroll, self.scroll_y + (selected_rect.bottom - bottom_limit))
            self._rebuild_for_scroll()

    def _difficulty_color(self, name):
        return DIFFICULTY_COLORS.get(name.strip().lower(), FALLBACK_DIFF_COLOR)

    def _ensure_mixer_ready(self):
        if pygame.mixer.get_init() is not None:
            return True
        try:
            pygame.mixer.init()
            return True
        except Exception as error:
            print(f"Warning: Audio preview disabled, mixer init failed: {error}")
            self._preview_enabled = False
            return False

    def _stop_preview(self):
        if pygame.mixer.get_init() is not None:
            pygame.mixer.music.stop()
        self._preview_song_index = None
        self._preview_is_fading_out = False

    def _play_preview_for_index(self, song_index, force_reload=False):
        if not self._preview_enabled or not self.songs:
            return
        if song_index < 0 or song_index >= len(self.songs):
            return
        if not self._ensure_mixer_ready():
            return

        song = self.songs[song_index]
        music_path = song.music_path
        if not music_path.is_file():
            print(f"Warning: Music file not found for preview: {music_path}")
            self._stop_preview()
            return

        preview_start = max(0.0, float(song.preview_start))
        preview_duration = max(0.0, float(song.preview_duration))
        if preview_duration <= 0.0:
            preview_duration = 15.0

        try:
            if force_reload or self._preview_loaded_path != music_path:
                pygame.mixer.music.load(str(music_path))
                pygame.mixer.music.set_volume(Config.MUSIC_VOLUME)
                self._preview_loaded_path = music_path

            pygame.mixer.music.play(loops=0, start=preview_start, fade_ms=self.preview_fade_in_ms)
            self._preview_song_index = song_index
            self._preview_started_ms = pygame.time.get_ticks()
            self._preview_start_sec = preview_start
            self._preview_duration_sec = preview_duration
            self._preview_is_fading_out = False
        except Exception as error:
            print(f"Warning: Failed to play preview for '{song.title}': {error}")
            self._stop_preview()

    def _start_selected_preview(self):
        self._play_preview_for_index(self.selected_index, force_reload=True)

    def _set_selected_index(self, new_index):
        if not self.songs:
            return
        clamped = max(0, min(new_index, len(self.songs) - 1))
        if clamped != self.selected_index:
            self.selected_index = clamped
            self.selected_difficulty_index = 0
            self._play_record_cache_key = None
            self._start_selected_preview()

    def _set_selected_difficulty_index(self, new_index):
        if not self.songs:
            return

        selected_song = self.songs[self.selected_index]
        charts = selected_song.difficulty
        if not charts:
            self.selected_difficulty_index = 0
            self._play_record_cache_key = None
            return

        clamped = max(0, min(new_index, len(charts) - 1))
        if clamped != self.selected_difficulty_index:
            self.selected_difficulty_index = clamped
            self._play_record_cache_key = None

    def _start_selected_chart(self):
        if not self.songs:
            return

        selected_song = self.songs[self.selected_index]
        charts = selected_song.difficulty
        if not charts:
            print(f"Start clicked: {selected_song.title} (no chart available)")
            return

        self.selected_difficulty_index = max(0, min(self.selected_difficulty_index, len(charts) - 1))
        chart = charts[self.selected_difficulty_index]
        difficulty_color = self._difficulty_color(chart.name)

        from scenes.loading import Loading

        self.switch_to_scene(Loading(selected_song, chart, difficulty_color))

    def on_scene_exit(self):
        self._stop_preview()

    def process_input(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.show_play_records:
                    if event.button == 1:
                        self._handle_record_table_click(event.pos)
                    continue

                if event.button == 1:
                    if self._handle_sort_click(event.pos):
                        continue

                    if self.start_button_rect.collidepoint(event.pos):
                        self._start_selected_chart()
                        continue

                    picked_diff = self._difficulty_card_at_pos(event.pos)
                    if picked_diff is not None:
                        self._set_selected_difficulty_index(picked_diff)
                        continue

                    picked_song = self._card_at_pos(event.pos)
                    if picked_song is not None:
                        self._set_selected_index(picked_song)

                elif event.button == 4:
                    self.scroll_y = max(0, self.scroll_y - 40)
                    self._rebuild_for_scroll()
                elif event.button == 5:
                    self.scroll_y = min(self.max_scroll, self.scroll_y + 40)
                    self._rebuild_for_scroll()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    self.show_play_records = not self.show_play_records
                    if self.show_play_records:
                        self._load_selected_play_records(force=True)
                    continue

                if self.show_play_records:
                    if event.key == pygame.K_ESCAPE:
                        self.show_play_records = False
                    continue

                if event.key == pygame.K_LEFT and self.songs:
                    self._set_selected_index(self.selected_index - 1)
                elif event.key == pygame.K_RIGHT and self.songs:
                    self._set_selected_index(self.selected_index + 1)
                elif event.key == pygame.K_UP and self.songs:
                    self._set_selected_index(self.selected_index - self.columns)
                elif event.key == pygame.K_DOWN and self.songs:
                    self._set_selected_index(self.selected_index + self.columns)

                self._ensure_selection_visible()

                if event.key == pygame.K_ESCAPE:
                    from scenes.main_menu import MainMenu
                    self.switch_to_scene(MainMenu())
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._start_selected_chart()

    def update(self):
        # Switch happens at end of frame in main loop; avoid preview restart after scene exit.
        if self.next is not self:
            return

        if not self.songs:
            self._stop_preview()
            return

        self.selected_index = max(0, min(self.selected_index, len(self.songs) - 1))
        current_charts = self.songs[self.selected_index].difficulty
        if current_charts:
            new_index = max(0, min(self.selected_difficulty_index, len(current_charts) - 1))
            if new_index != self.selected_difficulty_index:
                self.selected_difficulty_index = new_index
                self._play_record_cache_key = None
        else:
            self.selected_difficulty_index = 0
            self._play_record_cache_key = None

        if self._preview_song_index != self.selected_index:
            self._start_selected_preview()
            return

        if not self._preview_enabled or self._preview_song_index is None:
            return
        if pygame.mixer.get_init() is None:
            return

        elapsed_seconds = (pygame.time.get_ticks() - self._preview_started_ms) / 1000.0
        fade_out_seconds = self.preview_fade_out_ms / 1000.0

        if (
            not self._preview_is_fading_out
            and self._preview_duration_sec > fade_out_seconds
            and elapsed_seconds >= self._preview_duration_sec - fade_out_seconds
        ):
            pygame.mixer.music.fadeout(self.preview_fade_out_ms)
            self._preview_is_fading_out = True

        if elapsed_seconds >= self._preview_duration_sec or not pygame.mixer.music.get_busy():
            self._play_preview_for_index(self.selected_index, force_reload=False)

    def _render_grid(self, screen):
        grid_clip = pygame.Rect(self.grid_area.x, self.grid_area.y, self.grid_area.width, self.grid_area.height)
        screen.set_clip(grid_clip)

        header_surface = self.title_font.render("Song Select", True, self.text_color)
        screen.blit(header_surface, (self.margin, self.margin))

        if not self.songs:
            empty_surface = self.song_title_font.render(
                "No songs found in assets folder.", True, self.subtle_text_color
            )
            screen.blit(empty_surface, (self.margin, self.margin + 64))

        else:
            for i, song in enumerate(self.songs):
                card_rect = self.song_card_rects[i]
                fill = self.card_selected_color if i == self.selected_index else self.card_color
                pygame.draw.rect(screen, fill, card_rect, border_radius=10)

                thumb = self._load_image(song.jacket_path, self.thumb_size)
                thumb_rect = thumb.get_rect(midtop=(card_rect.centerx, card_rect.y + 10))
                screen.blit(thumb, thumb_rect)

                title_rect = pygame.Rect(
                    card_rect.x + 10, thumb_rect.bottom + 8, card_rect.width - 20, self.song_title_font.get_height()
                )
                self._draw_looping_text(screen, song.title, self.song_title_font, self.text_color, title_rect)

                artist_rect = pygame.Rect(
                    card_rect.x + 10, thumb_rect.bottom + 30, card_rect.width - 20, self.song_artist_font.get_height()
                )
                self._draw_looping_text(screen, song.artist, self.song_artist_font, self.subtle_text_color, artist_rect)

                meta = song.raw_meta()
                bpm_text = self._format_bpm(meta.get("bpm"))
                duration_text = self._format_duration(meta.get("length"))
                info_rect = pygame.Rect(
                    card_rect.x + 10,
                    artist_rect.bottom + 4,
                    card_rect.width - 20,
                    self.small_font.get_height(),
                )

                bpm_surface = self.small_font.render(bpm_text, True, self.subtle_text_color)
                duration_surface = self.small_font.render(duration_text, True, self.subtle_text_color)
                screen.blit(bpm_surface, (info_rect.left, info_rect.y))
                screen.blit(duration_surface, duration_surface.get_rect(topright=(info_rect.right, info_rect.y)))

                charts = song.difficulty[:4]
                if charts:
                    badge_count = len(charts)
                    badge_gap = 6
                    badge_w = (card_rect.width - 20 - (badge_gap * (badge_count - 1))) // badge_count
                    badge_h = 22
                    badge_y = max(info_rect.bottom + 8, card_rect.bottom - 32)

                    for diff_i, chart in enumerate(charts):
                        badge_x = card_rect.x + 10 + diff_i * (badge_w + badge_gap)
                        badge_rect = pygame.Rect(badge_x, badge_y, badge_w, badge_h)
                        badge_color = self._difficulty_color(chart.name)

                        pygame.draw.rect(screen, (28, 34, 47), badge_rect, border_radius=6)
                        pygame.draw.rect(screen, badge_color, badge_rect, width=2, border_radius=6)

                        level_surface = self.diff_font.render(self._format_level_simple(chart.level), True, badge_color)
                        level_rect = level_surface.get_rect(center=badge_rect.center)
                        screen.blit(level_surface, level_rect)

        self._draw_dropdown(
            screen,
            self.sort_key_rect,
            f"Sort: {self._sort_label(self.sort_key_options, self.sort_key)}",
            self.sort_key_open,
            self.sort_key_options,
            self.sort_key_option_rects,
            self.sort_key,
        )
        self._draw_dropdown(
            screen,
            self.sort_order_rect,
            f"Order: {self._sort_label(self.sort_order_options, self.sort_order)}",
            self.sort_order_open,
            self.sort_order_options,
            self.sort_order_option_rects,
            self.sort_order,
        )

        screen.set_clip(None)

    def _draw_dropdown(self, screen, rect, label, is_open, options, option_rects, selected_value):
        fill_color = (35, 42, 58)
        border_color = (95, 105, 133)
        pygame.draw.rect(screen, fill_color, rect, border_radius=7)
        pygame.draw.rect(screen, border_color, rect, width=2, border_radius=7)

        label_surface = self.song_artist_font.render(label, True, self.text_color)
        label_rect = label_surface.get_rect(midleft=(rect.x + 10, rect.centery))
        screen.blit(label_surface, label_rect)

        caret_text = "v" if not is_open else "^"
        caret_surface = self.song_artist_font.render(caret_text, True, self.subtle_text_color)
        screen.blit(caret_surface, caret_surface.get_rect(midright=(rect.right - 10, rect.centery)))

        if not is_open:
            return

        for option_index, (option_value, option_label) in enumerate(options):
            option_rect = option_rects[option_index]
            is_selected = option_value == selected_value
            option_fill = (50, 59, 81) if is_selected else (30, 36, 51)
            option_border = (121, 165, 255) if is_selected else (95, 105, 133)

            pygame.draw.rect(screen, option_fill, option_rect, border_radius=7)
            pygame.draw.rect(screen, option_border, option_rect, width=2, border_radius=7)

            option_surface = self.song_artist_font.render(option_label, True, self.text_color)
            option_label_rect = option_surface.get_rect(midleft=(option_rect.x + 10, option_rect.centery))
            screen.blit(option_surface, option_label_rect)

    def _render_sidebar(self, screen, height):
        pygame.draw.rect(screen, self.sidebar_color, self.sidebar_area)
        pygame.draw.line(screen, (73, 86, 114), (self.sidebar_area.left, 0), (self.sidebar_area.left, height), 2)

        if not self.songs:
            return

        selected = self.songs[self.selected_index]
        sidebar_pad = 18

        title_rect = pygame.Rect(
            self.sidebar_area.x + sidebar_pad,
            sidebar_pad,
            self.sidebar_area.width - (sidebar_pad * 2),
            self.sidebar_title_font.get_height(),
        )
        self._draw_looping_text(screen, selected.title, self.sidebar_title_font, self.text_color, title_rect)

        translated_title = selected.translated_title.strip()
        translated_rect = pygame.Rect(
            self.sidebar_area.x + sidebar_pad,
            title_rect.bottom + 6,
            self.sidebar_area.width - (sidebar_pad * 2),
            self.song_artist_font.get_height(),
        )
        if translated_title and translated_title != selected.title:
            self._draw_looping_text(
                screen, translated_title, self.song_artist_font, self.subtle_text_color, translated_rect
            )

        artist_y = translated_rect.bottom + 8 if translated_title and translated_title != selected.title else title_rect.bottom + 8
        artist_rect = pygame.Rect(
            self.sidebar_area.x + sidebar_pad,
            artist_y,
            self.sidebar_area.width - (sidebar_pad * 2),
            self.sidebar_artist_font.get_height(),
        )
        self._draw_looping_text(screen, selected.artist, self.sidebar_artist_font, self.subtle_text_color, artist_rect)

        large_size = (self.sidebar_area.width - sidebar_pad * 2, self.sidebar_area.width - sidebar_pad * 2)
        large_jacket = self._load_image(selected.jacket_path, large_size)
        jacket_rect = large_jacket.get_rect(x=self.sidebar_area.x + sidebar_pad, y=artist_rect.bottom + 16)
        screen.blit(large_jacket, jacket_rect)

        frame_color = (95, 105, 133)
        if selected.difficulty:
            diff_i = max(0, min(self.selected_difficulty_index, len(selected.difficulty) - 1))
            frame_color = self._difficulty_color(selected.difficulty[diff_i].name)

        pygame.draw.rect(screen, frame_color, jacket_rect.inflate(8, 8), width=4, border_radius=10)

        diff_y = jacket_rect.bottom + 20
        diff_header = self.song_title_font.render("Difficulty", True, self.text_color)
        screen.blit(diff_header, (self.sidebar_area.x + sidebar_pad, diff_y))
        diff_y += 30

        self.diff_card_rects = []
        card_height = 54
        card_gap = 8

        for i, chart in enumerate(selected.difficulty):
            color = self._difficulty_color(chart.name)
            rect = pygame.Rect(
                self.sidebar_area.x + sidebar_pad,
                diff_y,
                self.sidebar_area.width - (sidebar_pad * 2),
                card_height,
            )
            self.diff_card_rects.append(rect)

            is_selected = i == self.selected_difficulty_index
            fill_color = (50, 59, 81) if is_selected else (35, 42, 58)
            border_color = color if is_selected else (95, 105, 133)

            pygame.draw.rect(screen, fill_color, rect, border_radius=8)
            pygame.draw.rect(screen, border_color, rect, width=2, border_radius=8)

            diff_name_surface = self.diff_font.render(chart.name, True, color)
            screen.blit(diff_name_surface, diff_name_surface.get_rect(topleft=(rect.x + 10, rect.y + 6)))

            level_surface = self.diff_font.render(self._format_level(chart.level), True, color)
            screen.blit(level_surface, level_surface.get_rect(topright=(rect.right - 10, rect.y + 6)))

            charter_rect = pygame.Rect(rect.x + 10, rect.y + 30, rect.width - 20, self.small_font.get_height())
            self._draw_looping_text(screen, chart.chart_author, self.small_font, self.subtle_text_color, charter_rect)

            diff_y += card_height + card_gap

        start_h = 42
        self.start_button_rect = pygame.Rect(
            self.sidebar_area.x + sidebar_pad,
            self.sidebar_area.bottom - sidebar_pad - start_h,
            self.sidebar_area.width - (sidebar_pad * 2),
            start_h,
        )

        pygame.draw.rect(screen, (40, 155, 85), self.start_button_rect, border_radius=10)
        pygame.draw.rect(screen, (68, 213, 126), self.start_button_rect, width=2, border_radius=10)

        start_label = self.song_title_font.render("Start", True, (255, 255, 255))
        screen.blit(start_label, start_label.get_rect(center=self.start_button_rect.center))

    def render(self, screen):
        width, height = screen.get_size()
        if (width, height) != self.layout_size:
            self._build_layout(width, height)

        screen.fill(self.background_color)
        self._render_grid(screen)
        self._render_sidebar(screen, height)
        self._render_play_record_table(screen)

    def _render_play_record_table(self, screen):
        self._record_header_hitboxes = []
        self._record_row_hitboxes = []
        if not self.show_play_records:
            return

        self._load_selected_play_records()
        if not self._selected_play_records:
            return

        width, height = screen.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((8, 12, 19, 170))
        screen.blit(overlay, (0, 0))

        panel_margin_x = 56
        panel_margin_y = 56
        panel_rect = pygame.Rect(
            panel_margin_x,
            panel_margin_y,
            max(320, width - panel_margin_x * 2),
            max(220, height - panel_margin_y * 2),
        )

        pygame.draw.rect(screen, (24, 30, 43), panel_rect, border_radius=12)
        pygame.draw.rect(screen, (95, 105, 133), panel_rect, width=2, border_radius=12)

        song, chart = self._get_selected_song_and_chart()
        title_text = "Play Records"
        if chart is not None:
            title_text = f"Play Records - {chart.name}"

        title_surface = self.record_title_font.render(title_text, True, self.text_color)
        screen.blit(title_surface, (panel_rect.x + 20, panel_rect.y + 14))

        hint_surface = self.small_font.render("TAB to hide", True, self.subtle_text_color)
        screen.blit(hint_surface, hint_surface.get_rect(topright=(panel_rect.right - 20, panel_rect.y + 22)))

        table_left = panel_rect.x + 20
        table_right = panel_rect.right - 20
        header_y = panel_rect.y + 58
        row_height = 30

        total_width = table_right - table_left
        x_cursor = table_left
        column_rects = []
        for index, (_key, _label, ratio, _align_right) in enumerate(self._record_columns):
            col_w = int(total_width * ratio)
            if index == len(self._record_columns) - 1:
                col_w = table_right - x_cursor
            column_rects.append(pygame.Rect(x_cursor, header_y, col_w, row_height))
            x_cursor += col_w

        for (key, label, _ratio, align_right), col_rect in zip(self._record_columns, column_rects):
            is_sorted = key == self._record_sort_key
            indicator = ""
            if is_sorted:
                indicator = " v" if self._record_sort_order == "desc" else " ^"
            header_surface = self.record_header_font.render(f"{label}{indicator}", True, self.text_color)
            if align_right:
                header_pos = header_surface.get_rect(midright=(col_rect.right - 8, col_rect.centery))
            else:
                header_pos = header_surface.get_rect(midleft=(col_rect.left + 8, col_rect.centery))
            screen.blit(header_surface, header_pos)
            self._record_header_hitboxes.append((key, col_rect.copy()))

        pygame.draw.line(screen, (95, 105, 133), (table_left, header_y + row_height), (table_right, header_y + row_height), 2)

        rows_start_y = header_y + row_height + 6
        available_h = panel_rect.bottom - 20 - rows_start_y
        max_rows = max(1, available_h // row_height)
        visible_rows = self._selected_play_records[:max_rows]
        mouse_pos = pygame.mouse.get_pos()

        for row_index, row in enumerate(visible_rows):
            row_y = rows_start_y + row_index * row_height
            row_rect = pygame.Rect(table_left, row_y, total_width, row_height)
            is_hovered = row_rect.collidepoint(mouse_pos)
            if row_index % 2 == 0:
                pygame.draw.rect(
                    screen,
                    (29, 36, 51),
                    row_rect,
                    border_radius=4,
                )

            if is_hovered:
                pygame.draw.rect(screen, (52, 66, 94), row_rect, border_radius=4)
                pygame.draw.rect(screen, (121, 165, 255), row_rect, width=2, border_radius=4)

            self._record_row_hitboxes.append((row_rect, row))

            for (key, _label, _ratio, align_right), col_rect in zip(self._record_columns, column_rects):
                value_text = str(row.get(key, ""))
                row_surface = self.record_row_font.render(value_text, True, self.text_color)
                if align_right:
                    row_pos = row_surface.get_rect(midright=(col_rect.right - 8, row_y + row_height // 2))
                else:
                    row_pos = row_surface.get_rect(midleft=(col_rect.left + 8, row_y + row_height // 2))
                screen.blit(row_surface, row_pos)
