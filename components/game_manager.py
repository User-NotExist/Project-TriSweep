from components.song import Song
from components.chart import Chart
from components.player import Player
from typing import Optional

class GameManager:
    def __init__(self, song: Optional[Song] = None, chart: Optional[Chart] = None):
        self._playing_song = song
        self._playing_chart = chart
        self._player = Player()

    @property
    def player(self) -> Player:
        return self._player

