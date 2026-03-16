from abc import ABC, abstractmethod

class SceneBase(ABC):
    def __init__(self):
        self.next = self

    @abstractmethod
    def ProcessInput(self, events):
        pass

    @abstractmethod
    def Update(self):
        pass

    @abstractmethod
    def Render(self, screen):
        pass

    def OnSceneExit(self):
        pass

    def SwitchToScene(self, next_scene):
        self.OnSceneExit()
        self.next = next_scene