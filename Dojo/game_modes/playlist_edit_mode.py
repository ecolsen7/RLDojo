from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Optional

from rlbot.utils.game_state_util import CarState, GameState, BallState

from custom_scenario import CustomScenario
from game_modes import BaseGameMode

if TYPE_CHECKING:
    from game_state import DojoGameState
    from playlist import Playlist
    from rlbot.utils.structures.game_interface import GameInterface
    from rlbot.utils.structures.game_data_struct import GameTickPacket

class EditPhase(Enum):
    # INIT = -1
    # SETUP = 0
    # ACTIVE = 1
    # MENU = 2
    # EXITING_MENU = 3
    # FINISHED = 4
    IN_REPLAY = 5  # DRAFT: Shows playlist details and hotkeys in UI
    EDIT_MODE = 6  # DRAFT: Use hotkeys to switch between scenarios. Edit or delete scenarios.

class PlaylistEditMode(BaseGameMode):
    """"""
    
    def __init__(self, game_state: 'DojoGameState', game_interface: 'GameInterface', game_ui: 'ReplayUIRenderer'):
        super().__init__(game_state, game_interface)
        self.game_state = game_state
        self.game_interface = game_interface
        self.game_ui = game_ui
        self.current_packet: Optional['GameTickPacket'] = None
        self.current_playlist: Optional['Playlist'] = None

    def update(self, packet: 'GameTickPacket') -> None:
        """Update the game mode with the current packet"""
        self.current_packet = packet

    def initialize(self) -> None:
        """Initialize the game mode"""
        pass

    def cleanup(self) -> None:
        """Clean up resources when switching away from this mode"""
        pass
    
    def get_current_game_state(self) -> GameState:
        packet = self.current_packet
        car_states = {}
        # Player indices should match already? The first index is the human player.
        for i, player_info in enumerate(packet.game_cars):
            car_states[i] = CarState(physics=player_info.physics, boost_amount=player_info.boost,
                                     jumped=player_info.jumped, double_jumped=player_info.double_jumped)
        ball_state = BallState(physics=packet.game_ball.physics)
        rlbot_game_state = GameState(ball=ball_state, cars=car_states)
        return rlbot_game_state

    def set_current_playlist(self, playlist: 'Playlist'):
        print("[PlaylistEditMode] Setting new playlist")
        if self.game_ui:
            self.game_ui.playlist = playlist
        else:
            print("[PlaylistEditMode] Error: No UI renderer set")


from typing import Optional
from game_state import DojoGameState, GymMode, ScenarioPhase, CUSTOM_MODES
from constants import (
    SCORE_BOX_START_X, SCORE_BOX_START_Y, SCORE_BOX_WIDTH, SCORE_BOX_HEIGHT,
    CUSTOM_MODE_MENU_START_X, CUSTOM_MODE_MENU_START_Y, CUSTOM_MODE_MENU_WIDTH, CUSTOM_MODE_MENU_HEIGHT,
    CONTROLS_MENU_WIDTH, CONTROLS_MENU_HEIGHT
)
import utils


class ReplayUIRenderer:
    """Handles all UI rendering for the Dojo application"""

    def __init__(self, renderer, game_state: DojoGameState):
        self.renderer = renderer
        self.game_state = game_state
        self.playlist = None

    def render_main_ui(self):
        """Render the main UI elements"""

        # Render UI elements
        self.renderer.begin_rendering()

        # Header text
        text = "Welcome to the Replay mode. Press 'm' to enter menu."
        self.renderer.draw_string_2d(20, 50, 1, 1, text, self.renderer.yellow())


        # Other text elements
        text_elements = ["In this mode you can add scenarios to a playlist."]

        if self.playlist:
            playlist = self.playlist
            text_elements.append("Current playlist:")
            text_elements.append(f"\t Name: {playlist.name}")
            text_elements.append(f"\t Scenarios: {len(playlist.scenarios)}")
            text_elements.append(f"\t Scenarios: {len(playlist.custom_scenarios)}")
            boost_range = playlist.settings.boost_range
            text_elements.append(f"\t Boost Range: {boost_range[0]}-{boost_range[1]}")
            text_elements.append(f"\t Timeout: {playlist.settings.timeout}s")
        else:
            text_elements.append("No playlist selected. Select a playlist from the menu.")



        text_elements.append("Instructions:")
        text_elements.append("\t - Go to any replay.")
        text_elements.append("\t - Press hotkey 'SAVE_STATE' to add a custom scenario to the playlist.")
        text_elements.append("\t - Do not forget to save the playlist afterwards.")
        # text_elements.extend([scores, total_score, time_since_start, previous_record])
        # if self.game_state.gym_mode == GymMode.SCENARIO:
        #     text_elements.extend([offensive_mode_name, defensive_mode_name, player_role_string, game_phase_name])
        #     text_elements.extend([timeout_enabled, freeze_scenario_enabled])

        # Draw elements
        current_y = SCORE_BOX_START_Y + 10
        for i, text in enumerate(text_elements):
            self.renderer.draw_string_2d(SCORE_BOX_START_X + 10, current_y, 1, 1, text, self.renderer.white())
            current_y += 30


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
            ball_end_vector = utils.add_vector3(rlbot_game_state.ball.physics.location,
                                                rlbot_game_state.ball.physics.velocity)
            ball_end = utils.vector3_to_list(ball_end_vector)
            self.renderer.draw_line_3d(ball_start, ball_end, self.renderer.white())

        # Bot car velocity vector
        if CarIndex.BOT.value in rlbot_game_state.cars:
            bot_car = rlbot_game_state.cars[CarIndex.BOT.value]
            bot_start = utils.vector3_to_list(bot_car.physics.location)
            bot_end_vector = utils.add_vector3(bot_car.physics.location, bot_car.physics.velocity)
            bot_end = utils.vector3_to_list(bot_end_vector)
            self.renderer.draw_line_3d(bot_start, bot_end, self.renderer.white())
