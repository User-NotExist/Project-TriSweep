from dataclasses import dataclass

import pygame

from config import Config
from scenes.scene_base import SceneBase


@dataclass
class SettingItem:
    key: str
    label: str
    section: str
    type_name: str
    value: object
    control: str
    min_value: float | None = None
    max_value: float | None = None
    step: float = 1.0


class Setting(SceneBase):
    def __init__(self):
        super().__init__()

        self.background_color = (18, 22, 31)
        self.panel_color = (26, 31, 43)
        self.card_color = (39, 47, 64)
        self.card_selected_color = (71, 128, 245)
        self.text_color = (240, 244, 252)
        self.subtle_text_color = (167, 176, 197)
        self.warning_color = (255, 196, 94)
        self.error_color = (245, 120, 120)
        self.success_color = (110, 220, 158)

        self.margin = 20
        self.layout_size = (0, 0)
        self.content_area = pygame.Rect(0, 0, 0, 0)
        self.save_button_rect = pygame.Rect(0, 0, 0, 0)
        self.reset_button_rect = pygame.Rect(0, 0, 0, 0)

        self.title_font = self._create_font(28, bold=True)
        self.section_font = self._create_font(18, bold=True)
        self.key_font = self._create_font(16, bold=True)
        self.value_font = self._create_font(15)
        self.small_font = self._create_font(12)

        self.items = []
        self.item_rects = []
        self.value_rects = {}
        self.slider_rects = {}
        self.selected_index = 0
        self.scroll_y = 0
        self.max_scroll = 0

        self.editing_key = None
        self.edit_buffer = ""
        self.dragging_slider_key = None

        self.pending_values = {}
        self.dirty_keys = set()
        self.caret_visible = True

        self.status_message = "Select a setting, then use the control hint shown in each row."
        self.status_tone = "info"

        Config.load_config()
        self._load_items()

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

    @staticmethod
    def _label_from_key(key):
        return key.replace("_", " ").title()

    @staticmethod
    def _section_for_key(key):
        if key.startswith("PLAYER_"):
            return "Player"
        if key.startswith("WINDOW_") or key in {"FPS", "MUSIC_VOLUME", "SOUND_EFFECT_VOLUME"}:
            return "Program"
        if key.startswith("OFFSET_"):
            return "Offset"
        if key.endswith("_TIMING"):
            return "Timing (ms)"
        if key.endswith("_SCORE"):
            return "Score (%)"
        return "Other"

    def _control_meta(self, key, type_name):
        if type_name == "bool":
            return "toggle", None, None, 1.0

        if key in {"MUSIC_VOLUME", "SOUND_EFFECT_VOLUME"}:
            return "slider", 0.0, 1.0, 0.01

        if type_name == "float":
            return "number", None, None, 0.1

        if type_name == "int":
            if key in {"WINDOW_WIDTH", "WINDOW_HEIGHT"}:
                return "text", 320, 4320, 1
            if key == "FPS":
                return "number", 30, 360, 5
            if key.endswith("_TIMING"):
                return "number", 0, 1000, 1
            if key.endswith("_SCORE"):
                return "number", 0, 100, 1
            return "number", None, None, 1

        return "text", None, None, 1.0

    @staticmethod
    def _control_hint(item):
        if item.control == "text":
            return "Enter to type"
        if item.control in {"number", "slider"}:
            return "Left/Right to adjust"
        if item.control == "toggle":
            return "Space to toggle"
        return ""

    def _set_status_for_selected(self):
        if not self.items or self.editing_key is not None:
            return

        item = self.items[self.selected_index]
        hint = self._control_hint(item)
        self.status_message = f"{item.label}: {hint}. S saves, R reloads, Esc returns."
        self.status_tone = "info"

    def _ordered_keys(self):
        config_keys = Config._config_fields().keys()
        ordered = []

        try:
            config_path = Config._resolve_config_path()
            with open(config_path, "r", encoding="utf-8") as handle:
                data = Config._parse_jsonc_text(handle.read())
            for key in data.keys():
                if key in config_keys:
                    ordered.append(key)
        except Exception:
            ordered = []

        for key in config_keys:
            if key not in ordered:
                ordered.append(key)
        return ordered

    def _load_items(self):
        self.items = []
        self.pending_values = {}
        self.dirty_keys = set()

        type_map = Config.load_config_types()
        for key in self._ordered_keys():
            current_value = getattr(Config, key)
            type_name = type_map.get(key, Config._type_name_for_value(current_value))
            control, min_value, max_value, step = self._control_meta(key, type_name)

            item = SettingItem(
                key=key,
                label=self._label_from_key(key),
                section=self._section_for_key(key),
                type_name=type_name,
                value=current_value,
                control=control,
                min_value=min_value,
                max_value=max_value,
                step=step,
            )
            self.items.append(item)
            self.pending_values[key] = current_value

        self.selected_index = max(0, min(self.selected_index, len(self.items) - 1))
        self._rebuild_layout_for_scroll()
        self._set_status_for_selected()

    def _status_color(self):
        if self.status_tone == "success":
            return self.success_color
        if self.status_tone == "error":
            return self.error_color
        if self.status_tone == "warning":
            return self.warning_color
        return self.subtle_text_color

    def _build_layout(self, width, height):
        self.layout_size = (width, height)
        title_h = self.title_font.get_height()

        self.content_area = pygame.Rect(
            self.margin,
            self.margin + title_h + 18,
            max(1, width - self.margin * 2),
            max(1, height - (self.margin * 2) - title_h - 90),
        )

        footer_y = self.content_area.bottom + 10
        button_w = 120
        button_h = 34
        self.save_button_rect = pygame.Rect(width - self.margin - button_w, footer_y, button_w, button_h)
        self.reset_button_rect = pygame.Rect(self.save_button_rect.left - 12 - button_w, footer_y, button_w, button_h)

        self._compute_scroll_limits()

    def _compute_scroll_limits(self):
        y = 0
        last_section = None
        for item in self.items:
            if item.section != last_section:
                y += 28
                last_section = item.section
            y += 74

        self.max_scroll = max(0, y - self.content_area.height)
        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))

    def _rebuild_layout_for_scroll(self):
        if self.layout_size != (0, 0):
            self._build_layout(*self.layout_size)

    def _value_text(self, item):
        value = self.pending_values.get(item.key)
        if item.control == "slider" and isinstance(value, (int, float)):
            return f"{value:.2f}"
        if item.type_name == "float" and isinstance(value, (int, float)):
            return f"{value:g}"
        return str(value)

    def _set_item_value(self, item, raw_value):
        try:
            coerced = Config._coerce_value(item.key, raw_value, item.type_name)
        except ValueError as error:
            self.status_message = str(error)
            self.status_tone = "error"
            return False

        if item.min_value is not None:
            coerced = max(item.min_value, coerced)
        if item.max_value is not None:
            coerced = min(item.max_value, coerced)

        if item.type_name == "int":
            coerced = int(round(float(coerced)))
        elif item.type_name == "float":
            coerced = float(coerced)

        self.pending_values[item.key] = coerced
        if coerced != item.value:
            self.dirty_keys.add(item.key)
        elif item.key in self.dirty_keys:
            self.dirty_keys.remove(item.key)
        return True

    def _adjust_selected_numeric(self, direction, boost=False):
        if not self.items:
            return
        item = self.items[self.selected_index]
        if item.control not in {"slider", "number"}:
            return

        current = self.pending_values[item.key]
        step = item.step * (10 if boost else 1)
        new_value = float(current) + (step * direction)
        if self._set_item_value(item, new_value):
            self.status_message = f"{item.label}: {self._value_text(item)}"
            self.status_tone = "info"

    def _toggle_selected_bool(self):
        if not self.items:
            return
        item = self.items[self.selected_index]
        if item.control != "toggle":
            return
        self._set_item_value(item, not bool(self.pending_values[item.key]))

    def _begin_text_edit(self, index):
        item = self.items[index]
        if item.control != "text":
            return
        self.selected_index = index
        self.editing_key = item.key
        self.edit_buffer = str(self.pending_values[item.key])
        pygame.key.start_text_input()
        self.caret_visible = True
        self.status_message = f"Editing {item.label}. Enter to apply, Esc to cancel."
        self.status_tone = "warning"

    def _commit_text_edit(self):
        if self.editing_key is None:
            return
        item = next((i for i in self.items if i.key == self.editing_key), None)
        if item is None:
            self.editing_key = None
            return

        if self._set_item_value(item, self.edit_buffer):
            self.status_message = f"Updated {item.label}."
            self.status_tone = "success"
        self.editing_key = None
        self.edit_buffer = ""
        pygame.key.stop_text_input()

    def _cancel_text_edit(self):
        if self.editing_key is None:
            return
        self.editing_key = None
        self.edit_buffer = ""
        pygame.key.stop_text_input()
        self.status_message = "Edit canceled."
        self.status_tone = "info"

    def _ensure_selection_visible(self):
        if not self.item_rects or self.selected_index >= len(self.item_rects):
            return

        selected_rect = self.item_rects[self.selected_index]
        if selected_rect.top < self.content_area.top:
            self.scroll_y = max(0, self.scroll_y - (self.content_area.top - selected_rect.top))
            self._rebuild_layout_for_scroll()
        elif selected_rect.bottom > self.content_area.bottom:
            self.scroll_y = min(self.max_scroll, self.scroll_y + (selected_rect.bottom - self.content_area.bottom))
            self._rebuild_layout_for_scroll()

    def _save_changes(self):
        if not self.dirty_keys:
            self.status_message = "No pending changes."
            self.status_tone = "info"
            return

        updated_count = 0
        for item in self.items:
            if item.key not in self.dirty_keys:
                continue
            Config.write_config(key=item.key, value=self.pending_values[item.key])
            item.value = self.pending_values[item.key]
            updated_count += 1

        self.dirty_keys.clear()
        if pygame.mixer.get_init() is not None:
            pygame.mixer.music.set_volume(Config.MUSIC_VOLUME)

        self.status_message = f"Saved {updated_count} setting(s)."
        self.status_tone = "success"

    def _discard_changes(self):
        Config.load_config()
        self._load_items()
        self.status_message = "Reloaded values from config.jsonc."
        self.status_tone = "info"

    def _index_at_pos(self, pos):
        for index, rect in enumerate(self.item_rects):
            if rect.collidepoint(pos):
                return index
        return None

    def _set_slider_from_mouse(self, key, mouse_x):
        if key not in self.slider_rects:
            return
        item = next((entry for entry in self.items if entry.key == key), None)
        if item is None or item.min_value is None or item.max_value is None:
            return

        slider_rect = self.slider_rects[key]
        ratio = (mouse_x - slider_rect.left) / max(1, slider_rect.width)
        ratio = max(0.0, min(1.0, ratio))
        value = item.min_value + (item.max_value - item.min_value) * ratio
        if item.step > 0:
            value = round(value / item.step) * item.step
        self._set_item_value(item, value)

    def process_input(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if self.save_button_rect.collidepoint(event.pos):
                        self._save_changes()
                        continue
                    if self.reset_button_rect.collidepoint(event.pos):
                        self._discard_changes()
                        continue

                    index = self._index_at_pos(event.pos)
                    if index is not None:
                        self.selected_index = index
                        self._set_status_for_selected()
                        item = self.items[index]

                        if item.control == "text" and self.value_rects.get(item.key, pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                            self._begin_text_edit(index)
                        elif item.control == "slider" and item.key in self.slider_rects:
                            if self.slider_rects[item.key].collidepoint(event.pos):
                                self.dragging_slider_key = item.key
                                self._set_slider_from_mouse(item.key, event.pos[0])

                elif event.button == 4:
                    self.scroll_y = max(0, self.scroll_y - 42)
                    self._rebuild_layout_for_scroll()
                elif event.button == 5:
                    self.scroll_y = min(self.max_scroll, self.scroll_y + 42)
                    self._rebuild_layout_for_scroll()

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging_slider_key = None

            elif event.type == pygame.MOUSEMOTION and self.dragging_slider_key is not None:
                self._set_slider_from_mouse(self.dragging_slider_key, event.pos[0])

            elif event.type == pygame.TEXTINPUT and self.editing_key is not None:
                if len(self.edit_buffer) < 128:
                    self.edit_buffer += event.text

            elif event.type == pygame.KEYDOWN:
                if self.editing_key is not None:
                    if event.key == pygame.K_RETURN:
                        self._commit_text_edit()
                    elif event.key == pygame.K_ESCAPE:
                        self._cancel_text_edit()
                    elif event.key == pygame.K_BACKSPACE:
                        self.edit_buffer = self.edit_buffer[:-1]
                    continue

                if event.key == pygame.K_ESCAPE:
                    from scenes.main_menu import MainMenu

                    self.switch_to_scene(MainMenu())
                    continue

                if event.key == pygame.K_UP and self.items:
                    self.selected_index = max(0, self.selected_index - 1)
                    self._ensure_selection_visible()
                    self._set_status_for_selected()
                elif event.key == pygame.K_DOWN and self.items:
                    self.selected_index = min(len(self.items) - 1, self.selected_index + 1)
                    self._ensure_selection_visible()
                    self._set_status_for_selected()
                elif event.key == pygame.K_LEFT:
                    self._adjust_selected_numeric(direction=-1, boost=bool(event.mod & pygame.KMOD_SHIFT))
                elif event.key == pygame.K_RIGHT:
                    self._adjust_selected_numeric(direction=1, boost=bool(event.mod & pygame.KMOD_SHIFT))
                elif event.key == pygame.K_SPACE:
                    self._toggle_selected_bool()
                elif event.key == pygame.K_RETURN and self.items:
                    self._begin_text_edit(self.selected_index)
                elif event.key == pygame.K_s:
                    self._save_changes()
                elif event.key == pygame.K_r:
                    self._discard_changes()

    def update(self):
        if self.editing_key is not None:
            self.caret_visible = (pygame.time.get_ticks() // 450) % 2 == 0
        else:
            self.caret_visible = False

    def _draw_value_control(self, screen, item, card_rect):
        value_rect = pygame.Rect(card_rect.right - 280, card_rect.y + 12, 250, card_rect.height - 24)
        self.value_rects[item.key] = value_rect

        mode_label_map = {
            "text": "TEXT",
            "number": "ARROW",
            "slider": "SLIDER",
            "toggle": "TOGGLE",
        }
        mode_label = mode_label_map.get(item.control, "INPUT")
        badge_rect = pygame.Rect(value_rect.x - 78, value_rect.y + 8, 70, 24)
        badge_fill = (47, 58, 81) if item.control != "text" else (64, 84, 126)
        pygame.draw.rect(screen, badge_fill, badge_rect, border_radius=12)
        pygame.draw.rect(screen, (105, 128, 177), badge_rect, width=1, border_radius=12)
        badge_text = self.small_font.render(mode_label, True, self.text_color)
        screen.blit(badge_text, badge_text.get_rect(center=badge_rect.center))

        pygame.draw.rect(screen, (30, 36, 51), value_rect, border_radius=8)
        pygame.draw.rect(screen, (95, 105, 133), value_rect, width=2, border_radius=8)

        if item.control == "slider" and item.min_value is not None and item.max_value is not None:
            slider_rect = pygame.Rect(value_rect.x + 12, value_rect.centery - 5, value_rect.width - 24, 10)
            self.slider_rects[item.key] = slider_rect
            pygame.draw.rect(screen, (58, 68, 92), slider_rect, border_radius=5)

            current = float(self.pending_values[item.key])
            ratio = (current - item.min_value) / max(0.0001, item.max_value - item.min_value)
            ratio = max(0.0, min(1.0, ratio))
            fill_rect = pygame.Rect(slider_rect.x, slider_rect.y, int(slider_rect.width * ratio), slider_rect.height)
            pygame.draw.rect(screen, (121, 165, 255), fill_rect, border_radius=5)

            knob_x = slider_rect.x + int(slider_rect.width * ratio)
            pygame.draw.circle(screen, (235, 240, 255), (knob_x, slider_rect.centery), 7)

            text = self.value_font.render(self._value_text(item), True, self.text_color)
            screen.blit(text, text.get_rect(midtop=(value_rect.centerx, value_rect.y + 4)))
            return

        if item.control == "toggle":
            current = bool(self.pending_values[item.key])
            label = "ON" if current else "OFF"
            color = self.success_color if current else self.error_color
            text = self.key_font.render(label, True, color)
            screen.blit(text, text.get_rect(center=value_rect.center))
            return

        render_text = self.edit_buffer if self.editing_key == item.key else self._value_text(item)
        text_surface = self.value_font.render(render_text, True, self.text_color)
        text_x = value_rect.x + 10
        text_y = value_rect.centery - (text_surface.get_height() // 2)
        screen.blit(text_surface, (text_x, text_y))

        if self.editing_key == item.key and self.caret_visible:
            caret_x = text_x + text_surface.get_width() + 2
            caret_top = text_y + 2
            caret_bottom = text_y + text_surface.get_height() - 2
            pygame.draw.line(screen, self.text_color, (caret_x, caret_top), (caret_x, caret_bottom), 2)

    def render(self, screen):
        width, height = screen.get_size()
        if (width, height) != self.layout_size:
            self._build_layout(width, height)

        screen.fill(self.background_color)

        title_surface = self.title_font.render("Settings", True, self.text_color)
        screen.blit(title_surface, (self.margin, self.margin))

        legend_text = "Input modes: Enter = type text, Left/Right = adjust number/slider, Space = toggle"
        legend_surface = self.small_font.render(legend_text, True, self.subtle_text_color)
        screen.blit(legend_surface, (self.margin, self.margin + self.title_font.get_height() + 2))

        dirty_text = self.small_font.render(f"Pending changes: {len(self.dirty_keys)}", True, self.subtle_text_color)
        screen.blit(dirty_text, (self.margin, self.margin + self.title_font.get_height() + 20))

        pygame.draw.rect(screen, self.panel_color, self.content_area, border_radius=10)

        self.item_rects = []
        self.value_rects = {}
        self.slider_rects = {}

        clip_before = screen.get_clip()
        screen.set_clip(self.content_area)

        y = self.content_area.y - self.scroll_y
        last_section = None
        for index, item in enumerate(self.items):
            if item.section != last_section:
                section_surface = self.section_font.render(item.section, True, self.subtle_text_color)
                screen.blit(section_surface, (self.content_area.x + 12, y + 4))
                y += 28
                last_section = item.section

            card_rect = pygame.Rect(self.content_area.x + 10, y, self.content_area.width - 20, 64)
            self.item_rects.append(card_rect)

            fill_color = self.card_selected_color if index == self.selected_index else self.card_color
            pygame.draw.rect(screen, fill_color, card_rect, border_radius=8)

            key_surface = self.key_font.render(item.label, True, self.text_color)
            screen.blit(key_surface, (card_rect.x + 12, card_rect.y + 10))

            key_hint = f"{item.key}  [{item.type_name}]  {self._control_hint(item)}"
            if item.key in self.dirty_keys:
                key_hint += "  *"
            hint_surface = self.small_font.render(key_hint, True, self.subtle_text_color)
            screen.blit(hint_surface, (card_rect.x + 12, card_rect.y + 34))

            self._draw_value_control(screen, item, card_rect)

            y += 74

        screen.set_clip(clip_before)

        save_fill = (40, 155, 85)
        reset_fill = (68, 84, 117)

        pygame.draw.rect(screen, reset_fill, self.reset_button_rect, border_radius=8)
        pygame.draw.rect(screen, (95, 105, 133), self.reset_button_rect, width=2, border_radius=8)
        reset_label = self.value_font.render("Reload", True, self.text_color)
        screen.blit(reset_label, reset_label.get_rect(center=self.reset_button_rect.center))

        pygame.draw.rect(screen, save_fill, self.save_button_rect, border_radius=8)
        pygame.draw.rect(screen, (68, 213, 126), self.save_button_rect, width=2, border_radius=8)
        save_label = self.value_font.render("Save", True, self.text_color)
        screen.blit(save_label, save_label.get_rect(center=self.save_button_rect.center))

        status_surface = self.small_font.render(self.status_message, True, self._status_color())
        screen.blit(status_surface, (self.margin, self.content_area.bottom + 18))
