from pathlib import Path
import csv

from components.notes.break_note import BreakNote
from components.notes.break_stripe_note import BreakStripeNote
from components.notes.normal_note import NormalNote
from components.notes.normal_stripe_note import NormalStripeNote
from components.obstacles.collect_obstacle import CollectObstacle
from components.obstacles.damage_obstacle import DamageObstacle


class Chart:
    SIMULTANEOUS_NOTE_COLOR = (255, 255, 0)

    NOTE_FACTORIES = {
        1: NormalNote,
        2: BreakNote,
        5: NormalStripeNote,
        6: BreakStripeNote,
    }
    OBSTACLE_FACTORIES = {
        3: DamageObstacle,
        4: CollectObstacle,
    }

    def __init__(self, diff_meta: dict, path_to_folder):
        self.name = diff_meta.get("name", "Unknown")
        self.level = diff_meta.get("level", 0)
        self.chart_author = diff_meta.get("chart_author", "Unknown")
        self.chart_path = path_to_folder / diff_meta.get("chart_path", "")
        self.forced_note_speed = self._coerce_forced_note_speed(diff_meta.get("forced_note_speed"))
        self._is_chart_initialized = False
        self._notes = []
        self._obstacles = []

    @staticmethod
    def _coerce_forced_note_speed(value):
        if value in (None, ""):
            return None

        try:
            note_speed = float(value)
        except (TypeError, ValueError):
            print(f"[Chart] Invalid forced_note_speed '{value}', ignoring")
            return None

        if note_speed <= 0:
            print(f"[Chart] forced_note_speed must be > 0, got '{value}', ignoring")
            return None

        return note_speed

    @property
    def notes(self):
        if not self._is_chart_initialized:
            self.load_from_gay_file()

        return self._notes

    @property
    def obstacles(self):
        if not self._is_chart_initialized:
            self.load_from_gay_file()

        return self._obstacles

    @property
    def is_chart_initialized(self):
        return self._is_chart_initialized

    def _mark_simultaneous_lane_notes(self):
        grouped_notes = {}
        for note in self._notes:
            grouped_notes.setdefault((note.lane, note.start_time), []).append(note)

        # Highlight same-lane chord overlaps with a fixed color for quick visual debugging.
        for notes in grouped_notes.values():
            if len(notes) >= 2:
                for note in notes:
                    note.color_override = self.SIMULTANEOUS_NOTE_COLOR

    def load_from_gay_file(self, chart_path=None):
        resolved_path = Path(chart_path) if chart_path is not None else self.chart_path

        self._notes = []
        self._obstacles = []

        if not resolved_path or not resolved_path.exists() or not resolved_path.is_file():
            print(f"[Chart] Missing chart file: {resolved_path}")
            self._is_chart_initialized = True
            return

        with open(resolved_path, "r", encoding="utf-8-sig", newline="") as chart_file:
            reader = csv.DictReader(chart_file)
            if not reader.fieldnames:
                print(f"[Chart] Missing CSV header in chart file: {resolved_path}")
                self._is_chart_initialized = True
                return

            required_columns = {"start_stamp", "end_stamp", "lane", "type", "color_override"}
            normalized_headers = {header.strip() for header in reader.fieldnames if header}
            missing_columns = required_columns - normalized_headers
            if missing_columns:
                print(
                    f"[Chart] Missing required columns {sorted(missing_columns)} in {resolved_path}"
                )
                self._is_chart_initialized = True
                return

            for row_index, raw_row in enumerate(reader, start=2):
                row = {str(key).strip(): value for key, value in raw_row.items()}

                try:
                    note_type = int(row.get("type", ""))
                except Exception:
                    print(f"[Chart] Row {row_index}: invalid type '{row.get('type')}', skipping")
                    continue

                factory = self.NOTE_FACTORIES.get(note_type)
                target_collection = self._notes
                if factory is None:
                    factory = self.OBSTACLE_FACTORIES.get(note_type)
                    target_collection = self._obstacles

                if factory is None:
                    print(f"[Chart] Row {row_index}: unknown type '{note_type}', skipping")
                    continue

                item = factory(
                    row.get("start_stamp"),
                    row.get("end_stamp"),
                    row.get("lane"),
                    row.get("color_override", -1),
                )

                if not item.is_valid:
                    print(f"[Chart] Row {row_index}: {item.validation_error}, skipping")
                    continue

                target_collection.append(item)

        self._mark_simultaneous_lane_notes()

        self._is_chart_initialized = True

