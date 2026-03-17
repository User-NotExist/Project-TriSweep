import json
from pathlib import Path
from jsonc_parser.parser import JsoncParser

class Config:
    """
    Contains all the config used by the game/editor.
    """

    "Player"
    PLAYER_SPEED = 9.0
    PLAYER_NAME = "GUEST"
    PLAYER_IMAGE_PATH = "./guest_player.png"

    "Program"
    WINDOW_WIDTH = 900
    WINDOW_HEIGHT = 800
    FPS = 60
    MUSIC_VOLUME = 0.8
    SOUND_EFFECT_VOLUME = 0.8

    "Judgement Timing (ms)"
    CRITICAL_PERFECT_TIMING = 16
    PERFECT_TIMING = 50
    GREAT_TIMING = 100
    GOOD_TIMING = 150
    EARLY_MISS_TIMING = 200

    "Judgement Score (%)"
    CRITICAL_PERFECT_SCORE = 100
    PERFECT_SCORE = 100
    GREAT_SCORE = 80
    GOOD_SCORE = 50

    "Offset Setting (tick)"
    OFFSET_MUSIC = 0
    OFFSET_DISPLAY = 0

    @classmethod
    def create_config_file(cls, config_path: Path):
        """
        Create a JSONC config file at `config_path` with the current class attribute values.
        Only includes uppercase attributes that are not callable and do not start with "__".
        """
        if config_path.exists():
            print(f"Config file already exists at: {config_path}")
            return

        data = {
            name: val for name, val in vars(cls).items()
            if name.isupper() and not callable(val) and not name.startswith("__")
        }
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, indent=4))
            print(f"Config file created at: {config_path}")
        except Exception as e:
            print(f"Error creating config file at {config_path}: {e}")

    @classmethod
    def load_config(cls, config_path: Path):
        """
        Load config values from a JSONC file at `config_path`.
        Detects and reports any expected class attributes (uppercase) that are missing
        from the file and warns about unrecognized keys.
        """
        if not config_path.exists():
            print(f"Config file does not exist at: {config_path}")
            print("Creating default config file...")
            cls.create_config_file(config_path)

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = JsoncParser.parse_str(f.read())

            # Expected keys: uppercase class attributes (non-callable)
            expected_keys = {
                name for name, val in vars(cls).items()
                if name.isupper() and not callable(val) and not name.startswith("__")
            }

            file_keys = set(data.keys())
            missing_keys = expected_keys - file_keys
            if missing_keys:
                print(f"Warning: Missing config keys in {config_path}: {', '.join(sorted(missing_keys))}")

            for key, value in data.items():
                if hasattr(cls, key):
                    setattr(cls, key, value)
                else:
                    print(f"Warning: Unrecognized config key '{key}' in {config_path}")

            img_path = Path(cls.PLAYER_IMAGE_PATH)
            if not img_path.is_file():
                print(f"Warning: Player image path does not exist: {img_path}")
                cls.PLAYER_IMAGE_PATH = "./guest_player.png"
                print(f"Using default player image path: {cls.PLAYER_IMAGE_PATH}")

        except FileNotFoundError:
            print(f"Config file not found: {config_path}")
        except Exception as e:
            print(f"Error loading config from {config_path}: {e}")

    @classmethod
    def write_config(cls, config_path: Path):
        """
        Write the current config values to a JSONC file at `config_path`.
        Only includes uppercase attributes that are not callable and do not start with "__".
        """

        if not config_path.exists():
            print(f"Config file does not exist at: {config_path}??? Cannot write config.")
            return

        data = {
            name: val for name, val in vars(cls).items()
            if name.isupper() and not callable(val) and not name.startswith("__")
        }
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, indent=4))
            print(f"Config file updated at: {config_path}")
        except Exception as e:
            print(f"Error writing config file at {config_path}: {e}")

if __name__ == "__main__":
    # Example usage
    config_path = Path("config.jsonc")
    Config.create_config_file(config_path)
    Config.load_config(config_path)

    # print all config values
    print("Current Config Values:")
    for name in vars(Config):
        if name.isupper() and not callable(getattr(Config, name)) and not name.startswith("__"):
            print(f"{name}: {getattr(Config, name)} {type(getattr(Config, name)).__name__}")