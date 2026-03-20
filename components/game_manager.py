from components.song import Song
from components.chart import Chart

class GameManager:
    def __init__(self, song : Song, chart : Chart):
        self._playing_song = song
        self._playing_chart = chart

