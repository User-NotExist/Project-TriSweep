from abc import ABC, abstractmethod
from components.local_enum.judgement_level import JudgementLevel

from components.song import Song
from config import Config


class NoteBase(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def draw_note(self):
        pass

    @abstractmethod
    def _calculate_judgement(self):
        pass

    @staticmethod
    def judgement_to_score(base_score : int, judgement : JudgementLevel):
        match judgement:
            case JudgementLevel.CRITPERFECT:
                return base_score * Config.CRITICAL_PERFECT_SCORE

            case JudgementLevel.PERFECT:
                return base_score * Config.PERFECT_SCORE

            case JudgementLevel.GREAT:
                return base_score * Config.GREAT_SCORE

            case JudgementLevel.GOOD:
                return base_score * Config.GOOD_SCORE

            case _:
                return 0
