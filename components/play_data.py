from components.local_enum.judgement_level import JudgementLevel
from components.obstacles.collect_obstacle import CollectObstacle
from components.obstacles.obstacle_base import ObstacleBase
from components.song import Song
from components.chart import Chart

class PlayData:

    PERCENTAGE_WEIGHT = {
        "base": 950000,
        "collect": 30000,
        "avoid": 20000,
        "bonus": 10000
    }

    def __init__(self, player_name : str, song : Song, chart : Chart):
        self._player_name = player_name
        self._song = song
        self._chart = chart
        self._play_number = self._get_play_count()

        self._max_base_note_raw = 0
        self._max_collect_raw = 0
        self._max_avoid_raw = 0
        self._max_bonus_raw = 0
        self._max_combo = 0
        self._create_max_raw()

        self._recorded_note_hit = []
        self._base_note_raw = 0
        self._collect_raw = 0
        self._avoid_raw = 0
        self._bonus_raw = 0
        self._combo = 0
        self._highest_combo = 0

    def record_note(self, note : NoteBase, hit_error : int, judgement_level : JudgementLevel, pressed_side : int):

        if judgement_level == JudgementLevel.MISS:
            self._combo = 0
        else:
            self._combo += 1
            if self._combo > self._max_combo:
                self._max_combo = self._combo

        score = note.get_score(judgement_level, hit_error=hit_error)
        self._base_note_raw += score[0]
        self._bonus_raw += score[1]

        self._recorded_note_hit.append({
            "note_time" : note.start_time,
            "note_type": note.note_type,
            "hit_error" : hit_error,
            "judgement_level" : judgement_level,
            "pressed_side" : pressed_side,
        })

    def record_obstacle(self, obstacle : ObstacleBase, judgement_level : JudgementLevel):
        if judgement_level == JudgementLevel.MISS:
            self._combo = 0
        else:
            self._combo += 1
            if self._combo > self._max_combo:
                self._max_combo = self._combo

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
            else:
                self._max_avoid_raw += score
                self._max_combo += 1

    def calculate_score(self):
        base_score = min(PlayData.PERCENTAGE_WEIGHT["base"], math.floor((self._base_note_raw // self._max_base_note_raw) * PlayData.PERCENTAGE_WEIGHT["base"]))
        collect_score = min(PlayData.PERCENTAGE_WEIGHT["collect"], math.floor((self._collect_raw // self._max_collect_raw) * PlayData.PERCENTAGE_WEIGHT["collect"]))
        avoid_score = min(PlayData.PERCENTAGE_WEIGHT["avoid"], math.floor((self._avoid_raw // self._max_avoid_raw) * PlayData.PERCENTAGE_WEIGHT["avoid"]))
        bonus = min(PlayData.PERCENTAGE_WEIGHT["bonus"], math.floor((self._bonus_raw // self._max_bonus_raw) * PlayData.PERCENTAGE_WEIGHT["bonus"]))

        return sum([base_score, collect_score, avoid_score, bonus])

    def __repr__(self):
        return (f"PlayData(player_name={self._player_name}, song={self._song.title}, chart={self._chart.name})\n"
                f"_max_base_note_score={self._max_base_note_raw}\n"
                f"_max_collect_score={self._max_collect_raw}\n"
                f"_max_avoid_score={self._max_avoid_raw}\n"
                f"_max_bonus_score={self._max_bonus_raw}\n"
                f"total_combo={self._max_combo}\n"
                f"total_max_score={self._max_base_note_raw + self._max_collect_raw + self._max_avoid_raw + self._max_bonus_raw}\n")

"Testing"
if __name__ == '__main__':
    from pathlib import Path
    from config import Config
    Config.load_config(Path("D:\\UniProject\\TriSweep\\config.jsonc"), Path("D:\\UniProject\\TriSweep\\config_type.jsonc"))
    song = Song(Path("D:\\UniProject\\TriSweep\\data\\songs\\7 Wonders"))

    play_data = PlayData("GUEST", song, song.difficulty[0])
    print(repr(play_data))