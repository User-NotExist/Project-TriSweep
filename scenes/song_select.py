from scenes.scene_base import SceneBase
from pathlib import Path

EASY_COLOR = (52, 235, 58)
ADVANCED_COLOR = (250, 165, 37)
EXPERT_COLOR = (250, 41, 37)
MASTER_COLOR = (156, 39, 176)
SONG_ASSET_PATH = Path("./data/songs/")

class SongSelect(SceneBase):
    def __init__(self):
        super().__init__()

        songs_folder = [f for f in SONG_ASSET_PATH.iterdir() if f.is_dir()]
        self.songs = []
        for folder in songs_folder:
            meta_path = folder / "meta.jsonc"
            if meta_path.exists():
                self.songs.append(Song(folder))
            else:
                print(f"Warning: meta.jsonc not found in {folder}, skipping...")


    def ProcessInput(self, events):
        pass

    def Update(self):
        pass

    def Render(self, screen):
        pass