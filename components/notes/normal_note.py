from components.notes.note_base import NoteBase


class NormalNote(NoteBase):
    def __init__(self, start_stamp, end_stamp, lane, color_override):
        super().__init__(start_stamp, end_stamp, lane, 1, color_override)
        self.base_score = 100
        if self.end_time != -1:
            self.base_score = 200

