from pathlib import Path
from jsonc_parser.parser import JsoncParser

from components.chart import Chart

class Song:
    def __init__(self, path_to_folder : Path):
        self.__path_to_folder = path_to_folder
        self.__path_to_meta = self.__path_to_folder / "meta.jsonc"
        self.__charts = []
        self.__meta = {}
        try:
            self.__meta = self.jsonc_load()
        except FileNotFoundError as e:
            print(e)
            return None
        
        for diff in self.__meta.get("difficulty", []):
            try:
                chart = Chart(diff, self.__path_to_folder)
                self.__charts.append(chart)
            except Exception as e:
                print(f"Error loading chart for difficulty {diff.get('name', 'Unknown')}: {e}")
                continue

        print(f"Loaded song: {self.title} by {self.artist}")

    def jsonc_load(self):
        if not self.__path_to_meta.exists():
            raise FileNotFoundError(f"Meta file not found: {self.__path_to_meta}")

        with open(self.__path_to_meta, "r", encoding="utf-8") as f:
            data = JsoncParser.parse_str(f.read())

        return data

    def raw_meta(self) -> dict:
        return self.__meta

    @property
    def title(self) -> str:
        return self.__meta.get("title", "Unknown Song")

    @property
    def translated_title(self) -> str:
        return self.__meta.get("translated_title", self.title)

    @property
    def artist(self) -> str:
        return self.__meta.get("artist", "Unknown Artist")

    @property
    def version(self) -> str:
        return self.__meta.get("version", "1.0")

    @property
    def bpm(self) -> float:
        return float(self.__meta.get("bpm", 120.0))

    @property
    def offset(self) -> float:
        return float(self.__meta.get("offset", 0.0))

    @property
    def length(self) -> float:
        return float(self.__meta.get("length", 0.0))

    @property
    def preview_start(self) -> float:
        return float(self.__meta.get("previewStart", 0.0))

    @property
    def preview_duration(self) -> float:
        return float(self.__meta.get("previewDuration", 0.0))

    @property
    def music_path(self) -> Path:
        return self.__path_to_folder / self.__meta.get("music_path", "")

    @property
    def jacket_path(self) -> Path:
        return self.__path_to_folder / self.__meta.get("jacket_path", "")

    @property
    def folder_path(self) -> Path:
        return self.__path_to_folder

    @property
    def difficulty(self) -> list:
        return self.__charts

    @property
    def tags(self) -> list:
        return self.__meta.get("tags", [])

    @property
    def created_at(self) -> str:
        return self.__meta.get("created_at", "")

    @property
    def updated_at(self) -> str:
        return self.__meta.get("updated_at", "")

    @property
    def hidden(self) -> bool:
        return bool(self.__meta.get("hidden", False))

if __name__ == "__main__":
    song = Song(Path("D:\\UniProject\\TriSweep\\data\\songs\\THE RHYTHM SENSE TEST"))
    print(f"Title: {song.title}")
    print(f"Artist: {song.artist}")
    print(f"BPM: {song.bpm}")
    print(f"Tags: {', '.join(song.tags)}")
    print(f"Difficulty {song.raw_meta()}")