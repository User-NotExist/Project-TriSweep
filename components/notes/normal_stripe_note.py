from components.local_enum.judgement_level import JudgementLevel
from components.notes.note_base import NoteBase
import pygame


class NormalStripeNote(NoteBase):
    def __init__(self, start_stamp, end_stamp, lane, color_override):
        super().__init__(start_stamp, end_stamp, lane, 5, color_override)
        self.base_score = 100
        if self.end_time != -1:
            self.base_score = 200

    def draw_note(self, width, note_speed, **kwargs):
        note_width = max(1, int(width))
        min_height = max(1, int(kwargs.get("min_height", 18)))
        note_speed_px_per_ms = abs(float(note_speed)) / 1000.0

        if self.is_long:
            duration_height = int(self.duration_ms * note_speed_px_per_ms)
            note_height = max(min_height, duration_height)
        else:
            explicit_height = kwargs.get("note_height", self.TAP_NOTE_HEIGHT)
            note_height = max(min_height, int(explicit_height))

        note_surface = pygame.Surface((note_width, note_height), pygame.SRCALPHA)
        note_surface.fill(self.resolved_color())

        stripe_spacing = max(6, int(kwargs.get("stripe_spacing", 14)))
        stripe_width = max(1, int(kwargs.get("stripe_width", 2)))
        stripe_color = (255, 255, 255, 220)

        # Draw repeated diagonal stripes clipped inside note bounds.
        for offset in range(-note_height, note_width + note_height, stripe_spacing):
            start_point = (offset, note_height - 1)
            end_point = (offset + note_height, -1)
            pygame.draw.line(note_surface, stripe_color, start_point, end_point, stripe_width)

        self._draw_note_border(note_surface)

        return note_surface
