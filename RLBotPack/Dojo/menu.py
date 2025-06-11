import numpy as np
from enum import Enum
import keyboard

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
from scenario import Scenario, OffensiveMode, DefensiveMode
import utils

units_x_per_char = 11
units_y_per_line = 40

class UIElement():
    ''' Each element consist of a text and a function to call when the element is clicked '''
    def __init__(self, text, function=None, function_args=None, submenu=None, header=False):
        self.text = text
        self.function = function
        self.function_args = function_args
        self.selected = False
        self.entered = False
        self.submenu = submenu
        self.header = header

    def back(self):
        self.entered = False

class MenuRenderer():
    def __init__(self, renderer, columns=1):
        self.renderer = renderer
        # Each column has its own list of elements
        self.elements = [[] for _ in range(columns)]
        self.columns = columns
        self.active_column = 0
        # Add scroll offset for each column to handle long lists
        self.scroll_offset = [0 for _ in range(columns)]

    def add_element(self, element, column=0):
        self.elements[column].append(element)
        # if column == 0 and len(self.elements[column]) == 1:
        #     self.elements[column][0].selected = True

    def _get_max_visible_elements(self):
        """Calculate maximum number of elements that can fit in the menu"""
        MENU_HEIGHT = 500
        available_height = MENU_HEIGHT - 20  # Account for padding
        return available_height // units_y_per_line

    def _ensure_selected_visible(self):
        """Ensure the selected element is visible by adjusting scroll offset"""
        max_visible = self._get_max_visible_elements()
        
        # Find selected element index
        selected_index = -1
        for index, element in enumerate(self.elements[self.active_column]):
            if element.selected:
                selected_index = index
                break
        
        if selected_index == -1:
            return
        
        # Adjust scroll offset to keep selected element visible
        if selected_index < self.scroll_offset[self.active_column]:
            # Selected element is above visible area
            self.scroll_offset[self.active_column] = selected_index
        elif selected_index >= self.scroll_offset[self.active_column] + max_visible:
            # Selected element is below visible area
            self.scroll_offset[self.active_column] = selected_index - max_visible + 1

    def select_next_element(self):
        # If an element is currently entered, call its select_next_element function
        for element in self.elements[self.active_column]:
            if element.entered:
                element.submenu.select_next_element()
                return
        for index, element in enumerate(self.elements[self.active_column]):
            if element.selected:
                element.selected = False
                if index < len(self.elements[self.active_column]) - 1:
                    self.elements[self.active_column][index + 1].selected = True
                else:
                    if not self.elements[self.active_column][0].header:
                        self.elements[self.active_column][0].selected = True
                    else:
                        self.elements[self.active_column][1].selected = True
                break
        self._ensure_selected_visible()

    def select_last_element(self):
        # If an element is currently entered, call its select_last_element function
        for element in self.elements[self.active_column]:
            if element.entered:
                element.submenu.select_last_element()
                return
        for index, element in enumerate(self.elements[self.active_column]):
            if element.selected:
                element.selected = False
                if index > 0:
                    if not self.elements[self.active_column][index - 1].header:
                        self.elements[self.active_column][index - 1].selected = True
                    else:
                        if index == 1:
                            self.elements[self.active_column][len(self.elements[self.active_column]) - 1].selected = True
                        else:
                            self.elements[self.active_column][index - 2].selected = True
                else:
                    self.elements[self.active_column][len(self.elements[self.active_column]) - 1].selected = True
                break
        self._ensure_selected_visible()

    def move_to_next_column(self):
        print("move_to_next_column")
        for column in range(self.columns):
            for element in self.elements[column]:
                if element.entered:
                    print("moving to next column in submenu: ", element)
                    element.submenu.move_to_next_column()
                    return
        prev_column = self.active_column
        self.active_column += 1
        if self.active_column >= self.columns:
            self.active_column = 0

        # Update selected element
        for index, element in enumerate(self.elements[prev_column]):
            if element.selected:
                if index < len(self.elements[self.active_column]):
                    self.elements[self.active_column][index].selected = True
                else:
                    self.elements[self.active_column][len(self.elements[self.active_column]) - 1].selected = True
                element.selected = False
                break
        print(self.active_column)

    def move_to_prev_column(self):
        for column in range(self.columns):
            for element in self.elements[column]:
                if element.entered:
                    element.submenu.move_to_prev_column()
                    return
        prev_column = self.active_column
        self.active_column -= 1
        if self.active_column < 0:
            self.active_column = self.columns - 1

        # Update selected element
        for index, element in enumerate(self.elements[prev_column]):
            if element.selected:
                if index < len(self.elements[self.active_column]):
                    self.elements[self.active_column][index].selected = True
                else:
                    self.elements[self.active_column][len(self.elements[self.active_column]) - 1].selected = True
                element.selected = False
                break

    def enter_element(self):
        # If an element is currently entered, call its enter_element function
        for element in self.elements[self.active_column]:
            if element.entered:
                element.submenu.enter_element()
                return
        for element in self.elements[self.active_column]:
            if element.selected:
                if element.submenu:
                    element.entered = True
                elif element.function:
                    print("entering element: ", element)
                    if element.function_args:
                        element.function(element.function_args)
                    else:
                        element.function()
                break

    def handle_back_key(self):
        """Handle the 'b' key press to go back in menus"""
        # Check if any element in any column is entered
        for column in range(self.columns):
            for element in self.elements[column]:
                if element.entered:
                    element.back()
                    return True
        return False

    def render_menu(self):
        # If no elements are selected the first time we render the menu, select the first non-header element
        if not any(element.selected for element in self.elements[self.active_column]):
            for element in self.elements[self.active_column]:
                if not element.header:
                    element.selected = True
                    break

        # First, check if any submenu is entered
        for element in self.elements[self.active_column]:
            if element.entered:
                element.submenu.render_menu()
                return

        # Ensure selected element is visible
        self._ensure_selected_visible()

        # Draw a rectangle around the menu
        MENU_START_X = 20
        MENU_START_Y = 400
        MENU_WIDTH = 500
        MENU_HEIGHT = 500
        COLUMN_WIDTH = MENU_WIDTH / self.columns
        max_visible_elements = self._get_max_visible_elements()
        
        self.renderer.begin_rendering()
        self.renderer.draw_rect_2d(MENU_START_X, MENU_START_Y, MENU_WIDTH, MENU_HEIGHT, False, self.renderer.black())
        print_x = MENU_START_X + 10
        print_y = MENU_START_Y + 10
        text_color = self.renderer.white()

        # Then, render the menu
        for column in range(self.columns):
            print_x = MENU_START_X + COLUMN_WIDTH * column + 10
            print_y = MENU_START_Y + 10
            
            # Calculate which elements to show based on scroll offset
            start_index = self.scroll_offset[column]
            end_index = min(start_index + max_visible_elements, len(self.elements[column]))
            
            # Render only visible elements
            for i in range(start_index, end_index):
                element = self.elements[column][i]
                
                # If header, draw a smaller rectangle
                if element.header:
                    self.renderer.draw_rect_2d(print_x, print_y - 10, len(element.text) * units_x_per_char, units_y_per_line, False, self.renderer.blue())
                # If selected, draw a rectangle around the element
                if element.selected:
                    self.renderer.draw_rect_2d(print_x, print_y - 10, len(element.text) * units_x_per_char, units_y_per_line, False, self.renderer.white())
                    color = self.renderer.black()
                else:
                    color = text_color
                # If header, draw text in green
                if element.header:
                    self.renderer.draw_string_2d(print_x + 5, print_y, 1, 1, element.text, self.renderer.white())
                else:
                    self.renderer.draw_string_2d(print_x + 5, print_y, 1, 1, element.text, color)
                print_y += units_y_per_line
            
            # Draw scroll indicators if needed
            if len(self.elements[column]) > max_visible_elements:
                # Draw scroll up indicator
                if self.scroll_offset[column] > 0:
                    indicator_x = print_x + COLUMN_WIDTH - 30
                    indicator_y = MENU_START_Y + 10
                    self.renderer.draw_string_2d(indicator_x, indicator_y, 1, 1, "↑", self.renderer.white())
                
                # Draw scroll down indicator
                if end_index < len(self.elements[column]):
                    indicator_x = print_x + COLUMN_WIDTH - 30
                    indicator_y = MENU_START_Y + MENU_HEIGHT - 30
                    self.renderer.draw_string_2d(indicator_x, indicator_y, 1, 1, "↓", self.renderer.white())

        # Draw the back instruction at the bottom of the menu
        back_text = "Press 'b' to go back"
        back_x = MENU_START_X + (MENU_WIDTH - len(back_text) * units_x_per_char) // 2
        back_y = MENU_START_Y + MENU_HEIGHT - 30
        self.renderer.draw_string_2d(back_x, back_y, 1, 1, back_text, self.renderer.white())
        
        self.renderer.end_rendering()
