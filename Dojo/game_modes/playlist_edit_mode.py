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
    
    def get_current_game_state(self) -> GameState | None:
        if not self.current_packet:
            print("No packet received from RLBot. Cannot get current game state.")
            return None
        packet = self.current_packet
        indices, should_mirror_physics = self.map_player_indices()
        car_states = {}
        # Store vehicles in order. The first element is always the player.
        # Mirror physics if necessary, so players are facing the correct goal.
        # print(f"Mirroring physics: {should_mirror_physics}")
        for player_mapping in indices:
            custom_scenario_index = player_mapping.custom_scenario_index
            rlbot_packet_index = player_mapping.rlbot_packet_index
            player = packet.game_cars[rlbot_packet_index]
            car_physics = self.mirror_physics(player.physics) if should_mirror_physics else player.physics
            car_state = CarState(physics=car_physics, boost_amount=player.boost,
                                 # jumped=player.jumped, double_jumped=player.double_jumped  # RLBotv4 does not support these
                                 )
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
        # Null handling
        if not self.current_packet:
            print("No current packet. Cannot map player indices.")
            return [], False

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


