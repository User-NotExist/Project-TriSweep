from config import Config
from pathlib import Path
from scenes.main_menu import MainMenu
import pygame

CONFIG_PATH = Path("./config.jsonc")

Config.load_config(CONFIG_PATH)

pygame.init()
screen = pygame.display.set_mode((Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT))
clock = pygame.time.Clock()
pygame.display.set_caption("TriSweep")

active_scene = MainMenu()
running = True

while running:
    filtered_events = []
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        else:
            filtered_events.append(event)

    active_scene.process_input(filtered_events)
    active_scene.update()
    active_scene.render(screen)

    pygame.display.flip()

    active_scene = active_scene.next
    clock.tick(Config.FPS)