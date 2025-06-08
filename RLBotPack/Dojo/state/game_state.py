from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
from scenario import Scenario, OffensiveMode, DefensiveMode
from record.race import RaceRecord, RaceRecords


class CustomUpDownSelection(Enum):
    Y = 1
    Z = 2
    PITCH = 3
    VELOCITY = 4


class CustomLeftRightSelection(Enum):
    X = 1
    YAW = 2
    ROLL = 3


class GymMode(Enum):
    SCENARIO = 1
    RACE = 2


class ScenarioPhase(Enum):
    INIT = -2
    PAUSED = -1
    SETUP = 0
    ACTIVE = 1
    MENU = 2
    CUSTOM_OFFENSE = 3
    CUSTOM_BALL = 4
    CUSTOM_DEFENSE = 5
    FINISHED = 6


class RacePhase(Enum):
    INIT = -1
    SETUP = 0
    ACTIVE = 1
    MENU = 2
    FINISHED = 3


class CarIndex(Enum):
    BLUE = 0
    ORANGE = 1
    HUMAN = 0
    BOT = 1


CUSTOM_MODES = [
    ScenarioPhase.CUSTOM_OFFENSE,
    ScenarioPhase.CUSTOM_BALL,
    ScenarioPhase.CUSTOM_DEFENSE
]


@dataclass
class DojoGameState:
    """Centralized game state for the Dojo application"""
    # Game mode and phase
    gym_mode: GymMode = GymMode.SCENARIO
    game_phase: ScenarioPhase = ScenarioPhase.SETUP
    
    # Scenario settings
    offensive_mode: OffensiveMode = OffensiveMode.POSSESSION
    defensive_mode: DefensiveMode = DefensiveMode.NEAR_SHADOW
    mirrored: bool = False
    freeze_scenario: bool = False
    freeze_scenario_index: int = 0
    scenario_history: List[Scenario] = None
    
    # Custom mode selections
    custom_updown_selection: CustomUpDownSelection = CustomUpDownSelection.Y
    custom_leftright_selection: CustomLeftRightSelection = CustomLeftRightSelection.X
    
    # Scores and timing
    human_score: int = 0
    bot_score: int = 0
    timeout: float = 10.0
    pause_time: float = 1.0
    cur_time: float = 0.0
    scored_time: float = 0.0
    started_time: float = 0.0
    
    # Game settings
    disable_goal_reset: bool = False
    rule_zero_mode: bool = False
    num_trials: int = 100
    race_mode_records: Optional[RaceRecords] = None
    
    # Internal state tracking
    scoreDiff_prev: int = 0
    score_human_prev: int = 0
    score_bot_prev: int = 0
    prev_ticks: int = 0
    ticks: int = 0
    paused: bool = False
    
    def __post_init__(self):
        if self.scenario_history is None:
            self.scenario_history = []
    
    def clear_score(self):
        """Reset both human and bot scores to zero"""
        self.human_score = 0
        self.bot_score = 0
    
    def toggle_mirror(self):
        """Toggle the mirrored state"""
        self.mirrored = not self.mirrored
    
    def toggle_freeze_scenario(self):
        """Toggle scenario freezing"""
        self.freeze_scenario = not self.freeze_scenario
    
    def is_in_custom_mode(self) -> bool:
        """Check if currently in any custom mode"""
        return self.game_phase in CUSTOM_MODES
    
    def get_time_since_start(self) -> tuple[int, int]:
        """Get minutes and seconds since start"""
        total_seconds = self.cur_time - self.started_time
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        return minutes, seconds 

    def get_previous_record(self) -> Optional[float]:
        if self.race_mode_records is None:
            return None
        return self.race_mode_records.get_previous_record(self.num_trials)
