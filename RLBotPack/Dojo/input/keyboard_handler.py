import keyboard
from typing import Callable, Dict, Any
from state.game_state import DojoGameState, CustomUpDownSelection, CustomLeftRightSelection, CUSTOM_MODES


class KeyboardHandler:
    """Handles all keyboard input for the Dojo application"""
    
    def __init__(self, game_state: DojoGameState):
        self.game_state = game_state
        self.callbacks: Dict[str, Callable] = {}
        self._setup_hotkeys()
    
    def register_callback(self, action: str, callback: Callable):
        """Register a callback for a specific action"""
        self.callbacks[action] = callback
    
    def _setup_hotkeys(self):
        """Set up all keyboard hotkeys"""
        keyboard.add_hotkey('m', self._menu_toggle)
        keyboard.add_hotkey('left', self._left_handler)
        keyboard.add_hotkey('right', self._right_handler)
        keyboard.add_hotkey('down', self._down_handler)
        keyboard.add_hotkey('up', self._up_handler)
        keyboard.add_hotkey('n', self._next_custom_step)
        keyboard.add_hotkey('b', self._prev_custom_step)
        keyboard.add_hotkey('x', self._custom_select_x)
        keyboard.add_hotkey('y', self._custom_select_y)
        keyboard.add_hotkey('z', self._custom_select_z)
        keyboard.add_hotkey('p', self._custom_select_pitch)
        keyboard.add_hotkey('Y', self._custom_select_yaw)
        keyboard.add_hotkey('r', self._custom_select_roll)
        keyboard.add_hotkey('v', self._custom_select_velocity)
        keyboard.add_hotkey('enter', self._enter_handler)
    
    def _menu_toggle(self):
        """Handle menu toggle"""
        if 'menu_toggle' in self.callbacks:
            self.callbacks['menu_toggle']()
    
    def _down_handler(self):
        """Handle down arrow key"""
        if self.game_state.is_in_custom_mode():
            if 'custom_down' in self.callbacks:
                self.callbacks['custom_down']()
        else:
            if 'menu_down' in self.callbacks:
                self.callbacks['menu_down']()
    
    def _up_handler(self):
        """Handle up arrow key"""
        if self.game_state.is_in_custom_mode():
            if 'custom_up' in self.callbacks:
                self.callbacks['custom_up']()
        else:
            if 'menu_up' in self.callbacks:
                self.callbacks['menu_up']()
    
    def _left_handler(self):
        """Handle left arrow key"""
        if self.game_state.is_in_custom_mode():
            if 'custom_left' in self.callbacks:
                self.callbacks['custom_left']()
        else:
            if 'menu_left' in self.callbacks:
                self.callbacks['menu_left']()
    
    def _right_handler(self):
        """Handle right arrow key"""
        if self.game_state.is_in_custom_mode():
            if 'custom_right' in self.callbacks:
                self.callbacks['custom_right']()
        else:
            if 'menu_right' in self.callbacks:
                self.callbacks['menu_right']()
    
    def _enter_handler(self):
        """Handle enter key"""
        if 'enter' in self.callbacks:
            self.callbacks['enter']()
    
    def _next_custom_step(self):
        """Handle next custom step"""
        if 'next_custom_step' in self.callbacks:
            self.callbacks['next_custom_step']()
    
    def _prev_custom_step(self):
        """Handle previous custom step"""
        if 'prev_custom_step' in self.callbacks:
            self.callbacks['prev_custom_step']()
    
    def _custom_select_x(self):
        """Select X coordinate for custom mode"""
        self.game_state.custom_leftright_selection = CustomLeftRightSelection.X
    
    def _custom_select_y(self):
        """Select Y coordinate for custom mode"""
        self.game_state.custom_updown_selection = CustomUpDownSelection.Y
    
    def _custom_select_z(self):
        """Select Z coordinate for custom mode"""
        self.game_state.custom_updown_selection = CustomUpDownSelection.Z
    
    def _custom_select_pitch(self):
        """Select pitch for custom mode"""
        self.game_state.custom_updown_selection = CustomUpDownSelection.PITCH
    
    def _custom_select_yaw(self):
        """Select yaw for custom mode"""
        self.game_state.custom_leftright_selection = CustomLeftRightSelection.YAW
    
    def _custom_select_roll(self):
        """Select roll for custom mode"""
        self.game_state.custom_leftright_selection = CustomLeftRightSelection.ROLL
    
    def _custom_select_velocity(self):
        """Select velocity for custom mode"""
        self.game_state.custom_updown_selection = CustomUpDownSelection.VELOCITY
    
    def cleanup(self):
        """Clean up keyboard handlers"""
        keyboard.unhook_all() 
