import numpy as np
import keyboard
import string
from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator

# Import our new modular components
from state.game_state import DojoGameState, GymMode, ScenarioPhase, RacePhase, CarIndex, CUSTOM_MODES, CustomUpDownSelection, CustomLeftRightSelection
from game_modes import ScenarioMode, RaceMode
from rendering import UIRenderer
from menu import MenuRenderer, UIElement
from scenario import Scenario, OffensiveMode, DefensiveMode
from config.constants import DEFAULT_TRIAL_OPTIONS, DEFAULT_NUM_TRIALS, DEFAULT_PAUSE_TIME
import modifier
import utils
from record.race import RaceRecord, RaceRecords, get_race_records
from custom_playlist import CustomPlaylistManager
from playlist import PlaylistRegistry, PlayerRole

class Dojo(BaseScript):
    """
    Dojo training application for RLBot.
    
    A modular training system with multiple game modes:
    - Scenario-based training with offensive and defensive modes
    - Race mode for speed training
    - Custom sandbox mode for creating scenarios
    - Menu system for easy configuration
    """
    
    def __init__(self):
        super().__init__("Dojo")
        
        # Initialize core components
        self.game_state = DojoGameState()
        self.ui_renderer = None  # Will be initialized after renderer is available
        
        # Game modes
        self.scenario_mode = None
        self.race_mode = None
        self.current_mode = None
        
        # Menu system
        self.menu_renderer = None
        self.preset_mode_menu = None
        self.race_mode_menu = None
        self.playlist_menu = None
        
        # Custom playlist manager
        self.custom_playlist_manager = None
        self.playlist_registry = None  # Will be initialized after game interface is available
        
        # Internal state
        self.rlbot_game_state = None
        
    def run(self):
        """Main game loop"""
        while True:
            # Wait for and get the game tick packet
            packet = self.wait_game_tick_packet()
            packet = self.get_game_tick_packet()
            
            # Update game state
            self._update_game_state(packet)
            
            # Initialize components on first tick
            if self.game_state.ticks == 1:
                self._initialize_components()
            
            # Update current game mode
            if self.current_mode:
                self.current_mode.update(packet)
            
            # Render UI
            self._render_ui()
    
    def _update_game_state(self, packet):
        """Update the game state with packet information"""
        self.game_state.cur_time = packet.game_info.seconds_elapsed
        self.game_state.ticks += 1
        # self.game_state.paused = packet.game_info.paused
        self.game_state.paused = False
        
        # Check for disable goal reset mutator on first tick
        if self.game_state.ticks == 1:
            match_settings = self.get_match_settings()
            mutators = match_settings.MutatorSettings()
            if mutators.RespawnTimeOption() == 3:
                self.game_state.disable_goal_reset = True
    
    def _initialize_components(self):
        """Initialize all components that require the game interface"""
        
        # Initialize UI renderer
        self.ui_renderer = UIRenderer(self.game_interface.renderer, self.game_state)
        
        # Initialize custom playlist manager and playlist registry
        self.custom_playlist_manager = CustomPlaylistManager(renderer=self.game_interface.renderer, main_menu_renderer=self.menu_renderer)
        self.playlist_registry = PlaylistRegistry(self.game_interface.renderer)
        self.playlist_registry.set_custom_playlist_manager(self.custom_playlist_manager)
        
        # Initialize game modes
        self.scenario_mode = ScenarioMode(self.game_state, self.game_interface)
        self.race_mode = RaceMode(self.game_state, self.game_interface)
        self.current_mode = self.scenario_mode
        
        # Set up custom playlist manager with scenario mode
        self.scenario_mode.set_playlist_registry(self.playlist_registry)
        
        # Initialize menu system
        self._setup_menus()
        
        self.custom_playlist_manager.main_menu_renderer = self.menu_renderer
        
        # Set up keyboard handlers
        self._setup_keyboard_handlers()
        
        # Set initial pause time
        self.game_state.pause_time = DEFAULT_PAUSE_TIME
    
    def _setup_menus(self):
        """Set up all menu systems"""
        # Main menu
        self.menu_renderer = MenuRenderer(self.game_interface.renderer)
        self.menu_renderer.is_root = True
        self.menu_renderer.add_element(UIElement('Main Menu', header=True))
        self.menu_renderer.add_element(UIElement('Reset Score', function=self._clear_score))
        self.menu_renderer.add_element(UIElement('Freeze Scenario', function=self._toggle_freeze_scenario))
        self.menu_renderer.add_element(UIElement('Create Custom Mode', function=self._create_custom_mode))
        
        # Playlist menu
        self.playlist_menu = self.create_playlist_menu()
        self.menu_renderer.add_element(UIElement('Select Playlist', submenu=self.playlist_menu, submenu_refresh_function=self.create_playlist_menu))
        
        # Custom playlist creation menu
        if self.custom_playlist_manager:
            custom_playlist_menu = self.custom_playlist_manager.create_playlist_creation_menu()
            self.menu_renderer.add_element(UIElement('Create Custom Playlist', submenu=custom_playlist_menu))
        
        # Preset mode menu
        self.preset_mode_menu = MenuRenderer(self.game_interface.renderer, columns=3)
        self.preset_mode_menu.add_element(UIElement('Offensive Mode', header=True), column=0)
        for mode in OffensiveMode:
            self.preset_mode_menu.add_element(
                UIElement(mode.name, function=self._select_offensive_mode, function_args=mode, chooseable=True), 
                column=0
            )
        self.preset_mode_menu.add_element(UIElement('Defensive Mode', header=True), column=1)
        for mode in DefensiveMode:
            self.preset_mode_menu.add_element(
                UIElement(mode.name, function=self._select_defensive_mode, function_args=mode, chooseable=True), 
                column=1
            )
        # Third column for player role
        self.preset_mode_menu.add_element(UIElement('Player Role', header=True), column=2)
        self.preset_mode_menu.add_element(UIElement('Offense', function=self._set_player_role, function_args=PlayerRole.OFFENSE, chooseable=True), column=2)
        self.preset_mode_menu.add_element(UIElement('Defense', function=self._set_player_role, function_args=PlayerRole.DEFENSE, chooseable=True), column=2)
        self.preset_mode_menu.add_element(UIElement('', header=True), column=2)  # Spacer
        self.preset_mode_menu.add_element(UIElement('Confirm Scenario', function=self._handle_back), column=2)
        self.menu_renderer.add_element(UIElement('Select Preset Mode', submenu=self.preset_mode_menu))
        
        # Race mode menu
        self.race_mode_menu = MenuRenderer(self.game_interface.renderer)
        self.race_mode_menu.add_element(UIElement('Number of Trials', header=True))
        for option in DEFAULT_TRIAL_OPTIONS:
            self.race_mode_menu.add_element(
                UIElement(str(option), function=self._set_race_mode, function_args=option)
            )
        self.menu_renderer.add_element(UIElement('Race Mode', submenu=self.race_mode_menu))
    
    def _setup_keyboard_handlers(self):
        """Set up all keyboard hotkeys"""
        keyboard.add_hotkey('m', self._toggle_menu)
        keyboard.add_hotkey('left', self._handle_left)
        keyboard.add_hotkey('right', self._handle_right)
        keyboard.add_hotkey('down', self._handle_down)
        keyboard.add_hotkey('up', self._handle_up)
        keyboard.add_hotkey('n', self._next_custom_step)
        keyboard.add_hotkey('b', self._handle_back)
        keyboard.add_hotkey('x', self._custom_select_x)
        keyboard.add_hotkey('y', self._custom_select_y)
        keyboard.add_hotkey('z', self._custom_select_z)
        keyboard.add_hotkey('p', self._custom_select_pitch)
        keyboard.add_hotkey('Y', self._custom_select_yaw)
        keyboard.add_hotkey('r', self._custom_select_roll)
        keyboard.add_hotkey('v', self._custom_select_velocity)
        keyboard.add_hotkey('enter', self._enter_handler)
        
        # For all other letters, submit the letter as a text input
        for letter in string.ascii_lowercase:
            self._add_hotkey_with_arg(letter, self._handle_text_input, letter)
            
        # Also allow underscores and dashes in text input
        self._add_hotkey_with_arg('_', self._handle_text_input, '_')
        self._add_hotkey_with_arg('-', self._handle_text_input, '-')
        
        # Allow backspace in text input
        keyboard.add_hotkey('backspace', self._handle_text_backspace)
        
    ### Keyboard handler utilities 
    def _add_hotkey_with_arg(self, hotkey, function, function_args):
        def wrapper():
            function(function_args)
        keyboard.add_hotkey(hotkey, wrapper)

    ### Keyboard handlers
    def _enter_handler(self):
        """Handle enter key"""
        if self.menu_renderer.is_in_text_input_mode():
            self._complete_text_input()
        else:
            self._enter_menu_element()

    def _enter_menu_element(self):
        """Enter the currently selected menu element"""
        if self.menu_renderer.is_in_text_input_mode():
            return
        
        self.menu_renderer.enter_element()

    def _complete_text_input(self):
        """Complete text input"""
        if not self.menu_renderer.is_in_text_input_mode():
            print(f"Not in text input mode, ignoring enter")
            return
        
        self.menu_renderer.complete_text_input()
        self.menu_renderer.handle_back_key()

    def _handle_left(self):
        """Handle left arrow key"""
        if self.game_state.is_in_custom_mode():
            self._custom_left_handler()
        else:
            self.menu_renderer.move_to_prev_column()

    def _handle_right(self):
        """Handle right arrow key"""
        if self.game_state.is_in_custom_mode():
            self._custom_right_handler()
        else:
            self.menu_renderer.move_to_next_column()

    def _handle_down(self):
        """Handle down arrow key"""
        if self.game_state.is_in_custom_mode():
            self._custom_down_handler()
        else:
            self.menu_renderer.select_next_element()

    def _handle_up(self):
        """Handle up arrow key"""
        if self.game_state.is_in_custom_mode():
            self._custom_up_handler()
        else:
            self.menu_renderer.select_last_element()

    def _handle_back(self):
        """Handle back key - either for menu navigation or custom mode"""
        # If in text input mode, no-op
        if self.menu_renderer.is_in_text_input_mode():
            return
        
        if self.game_state.is_in_custom_mode():
            self._prev_custom_step()
        else:
            self.menu_renderer.handle_back_key()

    def _custom_select_x(self):
        """Select X coordinate for custom mode"""
        # If in text input mode, no-op
        if self.menu_renderer.is_in_text_input_mode():
            return
            
        self.game_state.custom_leftright_selection = CustomLeftRightSelection.X

    def _custom_select_y(self):
        """Select Y coordinate for custom mode"""
        # If in text input mode, no-op
        if self.menu_renderer.is_in_text_input_mode():
            return
        
        self.game_state.custom_updown_selection = CustomUpDownSelection.Y

    def _custom_select_z(self):
        """Select Z coordinate for custom mode"""
        # If in text input mode, no-op
        if self.menu_renderer.is_in_text_input_mode():
            return
        
        self.game_state.custom_updown_selection = CustomUpDownSelection.Z

    def _custom_select_pitch(self):
        """Select pitch for custom mode"""
        # If in text input mode, no-op
        if self.menu_renderer.is_in_text_input_mode():
            return
        
        self.game_state.custom_updown_selection = CustomUpDownSelection.PITCH

    def _custom_select_yaw(self):
        """Select yaw for custom mode"""
        # If in text input mode, no-op
        if self.menu_renderer.is_in_text_input_mode():
            return
        
        self.game_state.custom_leftright_selection = CustomLeftRightSelection.YAW

    def _custom_select_roll(self):
        """Select roll for custom mode"""
        # If in text input mode, no-op
        if self.menu_renderer.is_in_text_input_mode():
            return
        
        self.game_state.custom_leftright_selection = CustomLeftRightSelection.ROLL

    def _custom_select_velocity(self):
        """Select velocity for custom mode"""
        # If in text input mode, no-op
        if self.menu_renderer.is_in_text_input_mode():
            return
        
        self.game_state.custom_updown_selection = CustomUpDownSelection.VELOCITY

    def _handle_text_backspace(self):
        """Handle backspace in text input"""
        if not self.menu_renderer.is_in_text_input_mode():
            print(f"Not in text input mode, ignoring backspace")
            return
        
        self.menu_renderer.handle_text_backspace()

    def _handle_text_input(self, key):
        """Handle text input if in text input mode"""
        if not self.menu_renderer.is_in_text_input_mode():
            print(f"Not in text input mode, ignoring key: {key}")
            return
        
        self.menu_renderer.handle_text_input(key)

    def _render_ui(self):
        """Render all UI elements"""
        if self.ui_renderer:
            # Render main UI
            self.ui_renderer.render_main_ui()
            
            # Render custom sandbox UI if in custom mode
            if self.game_state.is_in_custom_mode():
                rlbot_game_state = None
                if hasattr(self.current_mode, 'get_rlbot_game_state'):
                    rlbot_game_state = self.current_mode.get_rlbot_game_state()
                self.ui_renderer.render_custom_sandbox_ui(rlbot_game_state)
            
            # Render menu if in menu mode
            if self.game_state.game_phase in [ScenarioPhase.MENU, RacePhase.MENU]:
                self.menu_renderer.render_menu()
    
    # Menu action handlers
    def _clear_score(self):
        """Clear both human and bot scores"""
        self.game_state.clear_score()
    
    def _toggle_mirror(self):
        """Toggle mirror mode"""
        self.game_state.toggle_mirror()
        if self.game_state.game_phase != ScenarioPhase.MENU:
            self.game_state.game_phase = ScenarioPhase.SETUP
        elif hasattr(self.current_mode, '_set_next_game_state'):
            self.current_mode._set_next_game_state()
    
    def _toggle_freeze_scenario(self):
        """Toggle scenario freezing"""
        self.game_state.toggle_freeze_scenario()
    
    def _create_custom_mode(self):
        """Enter custom mode creation"""
        self.game_state.game_phase = ScenarioPhase.CUSTOM_OFFENSE
    
    def _select_offensive_mode(self, mode):
        """Select offensive mode"""
        print(f"Selecting offensive mode: {mode}")
        self.game_state.offensive_mode = mode
        if self.game_state.game_phase != ScenarioPhase.MENU:
            self.game_state.game_phase = ScenarioPhase.SETUP
        elif hasattr(self.current_mode, '_set_next_game_state'):
            self.current_mode._set_next_game_state()
    
    def _select_defensive_mode(self, mode):
        """Select defensive mode"""
        print(f"Selecting defensive mode: {mode}")
        self.game_state.defensive_mode = mode
        if self.game_state.game_phase != ScenarioPhase.MENU:
            self.game_state.game_phase = ScenarioPhase.SETUP
        elif hasattr(self.current_mode, '_set_next_game_state'):
            self.current_mode._set_next_game_state()
            
    def _set_player_role(self, role):
        """Set the player role"""
        if role == PlayerRole.OFFENSE:
            self.game_state.mirrored = True
        else:
            self.game_state.mirrored = False
        if hasattr(self.current_mode, '_set_next_game_state'):
            self.current_mode._set_next_game_state()
    
    def _set_race_mode(self, trials):
        """Set race mode with specified number of trials"""
        print(f"Setting race mode with {trials} trials")
        self.game_state.gym_mode = GymMode.RACE
        self.game_state.game_phase = RacePhase.INIT
        self.game_state.num_trials = trials
        self.game_state.race_mode_records = get_race_records()
        
        # Switch to race mode
        if self.current_mode:
            self.current_mode.cleanup()
        self.current_mode = self.race_mode
    
    def _toggle_menu(self):
        """Toggle menu visibility"""
        if self.game_state.gym_mode == GymMode.RACE:
            if self.game_state.game_phase == RacePhase.MENU:
                self.game_state.game_phase = RacePhase.EXITING_MENU
            else:
                self.game_state.game_phase = RacePhase.MENU
        elif self.game_state.gym_mode == GymMode.SCENARIO:
            if self.game_state.game_phase == ScenarioPhase.MENU:
                self.game_state.game_phase = ScenarioPhase.EXITING_MENU
            else:
                self.game_state.game_phase = ScenarioPhase.MENU
    
    # Custom mode handlers
    def _custom_down_handler(self):
        """Handle down input in custom mode"""
        object_to_modify = self._get_custom_object_to_modify()
        if not object_to_modify:
            return
        
        if self.game_state.custom_updown_selection.name == 'Y':
            modifier.modify_object_y(object_to_modify, -100)
        elif self.game_state.custom_updown_selection.name == 'Z':
            modifier.modify_object_z(object_to_modify, -100)
        elif self.game_state.custom_updown_selection.name == 'PITCH':
            modifier.modify_pitch(object_to_modify, 0.1)
        elif self.game_state.custom_updown_selection.name == 'VELOCITY':
            modifier.modify_velocity(object_to_modify, -0.1)
        
        # Update the game state
        if hasattr(self.current_mode, 'get_rlbot_game_state'):
            rlbot_game_state = self.current_mode.get_rlbot_game_state()
            if rlbot_game_state:
                self.game_interface.set_game_state(rlbot_game_state)
    
    def _custom_up_handler(self):
        """Handle up input in custom mode"""
        object_to_modify = self._get_custom_object_to_modify()
        if not object_to_modify:
            return
        
        if self.game_state.custom_updown_selection.name == 'Y':
            modifier.modify_object_y(object_to_modify, 100)
        elif self.game_state.custom_updown_selection.name == 'Z':
            modifier.modify_object_z(object_to_modify, 100)
        elif self.game_state.custom_updown_selection.name == 'PITCH':
            modifier.modify_pitch(object_to_modify, -0.1)
        elif self.game_state.custom_updown_selection.name == 'VELOCITY':
            modifier.modify_velocity(object_to_modify, 0.1)
        
        # Update the game state
        if hasattr(self.current_mode, 'get_rlbot_game_state'):
            rlbot_game_state = self.current_mode.get_rlbot_game_state()
            if rlbot_game_state:
                self.game_interface.set_game_state(rlbot_game_state)
    
    def _custom_left_handler(self):
        """Handle left input in custom mode"""
        object_to_modify = self._get_custom_object_to_modify()
        if not object_to_modify:
            return
        
        if self.game_state.custom_leftright_selection.name == 'X':
            modifier.modify_object_x(object_to_modify, -100)
        elif self.game_state.custom_leftright_selection.name == 'YAW':
            modifier.modify_yaw(object_to_modify, -0.1)
        elif self.game_state.custom_leftright_selection.name == 'ROLL':
            modifier.modify_roll(object_to_modify, -0.1)
        
        # Update the game state
        if hasattr(self.current_mode, 'get_rlbot_game_state'):
            rlbot_game_state = self.current_mode.get_rlbot_game_state()
            if rlbot_game_state:
                self.game_interface.set_game_state(rlbot_game_state)
    
    def _custom_right_handler(self):
        """Handle right input in custom mode"""
        object_to_modify = self._get_custom_object_to_modify()
        if not object_to_modify:
            return
        
        if self.game_state.custom_leftright_selection.name == 'X':
            modifier.modify_object_x(object_to_modify, 100)
        elif self.game_state.custom_leftright_selection.name == 'YAW':
            modifier.modify_yaw(object_to_modify, 0.1)
        elif self.game_state.custom_leftright_selection.name == 'ROLL':
            modifier.modify_roll(object_to_modify, 0.1)
        
        # Update the game state
        if hasattr(self.current_mode, 'get_rlbot_game_state'):
            rlbot_game_state = self.current_mode.get_rlbot_game_state()
            if rlbot_game_state:
                self.game_interface.set_game_state(rlbot_game_state)
    
    def _get_custom_object_to_modify(self):
        """Get the object to modify based on current custom phase"""
        rlbot_game_state = None
        if hasattr(self.current_mode, 'get_rlbot_game_state'):
            rlbot_game_state = self.current_mode.get_rlbot_game_state()
        
        if not rlbot_game_state:
            return None
        
        if self.game_state.game_phase == ScenarioPhase.CUSTOM_OFFENSE:
            return rlbot_game_state.cars.get(CarIndex.HUMAN.value)
        elif self.game_state.game_phase == ScenarioPhase.CUSTOM_BALL:
            return rlbot_game_state.ball
        elif self.game_state.game_phase == ScenarioPhase.CUSTOM_DEFENSE:
            return rlbot_game_state.cars.get(CarIndex.BOT.value)
        return None
    
    def _next_custom_step(self):
        """Move to next step in custom mode creation"""
        if self.game_state.game_phase == ScenarioPhase.CUSTOM_OFFENSE:
            self.game_state.game_phase = ScenarioPhase.CUSTOM_BALL
        elif self.game_state.game_phase == ScenarioPhase.CUSTOM_BALL:
            self.game_state.game_phase = ScenarioPhase.CUSTOM_DEFENSE
        elif self.game_state.game_phase == ScenarioPhase.CUSTOM_DEFENSE:
            # Save the custom scenario
            rlbot_game_state = None
            if hasattr(self.current_mode, 'get_rlbot_game_state'):
                rlbot_game_state = self.current_mode.get_rlbot_game_state()
            
            if rlbot_game_state:
                scenario = Scenario.FromGameState(rlbot_game_state)
                self.game_state.scenario_history.append(scenario)
                self.game_state.freeze_scenario_index = len(self.game_state.scenario_history) - 1
            self.game_state.game_phase = ScenarioPhase.MENU
    
    def _prev_custom_step(self):
        """Move to previous step in custom mode creation"""
        if self.game_state.game_phase == ScenarioPhase.CUSTOM_OFFENSE:
            self.game_state.game_phase = ScenarioPhase.MENU
        elif self.game_state.game_phase == ScenarioPhase.CUSTOM_BALL:
            self.game_state.game_phase = ScenarioPhase.CUSTOM_OFFENSE
        elif self.game_state.game_phase == ScenarioPhase.CUSTOM_DEFENSE:
            self.game_state.game_phase = ScenarioPhase.CUSTOM_BALL

    def create_playlist_menu(self):
        """Create playlist selection submenu"""
        # Refresh custom playlists to include any newly created ones
        self.playlist_registry.refresh_custom_playlists()
        
        playlist_menu = MenuRenderer(self.game_interface.renderer, columns=1)
        playlist_menu.add_element(UIElement("Select Playlist", header=True))
        
        # Add each playlist as a menu option
        for playlist_name in self.playlist_registry.list_playlists():
            print(f"Playlist name: {playlist_name}")
            print(f"Retrieved playlist: {self.playlist_registry.get_playlist(playlist_name)}")
            playlist = self.playlist_registry.get_playlist(playlist_name)
            playlist_menu.add_element(UIElement(
                f"{playlist.name}",
                function=self.set_playlist,
                function_args=playlist_name
            ))
        
        return playlist_menu
    
    def set_playlist(self, playlist_name):
        """Set the active playlist and return to game"""
        print(f"Setting playlist: {playlist_name}")
        self.scenario_mode.set_playlist(playlist_name)
        self.game_state.gym_mode = GymMode.SCENARIO
        self.game_state.game_phase = ScenarioPhase.SETUP
        
        # Switch to scenario mode if not already
        if self.current_mode != self.scenario_mode:
            if self.current_mode:
                self.current_mode.cleanup()
            self.current_mode = self.scenario_mode

    def cleanup(self):
        """Clean up keyboard handlers"""
        keyboard.unhook_all()

# Entry point
if __name__ == "__main__":
    script = Dojo()
    script.run() 
