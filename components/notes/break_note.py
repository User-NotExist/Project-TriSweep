import math
from components.local_enum.judgement_level import JudgementLevel
from components.notes.note_base import NoteBase

from config import Config


class BreakNote(NoteBase):
    def __init__(self, start_stamp, end_stamp, lane, color_override):
        super().__init__(start_stamp, end_stamp, lane, 2, color_override)
        self.base_score = 400
        if self.end_time != -1:
            self.base_score = 500
        self.bonus_score = 100


    def get_score(self, judgement : JudgementLevel, **kwargs):
        hit_error_ms = kwargs.get("hit_error", 0)

        match judgement:
            case JudgementLevel.CRITPERFECT:
                return (self.base_score * Config.CRITICAL_PERFECT_SCORE) , self.bonus_score
            case JudgementLevel.PERFECT:
                range_between_judgement = Config.PERFECT_TIMING - Config.CRITICAL_PERFECT_TIMING
                bonus_multiplier = 1 - (0.5 * ((abs(hit_error_ms - Config.CRITICAL_PERFECT_TIMING) / range_between_judgement)))

                return (self.base_score * Config.PERFECT_SCORE) , math.floor(self.bonus_score * bonus_multiplier)
            case JudgementLevel.GREAT:
                range_between_judgement = Config.GREAT_TIMING - Config.PERFECT_TIMING
                bonus_multiplier = 0.5 - (0.2 * ((abs(hit_error_ms - Config.PERFECT_TIMING) / range_between_judgement)))

                return (self.base_score * Config.GREAT_SCORE) , math.floor(self.bonus_score * bonus_multiplier)
            case JudgementLevel.GOOD:
                return (self.base_score * Config.GOOD_SCORE) , math.floor(self.bonus_score * 0.1)
            case JudgementLevel.MISS:
                return 0, 0
