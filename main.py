from config import Config
from pathlib import Path
from scenes.main_menu import MainMenu
from components.song import Song
from components.game_manager import GameManager

import pygame
import argparse

parser = argparse.ArgumentParser(description="TriSweep")
parser.add_argument("--game", type=bool, default=False, help="Force game to boot to game scene")
parser.add_argument("--fullscreen", type=bool, default=False, help="Force game screen size to fullscreen")
args = parser.parse_args()

CONFIG_PATH = Path("./config.jsonc")

Config.load_config(CONFIG_PATH)


def _build_test_game_manager():
    songs_root = Path("./data/songs")
    if songs_root.exists():
        for song_folder in sorted(path for path in songs_root.iterdir() if path.is_dir()):
            if not (song_folder / "meta.jsonc").exists():
                continue

            song = Song(song_folder)
            if song.hidden or not song.difficulty:
                continue

            chart = song.difficulty[0]
            return GameManager(song, chart, chart.notes, chart.obstacles)

    # Fallback keeps --game mode runnable even if no songs/charts are available.
    class _DummySong:
        title = "Dummy Song"
        artist = "Test Artist"

    class _DummyChart:
        name = "Test"

        @property
        def notes(self):
            return []

        @property
        def obstacles(self):
            return []

    dummy_song = _DummySong()
    dummy_chart = _DummyChart()
    return GameManager(dummy_song, dummy_chart, dummy_chart.notes, dummy_chart.obstacles)

pygame.init()

if not args.fullscreen:
    screen = pygame.display.set_mode((Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT))
else:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
clock = pygame.time.Clock()
pygame.display.set_caption("TriSweep")

if not args.game:
    active_scene = MainMenu()
else:
    from scenes.play_space import PlaySpace
    active_scene = PlaySpace(_build_test_game_manager())

running = True

while running:
    filtered_events = []
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        else:
            filtered_events.append(event)

    if active_scene == None:
        running = False
        break

    active_scene.process_input(filtered_events)
    active_scene.update()
    active_scene.render(screen)

    pygame.display.flip()

    active_scene = active_scene.next
    clock.tick(Config.FPS)