# Project Description

## 1. Project Overview
- **Project Name:**  Project TriSweep


- **Brief Description:**  
Project TriSweep is a 3 lane vertical scrolling rhythm game with a hint of danmaku using a mouse. 
Players have to press to the beat while evading obstacles/bullets or collect the note to clear the chart. 
This game aims to provide a new challenge for rhythm game player while trying to keep the game easy enough to clear.


- **Problem Statement:**  
  - The arcade game O.N.G.E.K.I. (オンゲキ) isn't avaliable outside Japan.
  - Many rhythm game usually only have keyboard gimmick.

- **Target Users:**  
  People who enjoys rhythm game and wanted to explore new challenge.

- **Key Features:**  
  - 3 Lane, 2 Input Each: Each lane is mapped to be pressed by either key.
  - Special Break Note: A note that give more score and have an additional score from the base score.
  Making this game max score to be 101.0000%
  - Player and Obstacle: Player character in the middle of the screen that need to be moved with mouse movement.
  Move them to collect the green obstacle or avoid the red obstacle.

---

## 2. Concept

### 2.1 Background

This game was created due to the unavaliability of the game O.N.G.E.K.I. (オンゲキ) 
outside of Japan. (Persumed to be because of the gambling mechanic in the game.)
Beside, there aren't many rhythm game that utilize mouse and keyboard at the same time.


### 2.2 Objectives

The objective for this game are as follow:
- 3 Lane vertical scrolling note with 2 input for each lane.
- Player character in the middle of screen moving in x direction.
- Variety of note type and obstacle type.
- Song selection screen with difficulty selection.
- Configuration page that can edit the config file in the GUI.

---

## 3. UML Class Diagram

UML Diagram can be found [Here](./uml_diagram.pdf).

---

## 4. Object-Oriented Programming Implementation
List all classes implemented in the project with brief descriptions.

- **Config (`config.py`):** Class-level configuration store. Loads/writes `config.jsonc` (JSONC) with type coercion from `config_type.jsonc`, and provides runtime constants (timing windows, volumes, keybind names, window size, etc.).
- **SceneBase (`components/scene_base.py`):** Abstract base class for all scenes. Defines the scene lifecycle (`process_input`/`update`/`render`) and the transition API `switch_to_scene(...)` (calls `on_scene_exit()` and sets `next`).
- **JudgementLevel (`components/local_enum/judgement_level.py`):** Enum of judgement outcomes (`MISS/GOOD/GREAT/PERFECT/CRITPERFECT`) used by gameplay judgement/scoring and result rendering.

- **Song (`components/song.py`):** Song-pack model loaded from a song folder. Parses `meta.jsonc` (via JSONC parser), exposes song metadata/asset paths, and constructs `Chart` objects for each difficulty.
- **Chart (`components/chart.py`):** Difficulty/chart model that loads `.gacf` CSV rows into gameplay objects via factory maps. Provides lazily-loaded `notes` and `obstacles` lists and supports optional `forced_note_speed`.

- **Player (`components/player.py`):** Player avatar model for X-position movement bounds and health. Loads/scales the player sprite, applies mouse delta movement, applies damage/heal, and renders the sprite (including a damage-flash effect).
- **PlayData (`components/play_data.py`):** Per-round record container. Records note/obstacle judgements, score/combo progression, pressed side, sampled player X movement, and round end reason; serializes and saves a JSON result file into the song difficulty folder.
- **GameManager (`components/game_manager.py`):** Core gameplay controller. Owns `Player` and `PlayData`, manages loaded notes/obstacles, handles input judgement (including long-hold tracking), scoring updates, health changes from obstacles, and music start/fade timing.

- **NoteBase (`components/notes/note_base.py`):** Base note model loaded from chart CSV. Validates inputs, computes hit error, resolves judgements from timing windows, handles long-note hold state, and builds judgement payloads for recording/UI.
- **NormalNote (`components/notes/normal_note.py`):** Standard note subtype (tap/hold) built from `NoteBase`.
- **BreakNote (`components/notes/break_note.py`):** Special note subtype that yields additional scoring/visual behavior compared to `NormalNote`.
- **NormalStripeNote (`components/notes/normal_stripe_note.py`):** Stripe variant note subtype with distinct judgement/scoring rules.
- **BreakStripeNote (`components/notes/break_stripe_note.py`):** Stripe variant of `BreakNote`.

- **ObstacleBase (`components/obstacles/obstacle_base.py`):** Base obstacle model loaded from chart CSV. Validates inputs, supports long obstacles, draws obstacle surfaces, and provides obstacle scoring rules.
- **DamageObstacle (`components/obstacles/damage_obstacle.py`):** Obstacle subtype representing a damaging obstacle (red).
- **CollectObstacle (`components/obstacles/collect_obstacle.py`):** Obstacle subtype representing a collectible/healing obstacle (green).

- **MainMenu (`scenes/main_menu.py`):** Main menu scene for navigation (Play -> `SongSelect`, Setting -> `Setting`, Exit -> quit).
- **SongSelect (`scenes/song_select.py`):** Song browser scene. Loads songs, filters hidden ones, supports sorting and difficulty selection, plays preview audio, shows play record overlay, and transitions into `Loading` for gameplay.
- **Loading (`scenes/loading.py`):** Pre-game loading scene. Builds a `GameManager`, displays song/chart metadata for a minimum duration, supports ESC back to `SongSelect`, then transitions to `PlaySpace`.
- **PlaySpace (`scenes/play_space.py`):** Gameplay scene. Runs the countdown/start flow, collects lane input events, updates/renders objects via `GameManager`, handles skip/death flows, and transitions to `Result`.
- **Result (`scenes/result.py`):** Result/analytics scene. Saves live `PlayData` to JSON (or displays an existing serialized record) and renders multi-tab dashboards (including matplotlib graphs).
- **SettingItem (`scenes/setting.py`):** Dataclass representing one configurable setting row (key/label/section/type/value/control metadata) used by the settings UI.
- **Setting (`scenes/setting.py`):** Settings scene. Provides a GUI for editing `Config` values (toggle/slider/text/number), validates lane-key conflicts, saves via `Config.write_config()`, reloads config, and returns to `MainMenu`.

---

## 5. Statistical Data

### 5.1 Data Recording Method
Data are recorded in the PlayData class. After finishing the game, a json file will be created for viewing another time.
(Located at `.\data\<song>\<difficulty>\*.json`)

### 5.2 Data Features
Describe the characteristics of the data used in your system.

|     Data Name      | Explaination | Key |
|:------------------:|:-------------|-----|
|     Hit Error      | Record how off the player input were compared to the actual note time | recorded_note_hit.hit_error |
| Judgement of Note  | Record the judgement level of each note | recorded_note_hit.judgement_level |
|       Combo        | Record how many non-miss note there were in a streak | recorded_note_hit.current_combo |
| Left & Right Input | Record whether the note were pressed with left or right key | recorded_note_hit.pressed_side |
| Player X Position | Record player X position in an interval to see how player move over time | recorded_player_x |

---

## 6. External Sources

1. Scene Manager Template, https://nerdparadise.com/programming/pygame/part7 [game source code]
2. [FeuxFollet](https://github.com/FeuxFollet) [default player image]
3. [RGredsky](https://soundcloud.com/rgredsky) [music [Enigmatic](https://soundcloud.com/rgredsky/rgredsky-enigmatic)]

