

class Chart:
    def __init__(self, diff_meta : dict):
        self.name = diff_meta["name"]
        self.level = diff_meta["level"]
        self.chart_author = diff_meta["chart_author"]
        self.chart_path = Path(diff_meta["chart_path"])