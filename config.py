import json
import re
from pathlib import Path
from jsonc_parser.parser import JsoncParser

class Config:
    """
    Contains all the config used by the game/editor.
    """

    "Player"
    PLAYER_MOVE_SPEED = 1.0
    PLAYER_LANE_SPEED = 9.0
    PLAYER_NAME = "GUEST"
    PLAYER_IMAGE_PATH = "./guest_player.png"

    "Key Settings"
    LANE_0_KEY_0 = "q"
    LANE_0_KEY_1 = "i"
    LANE_1_KEY_0 = "w"
    LANE_1_KEY_1 = "o"
    LANE_2_KEY_0 = "e"
    LANE_2_KEY_1 = "p"

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

    "Offset Setting (ms)"
    OFFSET_MUSIC = 0
    OFFSET_DISPLAY = 0

    _TYPE_NAME_MAP = {
        int: "int",
        float: "float",
        str: "str",
        bool: "bool",
    }

    BASE_DIR = Path(__file__).resolve().parent
    CONFIG_PATH = BASE_DIR / "config.jsonc"
    CONFIG_TYPE_PATH = BASE_DIR / "config_type.jsonc"
    _NON_CONFIG_KEYS = {"BASE_DIR", "CONFIG_PATH", "CONFIG_TYPE_PATH"}

    @classmethod
    def _resolve_path(cls, path_value, default_path: Path) -> Path:
        path = Path(path_value) if path_value is not None else default_path
        if not path.is_absolute():
            path = cls.BASE_DIR / path
        return path.resolve()

    @classmethod
    def _resolve_config_path(cls, config_path=None) -> Path:
        return cls._resolve_path(config_path, cls.CONFIG_PATH)

    @classmethod
    def _resolve_type_config_path(cls, type_config_path=None, config_path=None) -> Path:
        if type_config_path is not None:
            return cls._resolve_path(type_config_path, cls.CONFIG_TYPE_PATH)

        resolved_config_path = cls._resolve_config_path(config_path)
        if resolved_config_path == cls._resolve_config_path():
            return cls._resolve_path(None, cls.CONFIG_TYPE_PATH)
        return resolved_config_path.with_name("config_type.jsonc")

    @classmethod
    def _default_type_config_path(cls, config_path: Path) -> Path:
        return cls._resolve_type_config_path(config_path=config_path)

    @classmethod
    def _config_fields(cls):
        return {
            name: val for name, val in vars(cls).items()
            if (
                name.isupper()
                and not callable(val)
                and not name.startswith("__")
                and not name.startswith("_")
                and name not in cls._NON_CONFIG_KEYS
            )
        }

    @classmethod
    def _type_name_for_value(cls, value) -> str:
        return cls._TYPE_NAME_MAP.get(type(value), "str")

    @classmethod
    def _parse_jsonc_text(cls, text: str):
        try:
            return JsoncParser.parse_str(text)
        except Exception:
            # Fallback for files that include trailing commas before object/array close.
            cleaned = re.sub(r",\s*(?=[}\]])", "", text)
            return JsoncParser.parse_str(cleaned)

    @classmethod
    def _coerce_value(cls, key: str, value, target_type_name: str):
        try:
            if target_type_name == "bool":
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    lowered = value.strip().lower()
                    if lowered in {"true", "1", "yes", "on"}:
                        return True
                    if lowered in {"false", "0", "no", "off"}:
                        return False
                    raise ValueError(f"Cannot parse bool from '{value}'")
                return bool(value)
            if target_type_name == "int":
                return int(value)
            if target_type_name == "float":
                return float(value)
            if target_type_name == "str":
                return str(value)
        except Exception as e:
            raise ValueError(f"Failed to coerce '{key}' to {target_type_name}: {e}") from e

        raise ValueError(f"Unsupported type '{target_type_name}' for key '{key}'")

    @classmethod
    def _serialize_json_value(cls, value):
        return json.dumps(value, ensure_ascii=False)

    @classmethod
    def create_config_type_file(cls, type_config_path: Path = None):
        """
        Create a JSONC file that stores each config key's datatype.
        """
        type_config_path = cls._resolve_type_config_path(type_config_path)

        if type_config_path.exists():
            print(f"Config type file already exists at: {type_config_path}")
            return

        type_data = {
            key: cls._type_name_for_value(default_value)
            for key, default_value in cls._config_fields().items()
        }

        try:
            with open(type_config_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(type_data, indent=4))
            print(f"Config type file created at: {type_config_path}")
        except Exception as e:
            print(f"Error creating config type file at {type_config_path}: {e}")

    @classmethod
    def load_config_types(cls, type_config_path: Path = None):
        """
        Load type definitions for config keys from JSONC.
        Missing keys are filled from current class defaults.
        """
        type_config_path = cls._resolve_type_config_path(type_config_path)

        if not type_config_path.exists():
            print(f"Config type file does not exist at: {type_config_path}")
            print("Creating default config type file...")
            cls.create_config_type_file(type_config_path)

        default_types = {
            key: cls._type_name_for_value(default_value)
            for key, default_value in cls._config_fields().items()
        }

        try:
            with open(type_config_path, 'r', encoding='utf-8') as f:
                type_data = cls._parse_jsonc_text(f.read())

            missing_type_keys = set(default_types.keys()) - set(type_data.keys())
            if missing_type_keys:
                print(
                    f"Warning: Missing type keys in {type_config_path}: "
                    f"{', '.join(sorted(missing_type_keys))}"
                )
                for missing_key in missing_type_keys:
                    type_data[missing_key] = default_types[missing_key]

            for type_key in type_data.keys():
                if type_key not in default_types:
                    print(f"Warning: Unrecognized type key '{type_key}' in {type_config_path}")

            return type_data
        except Exception as e:
            print(f"Error loading config types from {type_config_path}: {e}")
            return default_types

    @classmethod
    def _upsert_key_value_in_jsonc(cls, config_text: str, key: str, serialized_value: str) -> str:
        key_pattern = re.compile(
            rf'(^\s*"{re.escape(key)}"\s*:\s*)(.*?)(\s*,?\s*(?://.*)?$)',
            re.MULTILINE,
        )

        if key_pattern.search(config_text):
            return key_pattern.sub(
                lambda match: f"{match.group(1)}{serialized_value}{match.group(3)}",
                config_text,
                count=1,
            )

        close_idx = config_text.rfind("}")
        if close_idx == -1:
            raise ValueError("Invalid config JSONC: missing closing brace")

        before_close = config_text[:close_idx].rstrip()
        after_close = config_text[close_idx:]

        last_char = before_close[-1:] if before_close else ""
        needs_comma = last_char not in {"{", ","}
        comma = "," if needs_comma else ""

        insertion = f'{comma}\n    "{key}": {serialized_value}\n'
        return before_close + insertion + after_close

    @classmethod
    def create_config_file(cls, config_path: Path = None):
        """
        Create a JSONC config file at `config_path` with the current class attribute values.
        Only includes uppercase attributes that are not callable and do not start with "__".
        """
        config_path = cls._resolve_config_path(config_path)

        if config_path.exists():
            print(f"Config file already exists at: {config_path}")
            return

        data = cls._config_fields()
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, indent=4))
            print(f"Config file created at: {config_path}")
        except Exception as e:
            print(f"Error creating config file at {config_path}: {e}")

    @classmethod
    def load_config(cls, config_path: Path = None, type_config_path: Path = None):
        """
        Load config values from a JSONC file at `config_path`.
        Detects and reports any expected class attributes (uppercase) that are missing
        from the file and warns about unrecognized keys.
        """
        config_path = cls._resolve_config_path(config_path)
        type_config_path = cls._resolve_type_config_path(type_config_path, config_path)

        if not config_path.exists():
            print(f"Config file does not exist at: {config_path}")
            print("Creating default config file...")
            cls.create_config_file(config_path)
        config_types = cls.load_config_types(type_config_path)

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = cls._parse_jsonc_text(f.read())

            # Expected keys: uppercase class attributes (non-callable)
            expected_keys = set(cls._config_fields().keys())

            file_keys = set(data.keys())
            missing_keys = expected_keys - file_keys
            if missing_keys:
                print(f"Warning: Missing config keys in {config_path}: {', '.join(sorted(missing_keys))}")

            for key, value in data.items():
                if hasattr(cls, key):
                    key_type = config_types.get(key, cls._type_name_for_value(getattr(cls, key)))
                    try:
                        setattr(cls, key, cls._coerce_value(key, value, key_type))
                    except ValueError as e:
                        print(f"Warning: {e}. Keeping default value for '{key}'.")
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
    def write_config(cls, config_path: Path = None, key: str = None, value=None, type_config_path: Path = None):
        """
        Write the current config values to a JSONC file at `config_path`.
        Only includes uppercase attributes that are not callable and do not start with "__".
        """

        config_path = cls._resolve_config_path(config_path)
        type_config_path = cls._resolve_type_config_path(type_config_path, config_path)

        if key is None:
            print("Error: Config key must be provided.")
            return

        if not config_path.exists():
            print(f"Config file does not exist at: {config_path}")
            print("Creating default config file...")
            cls.create_config_file(config_path)
        config_types = cls.load_config_types(type_config_path)

        if key not in cls._config_fields():
            print(f"Error: '{key}' is not a recognized config key.")
            return

        target_type = config_types.get(key, cls._type_name_for_value(getattr(cls, key)))
        try:
            parsed_value = cls._coerce_value(key, value, target_type)
            serialized_value = cls._serialize_json_value(parsed_value)

            with open(config_path, 'r', encoding='utf-8') as f:
                existing_text = f.read()

            updated_text = cls._upsert_key_value_in_jsonc(existing_text, key, serialized_value)

            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(updated_text)

            setattr(cls, key, parsed_value)
            print(f"Config file updated at: {config_path}")
        except Exception as e:
            print(f"Error writing config file at {config_path}: {e}")

if __name__ == "__main__":
    # Example usage
    Config.create_config_file()
    Config.create_config_type_file()
    Config.load_config()

    # print all config values
    print("Current Config Values:")
    for name in vars(Config):
        if (
            name.isupper()
            and not callable(getattr(Config, name))
            and not name.startswith("__")
            and not name.startswith("_")
            and name not in Config._NON_CONFIG_KEYS
        ):
            print(f"{name}: {getattr(Config, name)} {type(getattr(Config, name)).__name__}")