from pathlib import Path


class Chart:
    def __init__(self, diff_meta : dict):
        self.name = diff_meta.get("name", "Unknown")
        self.level = diff_meta.get("level", 0)
        self.chart_author = diff_meta.get("chart_author", "Unknown")
        self.chart_path = Path(diff_meta.get("chart_path", ""))
