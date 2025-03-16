import numpy as np
from enum import Enum
import keyboard

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
from scenario import Scenario, OffensiveMode, DefensiveMode
import utils

units_x_per_char = 10
units_y_per_line = 20

class UIElement():
    ''' Each element consist of a text and a function to call when the element is clicked '''
    def __init__(self, text, function):
        self.text = text
        self.function = function
        self.selected = False

class MenuRenderer():
    def __init__(self, renderer):
        self.renderer = renderer
        self.elements = []

    def add_element(self, element):
        self.elements.append(element)

    def render_menu(self):
        # Draw a rectangle around the menu
        MENU_START_X = 20
        MENU_START_Y = 400
        MENU_WIDTH = 500
        MENU_HEIGHT = 500
        self.renderer.draw_rect_2d(MENU_START_X, MENU_START_Y, MENU_WIDTH, MENU_HEIGHT, False, self.renderer.black())
        print_x = MENU_START_X + 10
        print_y = MENU_START_Y + 10
        for element in self.elements:
            self.renderer.draw_text(element.text, print_x, print_y)
            print_y += units_y_per_line
        
