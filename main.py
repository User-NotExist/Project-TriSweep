from config import Config
from pathlib import Path
from scenes.main_menu import MainMenu

import pygame
import argparse

parser = argparse.ArgumentParser(description="TriSweep")
parser.add_argument("--game", type=bool, default=False, help="Force game to boot to game scene")
parser.add_argument("--fullscreen", type=bool, default=False, help="Force game screen size to fullscreen")
args = parser.parse_args()

CONFIG_PATH = Path("./config.jsonc")

Config.load_config(CONFIG_PATH)

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
    active_scene = PlaySpace()

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