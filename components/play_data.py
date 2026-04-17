from components.local_enum.judgement_level import JudgementLevel
from components.obstacles.collect_obstacle import CollectObstacle
from components.obstacles.obstacle_base import ObstacleBase
from components.notes.note_base import NoteBase
from components.song import Song
from components.chart import Chart
import math
import json
import re
from datetime import datetime
from pathlib import Path

class PlayData:

    PERCENTAGE_WEIGHT = {
        "base": 950000,
        "collect": 50000,
        "bonus": 10000
    }

    def __init__(self, player_name : str, song : Song, chart : Chart):
        self._player_name = player_name
        self._song = song
        self._chart = chart
        self._play_number = self._get_play_count()

        self._max_base_note_raw = 0
        self._max_collect_raw = 0
        #self._max_avoid_raw = 0
        self._max_bonus_raw = 0
        self._max_combo = 0
        self._create_max_raw()

        self._recorded_hit_score = []
        self._recorded_note_hit = []
        self._recorded_player_x = []
        self._last_player_x_sample_ms = None
        self._base_note_raw = 0
        self._collect_raw = 0
        #self._avoid_raw = 0
        self._bonus_raw = 0
        self._combo = 0
        self._highest_combo = 0
        self._base_penalty_raw = 0
        self._collect_penalty_raw = 0
        self._bonus_penalty_raw = 0
        self._round_end_reason = "completed"
        self._played_to_song_end = True

    def set_round_end_status(self, reason: str):
        normalized_reason = str(reason or "completed").strip().lower()
        valid_reasons = {"completed", "skipped", "died"}
        if normalized_reason not in valid_reasons:
            normalized_reason = "completed"

        self._round_end_reason = normalized_reason
        self._played_to_song_end = normalized_reason == "completed"

    @staticmethod
    def _target_judgement_for_note(note: NoteBase):
        # Break notes require CRITPERFECT to avoid display score decrease.
        return JudgementLevel.CRITPERFECT

    def record_note(self, note : NoteBase, hit_error : int, judgement_level : JudgementLevel, pressed_side : int):

        if judgement_level == JudgementLevel.MISS:
            self._combo = 0
        else:
            self._combo += 1
            if self._combo > self._highest_combo:
                self._highest_combo = self._combo

        score = note.get_score(judgement_level, hit_error=hit_error)
        self._base_note_raw += score[0]
        self._bonus_raw += score[1]

        target_judgement = self._target_judgement_for_note(note)
        target_score = note.get_score(target_judgement, hit_error=0)
        self._base_penalty_raw += max(0, int(target_score[0]) - int(score[0]))
        self._bonus_penalty_raw += max(0, int(target_score[1]) - int(score[1]))

        self._recorded_note_hit.append({
            "note_time" : note.start_time,
            "note_type": note.note_type,
            "hit_error" : hit_error,
            "judgement_level" : judgement_level,
            "pressed_side" : pressed_side,
            "current_combo" : self._combo
        })

        self._recorded_hit_score.append({
            "object_type" : "NOTE",
            "type_id" : note.note_type,
            "time": note.start_time,
            "current_score" : self.current_score
        })

    def record_obstacle(self, obstacle : ObstacleBase, judgement_level : JudgementLevel):
        if judgement_level == JudgementLevel.MISS:
            self._combo = 0
        else:
            self._combo += 1
            if self._combo > self._max_combo:
                self._max_combo = self._combo

        if isinstance(obstacle, CollectObstacle):
            actual_collect_score = int(obstacle.get_score(judgement_level))
            self._collect_raw += actual_collect_score
            target_collect_score = int(obstacle.get_score(JudgementLevel.CRITPERFECT))
            self._collect_penalty_raw += max(0, target_collect_score - actual_collect_score)

            self._recorded_hit_score.append({
                "object_type": "OBSTACLE",
                "type_id": obstacle.obstacle_type,
                "time": obstacle.start_time,
                "current_score": self.current_score
            })

    def _get_play_count(self):
        diff_save_folder = self._song.folder_path / self._chart.name
        if not diff_save_folder.exists():
            diff_save_folder.mkdir()
            return 1

        existing_files = diff_save_folder.glob("*")
        count = 1

        for existing_file in existing_files:
            if existing_file.is_file():
                count += 1

        return count

    def record_player_x(self, player_x: float, timestamp_ms: int, center_x: float = 0.0):
        timestamp_ms = int(timestamp_ms)
        if self._last_player_x_sample_ms is not None:
            if (timestamp_ms - int(self._last_player_x_sample_ms)) < 500:
                return

        centered_x = float(player_x) - float(center_x)
        self._recorded_player_x.append(
            {
                "timestamp_ms": timestamp_ms,
                "x_position": centered_x,
            }
        )
        self._last_player_x_sample_ms = timestamp_ms


    def _create_max_raw(self):
        for note in self._chart.notes:
            score = note.get_score(JudgementLevel.CRITPERFECT, hit_error=0)

            self._max_base_note_raw += score[0]
            self._max_bonus_raw += score[1]
            self._max_combo += 1

        for obstacle in self._chart.obstacles:
            score = obstacle.get_score(JudgementLevel.CRITPERFECT)
            if isinstance(obstacle, CollectObstacle):
                self._max_collect_raw += score
                self._max_combo += 1

    def total_score(self):
        base_ratio = (self._base_note_raw / self._max_base_note_raw) if self._max_base_note_raw > 0 else 1.0
        collect_ratio = (self._collect_raw / self._max_collect_raw) if self._max_collect_raw > 0 else 1.0
        bonus_ratio = (self._bonus_raw / self._max_bonus_raw) if self._max_bonus_raw > 0 else 1.0

        base_score = min(
            PlayData.PERCENTAGE_WEIGHT["base"],
            math.floor(base_ratio * PlayData.PERCENTAGE_WEIGHT["base"]),
        )
        collect_score = min(
            PlayData.PERCENTAGE_WEIGHT["collect"],
            math.floor(collect_ratio * PlayData.PERCENTAGE_WEIGHT["collect"]),
        )
        bonus = min(
            PlayData.PERCENTAGE_WEIGHT["bonus"],
            math.floor(bonus_ratio * PlayData.PERCENTAGE_WEIGHT["bonus"]),
        )

        return sum([base_score, collect_score, bonus])

    @property
    def current_score(self):
        return self.total_score()

    @property
    def current_combo(self):
        return int(self._combo)

    @property
    def highest_combo(self):
        return int(self._highest_combo)

    @property
    def max_combo(self):
        return int(self._max_combo)

    @property
    def song(self):
        return self._song

    @property
    def chart(self):
        return self._chart

    @property
    def decreasing_display_score(self):
        base_penalty = 0
        collect_penalty = 0
        bonus_penalty = 0

        if self._max_base_note_raw > 0:
            base_penalty = math.floor(
                (self._base_penalty_raw / self._max_base_note_raw) * PlayData.PERCENTAGE_WEIGHT["base"]
            )
        if self._max_collect_raw > 0:
            collect_penalty = math.floor(
                (self._collect_penalty_raw / self._max_collect_raw) * PlayData.PERCENTAGE_WEIGHT["collect"]
            )
        if self._max_bonus_raw > 0:
            bonus_penalty = math.floor(
                (self._bonus_penalty_raw / self._max_bonus_raw) * PlayData.PERCENTAGE_WEIGHT["bonus"]
            )

        max_score = sum(PlayData.PERCENTAGE_WEIGHT.values())
        return max(0, int(max_score - base_penalty - collect_penalty - bonus_penalty))

    def __repr__(self):
        return (f"PlayData(player_name={self._player_name}, song={self._song.title}, chart={self._chart.name})\n"
                f"_max_base_note_score={self._max_base_note_raw}\n"
                f"_max_collect_score={self._max_collect_raw}\n"
                f"_max_bonus_score={self._max_bonus_raw}\n"
                f"total_combo={self._max_combo}\n"
                f"total_max_score={self._max_base_note_raw + self._max_collect_raw + self._max_bonus_raw}\n")

    @staticmethod
    def _sanitize_filename_component(text: str):
        cleaned = re.sub(r'[<>:"/\\|?*]', "_", str(text or "Unknown"))
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = cleaned.rstrip(". ")
        return cleaned or "Unknown"

    def _to_serializable_note_hit(self, note_hit: dict):
        serialized = dict(note_hit)
        judgement = serialized.get("judgement_level")
        if isinstance(judgement, JudgementLevel):
            serialized["judgement_level"] = judgement.name
        return serialized

    def to_serializable_dict(self):
        return {
            "player_name": self._player_name,
            "song_title": getattr(self._song, "title", "Unknown Song"),
            "song_artist": getattr(self._song, "artist", "Unknown Artist"),
            "chart_name": getattr(self._chart, "name", "Unknown"),
            "chart_author": getattr(self._chart, "chart_author", "Unknown"),
            "play_number": int(self._play_number),
            "max_base_note_raw": int(self._max_base_note_raw),
            "max_collect_raw": int(self._max_collect_raw),
            "max_bonus_raw": int(self._max_bonus_raw),
            "max_combo": int(self._max_combo),
            "base_note_raw": int(self._base_note_raw),
            "collect_raw": int(self._collect_raw),
            "bonus_raw": int(self._bonus_raw),
            "current_combo": int(self._combo),
            "highest_combo": int(self._highest_combo),
            "base_penalty_raw": int(self._base_penalty_raw),
            "collect_penalty_raw": int(self._collect_penalty_raw),
            "bonus_penalty_raw": int(self._bonus_penalty_raw),
            "total_score": int(self.current_score),
            "round_end_reason": str(self._round_end_reason),
            "played_to_song_end": bool(self._played_to_song_end),
            "recorded_note_hit": [
                self._to_serializable_note_hit(entry) for entry in self._recorded_note_hit
            ],
            "recorded_player_x": list(self._recorded_player_x),
        }

    def build_result_filename(self, timestamp: datetime | None = None):
        stamp = timestamp or datetime.now()
        player_name = self._sanitize_filename_component(self._player_name)
        song_title = self._sanitize_filename_component(getattr(self._song, "title", "Unknown Song"))
        chart_name = self._sanitize_filename_component(getattr(self._chart, "name", "Unknown"))
        datetime_part = stamp.strftime("%Y-%m-%d %H-%M-%S")
        return f"{player_name} - {song_title} - {chart_name} - {datetime_part}.json"

    def save_to_json(self, output_dir: Path | None = None, timestamp: datetime | None = None):
        target_dir = Path(output_dir) if output_dir is not None else (self._song.folder_path / self._chart.name)
        target_dir.mkdir(parents=True, exist_ok=True)

        file_name = self.build_result_filename(timestamp=timestamp)
        file_path = target_dir / file_name

        payload = self.to_serializable_dict()
        payload["saved_at"] = (timestamp or datetime.now()).isoformat(timespec="seconds")

        with open(file_path, "w", encoding="utf-8") as output_file:
            json.dump(payload, output_file, ensure_ascii=False, indent=2)

        return file_path



"Testing"
if __name__ == '__main__':
    from pathlib import Path
    from config import Config
    Config.load_config(Path("D:\\UniProject\\TriSweep\\config.jsonc"), Path("D:\\UniProject\\TriSweep\\config_type.jsonc"))
    song = Song(Path("D:\\UniProject\\TriSweep\\data\\songs\\7 Wonders"))

    play_data = PlayData("GUEST", song, song.difficulty[0])
    print(repr(play_data))