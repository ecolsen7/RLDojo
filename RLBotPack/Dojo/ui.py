import numpy as np
from enum import Enum
import keyboard

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
from scenario import Scenario, OffensiveMode, DefensiveMode
import utils

class CustomUpDownSelection(Enum):
    Y = 1
    Z = 2
    PITCH = 3

class CustomLeftRightSelection(Enum):
    X = 1
    YAW = 2
    ROLL = 3

class DojoUI():
    def __init__(self):
        self.up_down_selection = CustomUpDownSelection.Y
        self.left_right_selection = CustomLeftRightSelection.X

        # initialise reading keyboard for menu selection
        keyboard.add_hotkey('m', self.menu_toggle)
        keyboard.add_hotkey('0', self.clear_score)
        keyboard.add_hotkey('1', self.mirror_toggle)
        keyboard.add_hotkey('o', self.cycle_offensive_mode)
        keyboard.add_hotkey('d', self.cycle_defensive_mode)
        keyboard.add_hotkey('f', self.freeze_scenario_toggle)
        keyboard.add_hotkey('c', self.create_custom_mode)
        keyboard.add_hotkey('left', self.left_handler)
        keyboard.add_hotkey('right', self.right_handler)
        keyboard.add_hotkey('down', self.down_handler)
        keyboard.add_hotkey('up', self.up_handler)
        keyboard.add_hotkey('n', self.next_custom_step)
        keyboard.add_hotkey('b', self.prev_custom_step)
        keyboard.add_hotkey('x', self.custom_select_x)
        keyboard.add_hotkey('y', self.custom_select_y)
        keyboard.add_hotkey('z', self.custom_select_z)
        keyboard.add_hotkey('p', self.custom_select_pitch)
        keyboard.add_hotkey('y', self.custom_select_yaw)
        keyboard.add_hotkey('r', self.custom_select_roll)
        keyboard.add_hotkey('+', self.increase_velocity)
        keyboard.add_hotkey('-', self.decrease_velocity)
