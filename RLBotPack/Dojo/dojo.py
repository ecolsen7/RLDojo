import numpy as np
from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator

# Import our new modular components
from state.game_state import DojoGameState, GymMode, ScenarioPhase, RacePhase, CarIndex, CUSTOM_MODES
from game_modes import ScenarioMode, RaceMode
from input import KeyboardHandler
from rendering import UIRenderer
from menu import MenuRenderer, UIElement
from scenario import Scenario, OffensiveMode, DefensiveMode
from config.constants import DEFAULT_TRIAL_OPTIONS, DEFAULT_NUM_TRIALS, DEFAULT_PAUSE_TIME
import modifier
import utils
from record.race import RaceRecord, RaceRecords, get_race_records
from custom_playlist import CustomPlaylistManager

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
        self.keyboard_handler = KeyboardHandler(self.game_state)
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
        
        # Initialize custom playlist manager
        self.custom_playlist_manager = CustomPlaylistManager(self.game_interface.renderer)
        
        # Initialize game modes
        self.scenario_mode = ScenarioMode(self.game_state, self.game_interface)
        self.race_mode = RaceMode(self.game_state, self.game_interface)
        self.current_mode = self.scenario_mode
        
        # Set up custom playlist manager with scenario mode
        self.scenario_mode.playlist_registry.set_custom_playlist_manager(self.custom_playlist_manager)
        
        # Initialize menu system
        self._setup_menus()
        
        # Register keyboard callbacks
        self._setup_keyboard_callbacks()
        
        # Set initial pause time
        self.game_state.pause_time = DEFAULT_PAUSE_TIME
    
    def _setup_menus(self):
        """Set up all menu systems"""
        # Main menu
        self.menu_renderer = MenuRenderer(self.game_interface.renderer)
        self.menu_renderer.add_element(UIElement('Main Menu', header=True))
        self.menu_renderer.add_element(UIElement('Reset Score', function=self._clear_score))
        self.menu_renderer.add_element(UIElement('Toggle Mirror', function=self._toggle_mirror))
        self.menu_renderer.add_element(UIElement('Freeze Scenario', function=self._toggle_freeze_scenario))
        self.menu_renderer.add_element(UIElement('Create Custom Mode', function=self._create_custom_mode))
        
        # Playlist menu
        self.playlist_menu = self.create_playlist_menu()
        self.menu_renderer.add_element(UIElement('Select Playlist', submenu=self.playlist_menu))
        
        # Custom playlist creation menu
        if self.custom_playlist_manager:
            custom_playlist_menu = self.custom_playlist_manager.create_playlist_creation_menu()
            self.menu_renderer.add_element(UIElement('Create Custom Playlist', submenu=custom_playlist_menu))
        
        # Preset mode menu
        self.preset_mode_menu = MenuRenderer(self.game_interface.renderer, columns=2)
        self.preset_mode_menu.add_element(UIElement('Offensive Mode', header=True), column=0)
        for mode in OffensiveMode:
            self.preset_mode_menu.add_element(
                UIElement(mode.name, function=self._select_offensive_mode, function_args=mode), 
                column=0
            )
        self.preset_mode_menu.add_element(UIElement('Defensive Mode', header=True), column=1)
        for mode in DefensiveMode:
            self.preset_mode_menu.add_element(
                UIElement(mode.name, function=self._select_defensive_mode, function_args=mode), 
                column=1
            )
        self.menu_renderer.add_element(UIElement('Select Preset Mode', submenu=self.preset_mode_menu))
        
        # Race mode menu
        self.race_mode_menu = MenuRenderer(self.game_interface.renderer)
        self.race_mode_menu.add_element(UIElement('Number of Trials', header=True))
        for option in DEFAULT_TRIAL_OPTIONS:
            self.race_mode_menu.add_element(
                UIElement(str(option), function=self._set_race_mode, function_args=option)
            )
        self.menu_renderer.add_element(UIElement('Race Mode', submenu=self.race_mode_menu))
    
    def _setup_keyboard_callbacks(self):
        """Set up all keyboard callbacks"""
        # Menu callbacks
        self.keyboard_handler.register_callback('menu_toggle', self._toggle_menu)
        self.keyboard_handler.register_callback('menu_up', self.menu_renderer.select_last_element)
        self.keyboard_handler.register_callback('menu_down', self.menu_renderer.select_next_element)
        self.keyboard_handler.register_callback('menu_left', self.menu_renderer.move_to_prev_column)
        self.keyboard_handler.register_callback('menu_right', self.menu_renderer.move_to_next_column)
        self.keyboard_handler.register_callback('menu_back', self.menu_renderer.handle_back_key)
        self.keyboard_handler.register_callback('enter', self.menu_renderer.enter_element)
        
        # Custom mode callbacks
        self.keyboard_handler.register_callback('custom_down', self._custom_down_handler)
        self.keyboard_handler.register_callback('custom_up', self._custom_up_handler)
        self.keyboard_handler.register_callback('custom_left', self._custom_left_handler)
        self.keyboard_handler.register_callback('custom_right', self._custom_right_handler)
        self.keyboard_handler.register_callback('next_custom_step', self._next_custom_step)
        self.keyboard_handler.register_callback('prev_custom_step', self._prev_custom_step)
    
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
    
    def _set_free_goal_mode(self, trials):
        """Set free goal mode with specified number of trials"""
        print(f"Setting free goal mode with {trials} trials")
        self.game_state.free_goal_mode = True
        self.game_state.mirrored = True
        self.game_state.gym_mode = GymMode.SCENARIO
        self.game_state.game_phase = ScenarioPhase.INIT
        self.game_state.num_trials = trials
        
        # Switch to scenario mode
        if self.current_mode:
            self.current_mode.cleanup()
        self.current_mode = self.scenario_mode
    
    def _toggle_menu(self):
        """Toggle menu visibility"""
        if self.game_state.gym_mode == GymMode.RACE:
            if self.game_state.game_phase == RacePhase.MENU:
                self.game_state.game_phase = RacePhase.ACTIVE
            else:
                self.game_state.game_phase = RacePhase.MENU
        elif self.game_state.gym_mode == GymMode.SCENARIO:
            if self.game_state.game_phase == ScenarioPhase.MENU:
                self.game_state.game_phase = ScenarioPhase.PAUSED
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
        if hasattr(self.scenario_mode, 'playlist_registry'):
            self.scenario_mode.playlist_registry.refresh_custom_playlists()
        
        playlist_menu = MenuRenderer(self.game_interface.renderer, columns=1)
        playlist_menu.add_element(UIElement("Select Playlist", header=True))
        
        # Add each playlist as a menu option
        for playlist_name in self.scenario_mode.playlist_registry.list_playlists():
            playlist = self.scenario_mode.playlist_registry.get_playlist(playlist_name)
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


# Entry point
if __name__ == "__main__":
    script = Dojo()
    script.run() 
