from pathlib import Path
import random

import pygame

from components.scene_base import SceneBase
from components.song import Song
from config import Config


class MainMenu(SceneBase):
    SONG_ASSET_PATH = Path("./data/songs/")

    def __init__(self, audio_handoff=None):
        super().__init__()
        self.title_text = "Project TriSweep"

        self.background_color = (18, 22, 31)
        self.panel_color = (26, 31, 43)
        self.panel_border_color = (73, 86, 114)
        self.title_color = (240, 244, 252)
        self.subtitle_color = (167, 176, 197)
        self.button_color = (39, 47, 64)
        self.button_hover_color = (71, 128, 245)
        self.button_border_color = (95, 110, 142)
        self.button_text_color = (240, 244, 252)

        self.title_font = self._create_font(56, bold=True)
        self.subtitle_font = self._create_font(20)
        self.button_font = self._create_font(30, bold=True)
        self.music_title_font = self._create_font(15, bold=True)
        self.music_text_font = self._create_font(13)
        self.music_button_font = self._create_font(12, bold=True)

        self.button_size = (320, 62)
        self.button_gap = 14
        self.button_order = [("play", "Play"), ("setting", "Setting"), ("exit", "Exit")]

        self.title_surface = None
        self.subtitle_surface = None
        self.title_rect = pygame.Rect(0, 0, 0, 0)
        self.subtitle_rect = pygame.Rect(0, 0, 0, 0)
        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.button_rects = {
            "play": pygame.Rect(0, 0, 0, 0),
            "setting": pygame.Rect(0, 0, 0, 0),
            "exit": pygame.Rect(0, 0, 0, 0),
        }
        self.hovered_button = None
        self.layout_size = (0, 0)

        self.music_card_rect = pygame.Rect(0, 0, 0, 0)
        self.music_jacket_rect = pygame.Rect(0, 0, 0, 0)
        self.music_title_rect = pygame.Rect(0, 0, 0, 0)
        self.music_artist_rect = pygame.Rect(0, 0, 0, 0)
        self.music_control_rects = {
            "previous": pygame.Rect(0, 0, 0, 0),
            "pause": pygame.Rect(0, 0, 0, 0),
            "next": pygame.Rect(0, 0, 0, 0),
            "random": pygame.Rect(0, 0, 0, 0),
        }
        self.hovered_music_control = None

        self.music_card_color = (26, 31, 43)
        self.music_card_border_color = (73, 86, 114)
        self.music_accent_color = (71, 128, 245)
        self.music_text_color = (240, 244, 252)
        self.music_subtle_text_color = (167, 176, 197)
        self.music_control_color = (39, 47, 64)
        self.music_control_hover_color = (71, 128, 245)
        self.music_control_border_color = (95, 110, 142)

        self._songs = []
        self._song_index_by_path = {}
        self._music_index = -1
        self._music_enabled = True
        self._music_paused = False
        self._pause_started_ms = 0
        self._track_started_ms = pygame.time.get_ticks()
        self._track_duration_sec = 15.0
        self._fade_out_ms = 350
        self._is_fading_out = False
        self._jacket_cache = {}
        self._audio_handoff = audio_handoff or {}

        self._load_songs()
        if not self._apply_audio_handoff():
            self._play_random_song(force_reload=True)

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

    def _build_layout(self, width, height):
        self.layout_size = (width, height)

        panel_width = min(740, max(420, width - 120))
        panel_height = min(540, max(360, height - 120))
        self.panel_rect = pygame.Rect(
            (width - panel_width) // 2,
            (height - panel_height) // 2,
            panel_width,
            panel_height,
        )

        self.title_surface = self.title_font.render(self.title_text, True, self.title_color)
        self.title_rect = self.title_surface.get_rect(centerx=self.panel_rect.centerx, y=self.panel_rect.y + 56)

        self.subtitle_surface = self.subtitle_font.render(
            "3 lane VSRG thing",
            True,
            self.subtitle_color,
        )
        self.subtitle_rect = self.subtitle_surface.get_rect(centerx=self.panel_rect.centerx, y=self.title_rect.bottom + 10)

        button_w, button_h = self.button_size
        total_buttons_height = (len(self.button_order) * button_h) + ((len(self.button_order) - 1) * self.button_gap)
        start_y = self.panel_rect.y + self.panel_rect.height - total_buttons_height - 64

        for index, (key, _) in enumerate(self.button_order):
            y = start_y + index * (button_h + self.button_gap)
            self.button_rects[key] = pygame.Rect((self.panel_rect.centerx - (button_w // 2)), y, button_w, button_h)

        card_width = min(520, max(300, width // 2))
        card_height = 122
        card_x = width - card_width - 20
        card_y = 20
        self.music_card_rect = pygame.Rect(card_x, card_y, card_width, card_height)

        padding = 12
        jacket_size = card_height - (padding * 2)
        self.music_jacket_rect = pygame.Rect(
            card_x + padding,
            card_y + padding,
            jacket_size,
            jacket_size,
        )

        text_left = self.music_jacket_rect.right + 12
        text_width = card_x + card_width - text_left - padding
        self.music_title_rect = pygame.Rect(text_left, card_y + 24, text_width, 20)
        self.music_artist_rect = pygame.Rect(text_left, self.music_title_rect.bottom + 4, text_width, 18)

        controls_top = card_y + card_height - padding - 24
        control_gap = 6
        control_count = len(self.music_control_rects)
        control_area_width = max(180, text_width)
        control_width = max(38, (control_area_width - (control_gap * (control_count - 1))) // control_count)
        control_height = 24
        for index, key in enumerate(("previous", "pause", "next", "random")):
            left = text_left + (index * (control_width + control_gap))
            self.music_control_rects[key] = pygame.Rect(left, controls_top, control_width, control_height)

    def _button_at_position(self, mouse_pos):
        for key, _ in self.button_order:
            if self.button_rects[key].collidepoint(mouse_pos):
                return key
        return None

    def _music_control_at_position(self, mouse_pos):
        if not self.music_card_rect.collidepoint(mouse_pos):
            return None

        for key, rect in self.music_control_rects.items():
            if rect.collidepoint(mouse_pos):
                return key
        return None

    def _ensure_mixer_ready(self):
        if pygame.mixer.get_init() is not None:
            return True

        try:
            pygame.mixer.init()
            return True
        except Exception as error:
            print(f"Warning: Main menu music disabled, mixer init failed: {error}")
            self._music_enabled = False
            return False

    def _sync_music_volume(self):
        if not self._music_enabled or pygame.mixer.get_init() is None:
            return

        try:
            volume = float(getattr(Config, "MUSIC_VOLUME", 1.0))
        except (TypeError, ValueError):
            volume = 1.0

        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))

    def _load_songs(self):
        self._songs = []
        self._song_index_by_path = {}
        if not self.SONG_ASSET_PATH.exists():
            return

        for folder in sorted(path for path in self.SONG_ASSET_PATH.iterdir() if path.is_dir()):
            if not (folder / "meta.jsonc").exists():
                continue
            song = Song(folder)
            if song.hidden:
                continue
            self._song_index_by_path[str(song.folder_path)] = len(self._songs)
            self._songs.append(song)

    def _current_song(self):
        if 0 <= self._music_index < len(self._songs):
            return self._songs[self._music_index]
        return None

    def _load_jacket_image(self, image_path, size):
        cache_key = (str(image_path), size)
        cached = self._jacket_cache.get(cache_key)
        if cached is not None:
            return cached

        surface = pygame.Surface(size)
        surface.fill((56, 64, 86))
        pygame.draw.rect(surface, (89, 99, 127), surface.get_rect(), width=2)

        try:
            if image_path and Path(image_path).is_file():
                loaded = pygame.image.load(str(image_path)).convert_alpha()
                surface = pygame.transform.smoothscale(loaded, size)
        except Exception as error:
            print(f"Warning: Failed to load jacket image '{image_path}': {error}")

        self._jacket_cache[cache_key] = surface
        return surface

    def _play_song_index(self, song_index, force_reload=False):
        if not self._music_enabled or not self._songs:
            return False
        if song_index < 0 or song_index >= len(self._songs):
            return False
        if not self._ensure_mixer_ready():
            return False

        song = self._songs[song_index]
        music_path = song.music_path
        if not music_path.is_file():
            print(f"Warning: Music file not found for main menu playback: {music_path}")
            return False

        start_seconds = 0.0
        song_duration = max(0.0, float(song.length))
        if song_duration <= 0.0:
            # Fallback when metadata length is missing to avoid immediate cycling.
            song_duration = max(0.0, float(song.preview_duration))
        if song_duration <= 0.0:
            song_duration = 180.0

        try:
            pygame.mixer.music.load(str(music_path))
            self._sync_music_volume()
            pygame.mixer.music.play(loops=0, start=start_seconds, fade_ms=220 if force_reload else 0)
        except Exception as error:
            print(f"Warning: Failed to play menu song '{song.title}': {error}")
            return False

        self._music_index = song_index
        self._music_paused = False
        self._pause_started_ms = 0
        self._track_started_ms = pygame.time.get_ticks()
        self._track_duration_sec = song_duration
        self._is_fading_out = False
        return True

    def _play_relative_song(self, offset):
        if not self._songs:
            return

        if self._music_index < 0:
            self._play_song_index(0, force_reload=True)
            return

        new_index = (self._music_index + offset) % len(self._songs)
        self._play_song_index(new_index, force_reload=True)

    def _play_random_song(self, force_reload=False):
        if not self._songs:
            return

        if len(self._songs) == 1:
            self._play_song_index(0, force_reload=force_reload)
            return

        available_indices = [idx for idx in range(len(self._songs)) if idx != self._music_index]
        self._play_song_index(random.choice(available_indices), force_reload=force_reload)

    def _apply_audio_handoff(self):
        if not self._audio_handoff:
            return False
        if not self._ensure_mixer_ready():
            return False

        song_path = str(self._audio_handoff.get("song_folder_path", ""))
        song_index = self._song_index_by_path.get(song_path)
        if song_index is None:
            return False
        if not pygame.mixer.music.get_busy():
            return False

        self._sync_music_volume()

        self._music_index = song_index
        self._music_paused = False
        self._pause_started_ms = 0
        self._track_started_ms = int(self._audio_handoff.get("preview_started_ms", pygame.time.get_ticks()))
        self._track_duration_sec = float(self._audio_handoff.get("preview_duration_sec", 15.0))
        self._fade_out_ms = int(self._audio_handoff.get("preview_fade_out_ms", 350))
        self._is_fading_out = bool(self._audio_handoff.get("preview_is_fading_out", False))
        return True

    def _build_audio_handoff(self):
        song = self._current_song()
        if song is None:
            return None

        return {
            "song_folder_path": str(song.folder_path),
            "preview_started_ms": self._track_started_ms,
            "preview_duration_sec": self._track_duration_sec,
            "preview_fade_out_ms": self._fade_out_ms,
            "preview_is_fading_out": self._is_fading_out,
        }

    def _toggle_pause(self):
        if not self._music_enabled:
            return
        if not self._ensure_mixer_ready():
            return

        if self._music_paused:
            pygame.mixer.music.unpause()
            if self._pause_started_ms > 0:
                self._track_started_ms += pygame.time.get_ticks() - self._pause_started_ms
            self._pause_started_ms = 0
            self._music_paused = False
            return

        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self._pause_started_ms = pygame.time.get_ticks()
            self._music_paused = True
            return

        if self._music_index >= 0:
            self._play_song_index(self._music_index, force_reload=True)
        else:
            self._play_random_song(force_reload=True)

    def _handle_music_control(self, control_key):
        if control_key == "previous":
            self._play_relative_song(-1)
        elif control_key == "pause":
            self._toggle_pause()
        elif control_key == "next":
            self._play_relative_song(1)
        elif control_key == "random":
            self._play_random_song(force_reload=True)

    def _activate_button(self, key):
        if key == "play":
            from scenes.song_select import SongSelect

            self.switch_to_scene(SongSelect())
        elif key == "setting":
            from scenes.setting import Setting

            self.switch_to_scene(Setting(audio_handoff=self._build_audio_handoff()))
        elif key == "exit":
            print("Goodbye!")
            self.switch_to_scene(None)

    def process_input(self, events):
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.hovered_button = self._button_at_position(event.pos)
                self.hovered_music_control = self._music_control_at_position(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                music_control = self._music_control_at_position(event.pos)
                if music_control is not None:
                    self._handle_music_control(music_control)
                    continue

                clicked = self._button_at_position(event.pos)
                if clicked is not None:
                    self._activate_button(clicked)

    def update(self):
        if not self._music_enabled or not self._songs:
            return
        if not self._ensure_mixer_ready():
            return

        self._sync_music_volume()
        if self._music_paused:
            return

        if self._music_index < 0:
            self._play_random_song(force_reload=True)
            return

        elapsed_seconds = max(0.0, (pygame.time.get_ticks() - self._track_started_ms) / 1000.0)
        fade_out_seconds = self._fade_out_ms / 1000.0

        if (
            not self._is_fading_out
            and self._track_duration_sec > fade_out_seconds
            and elapsed_seconds >= self._track_duration_sec - fade_out_seconds
            and pygame.mixer.music.get_busy()
        ):
            pygame.mixer.music.fadeout(self._fade_out_ms)
            self._is_fading_out = True

        if elapsed_seconds >= self._track_duration_sec or not pygame.mixer.music.get_busy():
            self._play_random_song(force_reload=True)

    def render(self, screen):
        width, height = screen.get_size()
        if (width, height) != self.layout_size:
            self._build_layout(width, height)

        self.hovered_button = self._button_at_position(pygame.mouse.get_pos())
        self.hovered_music_control = self._music_control_at_position(pygame.mouse.get_pos())

        screen.fill(self.background_color)

        # Draw soft radial lights so the menu matches the rest of the game's neon-dark style.
        left_glow = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.circle(left_glow, (57, 120, 255, 40), (int(width * 0.2), int(height * 0.18)), 220)
        pygame.draw.circle(left_glow, (133, 85, 255, 28), (int(width * 0.8), int(height * 0.75)), 260)
        screen.blit(left_glow, (0, 0))

        pygame.draw.rect(screen, self.panel_color, self.panel_rect, border_radius=18)
        pygame.draw.rect(screen, self.panel_border_color, self.panel_rect, width=2, border_radius=18)

        accent_bar = pygame.Rect(self.panel_rect.x + 2, self.panel_rect.y + 2, self.panel_rect.width - 4, 7)
        pygame.draw.rect(screen, self.button_hover_color, accent_bar, border_radius=8)

        screen.blit(self.title_surface, self.title_rect)
        screen.blit(self.subtitle_surface, self.subtitle_rect)

        for key, label in self.button_order:
            rect = self.button_rects[key]
            color = self.button_hover_color if key == self.hovered_button else self.button_color

            pygame.draw.rect(screen, color, rect, border_radius=10)
            pygame.draw.rect(screen, self.button_border_color, rect, width=2, border_radius=10)

            text_surface = self.button_font.render(label, True, self.button_text_color)
            text_rect = text_surface.get_rect(center=rect.center)
            screen.blit(text_surface, text_rect)

        pygame.draw.rect(screen, self.music_card_color, self.music_card_rect, border_radius=14)
        pygame.draw.rect(screen, self.music_card_border_color, self.music_card_rect, width=2, border_radius=14)
        accent_rect = pygame.Rect(self.music_card_rect.x + 2, self.music_card_rect.y + 2, self.music_card_rect.width - 4, 6)
        pygame.draw.rect(screen, self.music_accent_color, accent_rect, border_radius=6)

        card_title = self.music_button_font.render("Now Playing", True, self.music_subtle_text_color)
        screen.blit(card_title, (self.music_title_rect.x, self.music_card_rect.y + 10))

        song = self._current_song()
        jacket_path = song.jacket_path if song is not None else None
        jacket_surface = self._load_jacket_image(jacket_path, self.music_jacket_rect.size)
        screen.blit(jacket_surface, self.music_jacket_rect)
        jacket_border_rect = self.music_jacket_rect.inflate(8, 8)
        pygame.draw.rect(screen, self.music_accent_color, jacket_border_rect, width=3, border_radius=10)

        title_text = song.title if song is not None else "No Song"
        artist_text = song.artist if song is not None else "-"

        title_surface = self.music_title_font.render(title_text, True, self.music_text_color)
        artist_surface = self.music_text_font.render(artist_text, True, self.music_subtle_text_color)
        previous_clip = screen.get_clip()
        screen.set_clip(self.music_title_rect)
        screen.blit(title_surface, (self.music_title_rect.x, self.music_title_rect.y))
        screen.set_clip(previous_clip)

        previous_clip = screen.get_clip()
        screen.set_clip(self.music_artist_rect)
        screen.blit(artist_surface, (self.music_artist_rect.x, self.music_artist_rect.y))
        screen.set_clip(previous_clip)

        control_labels = {
            "previous": "<<",
            "pause": ">" if self._music_paused else "||",
            "next": ">>",
            "random": "Rnd",
        }
        for key, rect in self.music_control_rects.items():
            fill_color = self.music_control_hover_color if key == self.hovered_music_control else self.music_control_color
            pygame.draw.rect(screen, fill_color, rect, border_radius=8)
            pygame.draw.rect(screen, self.music_control_border_color, rect, width=2, border_radius=8)

            label_surface = self.music_button_font.render(control_labels[key], True, self.music_text_color)
            screen.blit(label_surface, label_surface.get_rect(center=rect.center))

    def on_scene_exit(self):
        self._audio_handoff = {}

