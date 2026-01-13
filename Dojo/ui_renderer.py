from typing import Optional

from custom_playlist import CustomPlaylistManager
from game_state import DojoGameState, GymMode, ScenarioPhase, CUSTOM_MODES
from constants import (
    SCORE_BOX_START_X, SCORE_BOX_START_Y, SCORE_BOX_WIDTH, SCORE_BOX_HEIGHT,
    CUSTOM_MODE_MENU_START_X, CUSTOM_MODE_MENU_START_Y, CUSTOM_MODE_MENU_WIDTH, CUSTOM_MODE_MENU_HEIGHT,
    CONTROLS_MENU_WIDTH, CONTROLS_MENU_HEIGHT
)
import utils


class UIRenderer:
    """Handles all UI rendering for the Dojo application"""
    
    def __init__(self, renderer, game_state: DojoGameState, custom_playlist_manager: CustomPlaylistManager):
        self.renderer = renderer
        self.game_state = game_state
        self.custom_playlist_manager = custom_playlist_manager
    
    def render_main_ui(self):
        """Render the main UI elements (score, time, etc.)"""
        if self.game_state.game_phase in [ScenarioPhase.MENU, *CUSTOM_MODES]:
            return

        # Draw initial UI while components are initializing.
        # Especially HotkeyManager / Pygame can randomly take longer to initialize while blocking the main thread.
        if not self.game_state.dojo_components_initialized:
            self.render_initialization_ui()
            return

        minutes, seconds = self.game_state.get_time_since_start()
        seconds_str = f"{seconds:02d}"
        
        # Draw header text
        text = "Welcome to the Dojo. Press 'm' to enter menu."
        self.renderer.begin_rendering()
        self.renderer.draw_string_2d(20, 50, 1, 1, text, self.renderer.yellow())

        # Collect other text elements
        text_elements = []
        
        if self.game_state.gym_mode == GymMode.SCENARIO:
            text_elements.append(f"Human: {self.game_state.human_score} Bot: {self.game_state.bot_score}")
            text_elements.append(f"Total: {self.game_state.human_score + self.game_state.bot_score}")
            text_elements.append(f"Time: {minutes}:{seconds_str}")
            text_elements.append(f"Timeouts enabled: {self.game_state.enable_timeouts}")
            text_elements.append(f"Scenario frozen: {self.game_state.freeze_scenario}")
            text_elements.append(f"Offensive Mode: {self.game_state.offensive_mode.name}")
            text_elements.append(f"Defensive Mode: {self.game_state.defensive_mode.name}")
            player_role_name = "offense" if self.game_state.player_offense else "defense"
            text_elements.append(f"Player Role: {player_role_name}")
            text_elements.append(f"Game Phase: {self.game_state.game_phase.name}")
        elif self.game_state.gym_mode == GymMode.RACE:
            text_elements.append(f"Completed: {self.game_state.human_score}")
            text_elements.append(f"Out of: {self.game_state.num_trials}")
            text_elements.append(f"Time: {minutes}:{seconds_str}")
            previous_record_data = self.game_state.get_previous_record()
            if previous_record_data:
                prev_minutes = int(previous_record_data // 60)
                prev_seconds = int(previous_record_data % 60)
                previous_record = f"Previous Record: {prev_minutes}:{prev_seconds:02d}"
                text_elements.append(previous_record)
        elif self.game_state.gym_mode == GymMode.EDIT_PLAYLIST:
            text_elements.append(f"Gym mode: Edit playlist mode")
            text_elements.append(f"In this mode you can add scenarios to a playlist.")
            text_elements.append("Current playlist:")
            playlist = self.custom_playlist_manager.get_current_playlist()
            if playlist:
                text_elements.append(f"\t Name: {playlist.name}")
                text_elements.append(f"\t Scenarios: {len(playlist.scenarios)}")
                text_elements.append(f"\t Custom scenarios: {len(playlist.custom_scenarios)}")
                number_of_players = self.custom_playlist_manager.get_number_of_vehicles_in_custom_scenarios()
                rl_game_mode_names = [self.game_mode_from_number_of_vehicles(x) for x in number_of_players]
                text_elements.append(f"\t Custom scenario game modes: {rl_game_mode_names}")
                boost_range = playlist.settings.boost_range
                text_elements.append(f"\t Boost Range: {boost_range[0]}-{boost_range[1]}")
                text_elements.append(f"\t Timeout: {playlist.settings.timeout}s")
            else:
                text_elements.append("No playlist selected. Select a playlist from the menu.")
            text_elements.append("You can also create custom scenarios from replays:")
            text_elements.append("\t - Go to any replay.")
            text_elements.append("\t - Press hotkey 'SAVE_STATE' to add a custom scenario to the playlist.")
            text_elements.append("\t - Do not forget to save the playlist afterwards.")
        else:
            text_elements.append(f"Gym mode: Unknown mode")


        # Draw text elements
        current_y = SCORE_BOX_START_Y + 10
        for i, text in enumerate(text_elements):
            self.renderer.draw_string_2d(SCORE_BOX_START_X + 10, current_y, 1, 1, text, self.renderer.white())
            current_y += 30

        self.renderer.end_rendering()

    def render_initialization_ui(self):
        """ Render a UI that tells the user that components are still loading """
        self.renderer.begin_rendering()
        header_text = "Welcome to the Dojo."
        self.renderer.draw_string_2d(20, 50, 1, 1, header_text, self.renderer.yellow())
        warning_text = ("Waiting for components to initialize... "
                        "\nShould take a few seconds. "
                        "\nIf not, try waiting for up to a minute or restarting your PC.")
        self.renderer.draw_string_2d(
            SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 10,
            1, 1, warning_text, self.renderer.yellow()
        )
        self.renderer.end_rendering()
    
   
    
    def render_velocity_vectors(self, rlbot_game_state):
        """Render velocity vectors for all objects in custom mode"""
        if not rlbot_game_state:
            return
        
        from game_state import CarIndex
        
        # Human car velocity vector
        if CarIndex.HUMAN.value in rlbot_game_state.cars:
            human_car = rlbot_game_state.cars[CarIndex.HUMAN.value]
            human_start = utils.vector3_to_list(human_car.physics.location)
            human_end_vector = utils.add_vector3(human_car.physics.location, human_car.physics.velocity)
            human_end = utils.vector3_to_list(human_end_vector)
            self.renderer.draw_line_3d(human_start, human_end, self.renderer.white())
        
        # Ball velocity vector
        if rlbot_game_state.ball:
            ball_start = utils.vector3_to_list(rlbot_game_state.ball.physics.location)
            ball_end_vector = utils.add_vector3(rlbot_game_state.ball.physics.location, rlbot_game_state.ball.physics.velocity)
            ball_end = utils.vector3_to_list(ball_end_vector)
            self.renderer.draw_line_3d(ball_start, ball_end, self.renderer.white())
        
        # Bot car velocity vector
        if CarIndex.BOT.value in rlbot_game_state.cars:
            bot_car = rlbot_game_state.cars[CarIndex.BOT.value]
            bot_start = utils.vector3_to_list(bot_car.physics.location)
            bot_end_vector = utils.add_vector3(bot_car.physics.location, bot_car.physics.velocity)
            bot_end = utils.vector3_to_list(bot_end_vector)
            self.renderer.draw_line_3d(bot_start, bot_end, self.renderer.white()) 

    def game_mode_from_number_of_vehicles(self, number_of_vehicles):
        # Converts number of vehicles to human-readable name
        if number_of_vehicles <= 1:
            return "solo"
        elif number_of_vehicles <= 2:
            return "1v1"
        elif number_of_vehicles <= 4:
            return "2v2"
        elif number_of_vehicles <= 6:
            return "3v3"
        elif number_of_vehicles <= 8:
            return "4v4"
        else:
            return "Custom"
