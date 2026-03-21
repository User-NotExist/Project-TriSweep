from components.local_enum.judgement_level import JudgementLevel
from components.notes.note_base import NoteBase
import pygame


class NormalNote(NoteBase):
    def __init__(self, start_stamp, end_stamp, lane, color_override):
        super().__init__(start_stamp, end_stamp, lane, 1, color_override)
        self.base_score = 200

    def draw_note(self, width, note_speed, **kwargs):
        super().draw_note(width, note_speed, **kwargs)