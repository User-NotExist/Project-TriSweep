from abc import ABC, abstractmethod


class SceneBase(ABC):
    def __init__(self):
        self.next = self

    @abstractmethod
    def process_input(self, events):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def render(self, screen):
        pass

    def on_scene_exit(self):
        pass

    def switch_to_scene(self, next_scene):
        self.on_scene_exit()
        self.next = next_scene
