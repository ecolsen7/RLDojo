from abc import ABC, abstractmethod
from enum import Enum
from pprint import pprint
from typing import TYPE_CHECKING, Optional, Tuple
from collections import namedtuple

from rlbot.utils.game_state_util import CarState, GameState, BallState, Physics
from rlbot.messages.flat.PlayerSpectate import PlayerSpectate
from rlbot.socket.socket_manager_asyncio import SocketRelayAsyncio
from input_management.async_event_loop_manager import AsyncManager

from custom_scenario import CustomScenario
from game_modes import BaseGameMode
from game_state import EditPlaylistPhase

if TYPE_CHECKING:
    from game_state import DojoGameState
    from custom_replay import CustomReplayManager
    from playlist import Playlist
    from rlbot.utils.structures.game_interface import GameInterface
    from rlbot.utils.structures.game_data_struct import GameTickPacket

class PlaylistEditMode(BaseGameMode):
    """"""

    PlayerIndexMapping = namedtuple('PlayerIndexMapping', ['custom_scenario_index', 'rlbot_packet_index'])
    
    def __init__(self, game_state: 'DojoGameState', game_interface: 'GameInterface'):
        super().__init__(game_state, game_interface)
        self.game_state = game_state
        self.game_interface = game_interface
        self.current_packet: Optional['GameTickPacket'] = None
        self.current_playlist: Optional['Playlist'] = None
        self.currently_spectated_player_id: Optional[int] = None

        # Socket relay for listening to player spectate events
        self.socket_relay = None
        self.relay_task = None

    def update(self, packet: 'GameTickPacket') -> None:
        """Update the game mode with the current packet"""
        self.current_packet = packet

        phase_handlers = {
            EditPlaylistPhase.INIT: lambda _: self.initialize(),
            # EditPlaylistPhase.SETUP: self._handle_setup_phase,
            # EditPlaylistPhase.MENU: self._handle_menu_phase,
            EditPlaylistPhase.EXITING_MENU: self._handle_exit_menu_phase,
            # EditPlaylistPhase.ACTIVE: self._handle_active_phase,
        }

        handler = phase_handlers.get(self.game_state.game_phase)
        if handler:
            handler(packet)

    def initialize(self) -> None:
        """Initialize the game mode"""
        # Start listening to spectate events to figure out which player is being spectated in replay
        print("Initializing socket relay...")
        if self.socket_relay:
            print("Socket relay already initialized. Skipping...")
            return
        self.socket_relay = SocketRelayAsyncio()
        self.socket_relay.player_spectate_handlers.append(self._handle_spectate)
        relay_future = self.socket_relay.connect_and_run(wants_quick_chat=False, wants_game_messages=True,
                                                         wants_ball_predictions=False)
        AsyncManager.get_instance().start()
        self.relay_task = AsyncManager.get_instance().run_coroutine(relay_future)
        self.game_state.game_phase = EditPlaylistPhase.ACTIVE

    def cleanup(self) -> None:
        """Clean up resources when switching away from this mode"""
        print("Cleaning up socket relay...")
        if self.socket_relay:
            self.socket_relay.disconnect()
        if self.relay_task:
            self.relay_task.cancel()
        self.socket_relay = None
        self.relay_task = None

    def _handle_spectate(self, spectate: PlayerSpectate, seconds: float, frame_num: int):
        print(f'Spectating player index {spectate.PlayerIndex()}')
        self.currently_spectated_player_id = spectate.PlayerIndex()

    def _handle_exit_menu_phase(self, packet):
        """Handle exiting the menu"""
        self.game_state.game_phase = EditPlaylistPhase.ACTIVE
    
    def get_current_game_state(self) -> GameState:
        packet = self.current_packet
        indices, should_mirror_physics = self.map_player_indices()
        car_states = {}
        # Store vehicles in order. The first element is always the player.
        # Mirror physics if necessary, so players are facing the correct goal.
        print(f"Mirroring physics: {should_mirror_physics}")
        for player_mapping in indices:
            custom_scenario_index = player_mapping.custom_scenario_index
            rlbot_packet_index = player_mapping.rlbot_packet_index
            player = packet.game_cars[rlbot_packet_index]
            car_physics = self.mirror_physics(player.physics) if should_mirror_physics else player.physics
            car_state = CarState(physics=car_physics, boost_amount=player.boost,
                                     jumped=player.jumped, double_jumped=player.double_jumped)
            car_states[custom_scenario_index] = car_state
        ball_physics = self.mirror_physics(packet.game_ball.physics) if should_mirror_physics else packet.game_ball.physics
        ball_state = BallState(physics=ball_physics)
        rlbot_game_state = GameState(ball=ball_state, cars=car_states)
        return rlbot_game_state

    def mirror_physics(self, physics: Physics):
        '''
        Mirror the scenario across the Y axis, turning defensive scenarios into offensive scenarios
        Involves flipping the Y aspects of the car + ball locations, velocity, and yaw
        '''
        if physics.location:
            physics.location.y = -physics.location.y
        if physics.rotation:
            physics.rotation.yaw = -physics.rotation.yaw
        if physics.velocity:
            physics.velocity.y = -physics.velocity.y
        return physics

    def map_player_indices(self) -> Tuple[list[PlayerIndexMapping], bool]:
        """
        Players can be in any order in the game (i.e., in the RLBot packet).

        However, RLBot expects them to be in a specific order.
        The first car is always the ego player in RLBot / Dojo.
        Then comes anyone in their team and finally the other team.

        Here we create a mapping between these two indexing schemes.

        Example player order in a replay:
        [{'index': 0, 'name': 'orange_player_1', 'team': 1},
         {'index': 1, 'name': 'blue_player_1', 'team': 0},
         {'index': 2, 'name': 'blue_player_2', 'team': 0},
         {'index': 3, 'name': 'orange_player_2', 'team': 1},]
        """
        # Find ego car index and map teams
        ego_player_index = self.currently_spectated_player_id
        ego_player_team = None
        ego_player_name = None
        blue_team = {}  # Team 0
        orange_team = {}  # Team 1
        for i, player_info in enumerate(self.current_packet.game_cars):
            if player_info.hitbox.length == 0:
                # Assume that this player does not exist, as it has no hitbox.
                continue
            # Check team
            if player_info.team == 0:
                blue_team[i] = i
            else:
                orange_team[i] = i
            # Is this the ego player?
            if i == ego_player_index:
                ego_player_name = player_info.name
                ego_player_team = player_info.team

        if ego_player_name is None:
            ego_player_index = 0
            ego_player_team = 0
            print(f"Could not find ego player {ego_player_index} in current game state. "
                  f"Defaulting to player index 0 and team 0.")
        else:
            print(f"Ego player {ego_player_name} is player index {ego_player_index} on team {ego_player_team}")

        # Construct mapping from scenario index to rlbot packet index
        player_indices = []
        current_index = 0
        should_mirror_positions = False
        if ego_player_team == 0:
            # Blue team first
            teams = [blue_team, orange_team]
            should_mirror_positions = False
        else:
            # Orange team first
            teams = [orange_team, blue_team]
            should_mirror_positions = True

        # Handle ego player first
        if ego_player_index in teams[0]:
            del teams[0][ego_player_index]
            player_indices.append(self.PlayerIndexMapping(custom_scenario_index=current_index,
                                                          rlbot_packet_index=ego_player_index))
            # player_indices[current_index] = ego_player_index
            current_index += 1

        # Then add the rest of the players ordered by team
        for team in teams:
            for player_index in team:
                print(f"Mapping {current_index} to player {player_index}")
                # player_indices[current_index] = player_index
                player_indices.append(self.PlayerIndexMapping(custom_scenario_index=current_index,
                                                              rlbot_packet_index=player_index))
                current_index += 1

        pprint(player_indices)
        return player_indices, should_mirror_positions

    def get_player_metadata(self):
        packet = self.current_packet
        if not packet:
            return
        player_metadata = []

        for i, player_info in enumerate(packet.game_cars):
            if player_info.hitbox.length == 0:
                # Assume that this player does not exist, as it has no hitbox.
                continue
            player_metadata.append({
                "index": i,
                "team": player_info.team,
                "name": player_info.name,
            })

        pprint(player_metadata)


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

    def __init__(self, renderer, game_state: DojoGameState, custom_replay_manager: 'CustomReplayManager'):
        self.renderer = renderer
        self.game_state = game_state
        self.custom_replay_manager = custom_replay_manager

    def render_main_ui(self):
        """Render the main UI elements"""

        # Render UI elements
        self.renderer.begin_rendering()

        # Header text
        text = "Welcome to the Replay mode. Press 'm' to enter menu."
        self.renderer.draw_string_2d(20, 50, 1, 1, text, self.renderer.yellow())

        def game_mode_from_number_of_vehicles(number_of_vehicles):
            # Converts number of vehicles to human readable name
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


        # Other text elements
        text_elements = ["In this mode you can add scenarios to a playlist."]

        playlist = self.custom_replay_manager.get_current_playlist()
        if playlist:
            text_elements.append("Current playlist:")
            text_elements.append(f"\t Name: {playlist.name}")
            text_elements.append(f"\t Scenarios: {len(playlist.scenarios)}")
            text_elements.append(f"\t Custom scenarios: {len(playlist.custom_scenarios)}")
            number_of_players = self.custom_replay_manager.get_number_of_vehicles_in_custom_scenarios()
            rl_game_mode_names = [game_mode_from_number_of_vehicles(x) for x in number_of_players]
            text_elements.append(f"\t Custom scenario game modes: {rl_game_mode_names}")
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
