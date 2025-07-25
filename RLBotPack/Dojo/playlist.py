"""
Playlist system for Dojo training scenarios.

This module provides a flexible playlist system that allows grouping scenarios
around specific themes or training goals. Playlists can specify:

- Combinations of offensive and defensive modes
- Player role (offense or defense)
- Custom settings like timeout, shuffle, boost ranges, and rule zero
- Weighted scenario selection

Boost Range Feature:
- If a playlist specifies boost_range=(min, max), it overrides the default
  random boost generation (12-100) that happens in scenario creation
- This allows playlists to focus on specific boost management scenarios
- Examples: Low boost for finishing practice, high boost for mechanical plays

Rule Zero Feature:
- If a playlist specifies rule_zero=True, scenarios won't end at timeout until
  the ball touches the ground, similar to Rocket League's "rule zero"
- This creates more realistic game-ending conditions and allows plays to finish naturally
- Useful for training scenarios where timing and ball control are critical
"""

from enum import Enum
import numpy as np
from scenario import OffensiveMode, DefensiveMode
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Tuple

EXTERNAL_MENU_START_X = 1200
EXTERNAL_MENU_START_Y = 200
EXTERNAL_MENU_WIDTH = 500
EXTERNAL_MENU_HEIGHT = 800

class PlayerRole(Enum):
    OFFENSE = 0
    DEFENSE = 1

class ScenarioConfig(BaseModel):
    offensive_mode: OffensiveMode
    defensive_mode: DefensiveMode
    player_role: PlayerRole
    weight: float = 1.0

class PlaylistSettings(BaseModel):
    timeout: float = 7.0
    shuffle: bool = True
    loop: bool = True
    boost_range: Tuple[int, int] = (12, 100)
    rule_zero: bool = False

class Playlist(BaseModel):
    name: str
    description: str
    scenarios: Optional[List[ScenarioConfig]] = Field(default_factory=list)
    settings: Optional[PlaylistSettings] = None
    offensive_modes: Optional[List[OffensiveMode]] = Field(default_factory=list)
    defensive_modes: Optional[List[DefensiveMode]] = Field(default_factory=list)
    player_role: Optional[PlayerRole] = None

    def setup(self):
        # If offensive_modes and defensive_modes are provided, generate all combinations
        if self.offensive_modes and self.defensive_modes and self.player_role is not None:
            self.scenarios = []
            for off_mode in self.offensive_modes:
                for def_mode in self.defensive_modes:
                    self.scenarios.append(ScenarioConfig(off_mode, def_mode, self.player_role))
        
        if self.settings and self.settings.shuffle:
            self._shuffle_scenarios()
    
    def get_next_scenario(self):
        """Get next scenario, considering weights"""
        if not self.scenarios:
            return None
            
        # Use weighted random selection
        weights = [s.weight for s in self.scenarios]
        scenario = np.random.choice(self.scenarios, p=np.array(weights)/sum(weights))
        return scenario
    
    def _shuffle_scenarios(self):
        """Shuffle scenario order"""
        np.random.shuffle(self.scenarios)
        
    def render_details(self, renderer):
        """Render the playlist details"""
        if not renderer:
            return
        
        renderer.draw_rect_2d(EXTERNAL_MENU_START_X, EXTERNAL_MENU_START_Y, EXTERNAL_MENU_WIDTH, EXTERNAL_MENU_HEIGHT, False, renderer.black())
        print_start_x = EXTERNAL_MENU_START_X + 10
        print_start_y = EXTERNAL_MENU_START_Y + 10
        text_color = renderer.white()
        renderer.draw_string_2d(print_start_x, print_start_y, 1, 1, "Playlist Details", text_color)
        print_start_y += 20
        renderer.draw_string_2d(print_start_x, print_start_y, 1, 1, f"Name: {self.name}", text_color)
        print_start_y += 20
        num_scenarios = len(self.scenarios)
        num_scenarios_text = str(num_scenarios)
        renderer.draw_string_2d(print_start_x, print_start_y, 1, 1, f"Scenarios: {num_scenarios_text}", text_color)
        print_start_y += 20
        for scenario in self.scenarios:
            renderer.draw_string_2d(print_start_x, print_start_y, 1, 1, f"{scenario.offensive_mode.name} vs {scenario.defensive_mode.name}", text_color)
            print_start_y += 20
        if self.settings:
            renderer.draw_string_2d(print_start_x, print_start_y, 1, 1, f"Boost Range: {self.settings.boost_range[0]}-{self.settings.boost_range[1]}", text_color)
            print_start_y += 20
            renderer.draw_string_2d(print_start_x, print_start_y, 1, 1, f"Timeout: {self.settings.timeout}s", text_color)
            print_start_y += 20

class PlaylistRegistry:
    def __init__(self, renderer=None):
        self.playlists = {}
        self.custom_playlist_manager = None
        self._register_default_playlists()
    
    def set_custom_playlist_manager(self, manager):
        """Set the custom playlist manager to load custom playlists"""
        self.custom_playlist_manager = manager
        self._load_custom_playlists()
    
    def _load_custom_playlists(self):
        """Load custom playlists from the manager"""
        if self.custom_playlist_manager:
            custom_playlists = self.custom_playlist_manager.get_custom_playlists()
            for name, playlist in custom_playlists.items():
                self.playlists[name] = playlist
    
    def register_playlist(self, playlist):
        self.playlists[playlist.name] = playlist
    
    def get_playlist(self, name):
        return self.playlists.get(name)
    
    def list_playlists(self):
        return list(self.playlists.keys())
    
    def refresh_custom_playlists(self):
        """Refresh custom playlists from disk"""
        if self.custom_playlist_manager:
            # Remove existing custom playlists
            custom_names = list(self.custom_playlist_manager.get_custom_playlists().keys())
            for name in custom_names:
                if name in self.playlists:
                    del self.playlists[name]
            
            # Reload custom playlists
            self.custom_playlist_manager.load_custom_playlists()
            self._load_custom_playlists()
    
    def _register_default_playlists(self):
        # Free Goal (Offense focus) - Low boost for finishing practice
        free_goal = Playlist(
            name="Free Goal",
            description="Practice finishing with minimal defense",
            scenarios=[
                ScenarioConfig(offensive_mode=OffensiveMode.BACKPASS, defensive_mode=DefensiveMode.RECOVERING, player_role=PlayerRole.OFFENSE),
                ScenarioConfig(offensive_mode=OffensiveMode.SIDEWALL_BREAKOUT, defensive_mode=DefensiveMode.RECOVERING, player_role=PlayerRole.OFFENSE),
                ScenarioConfig(offensive_mode=OffensiveMode.PASS, defensive_mode=DefensiveMode.RECOVERING, player_role=PlayerRole.OFFENSE),
                ScenarioConfig(offensive_mode=OffensiveMode.CORNER, defensive_mode=DefensiveMode.RECOVERING, player_role=PlayerRole.OFFENSE),
                ScenarioConfig(offensive_mode=OffensiveMode.SIDE_BACKBOARD_PASS, defensive_mode=DefensiveMode.RECOVERING, player_role=PlayerRole.OFFENSE),
            ],
            settings=PlaylistSettings(boost_range=(20, 60), rule_zero=True)  # Lower boost for finishing practice, rule zero for natural endings
        )
        
        # Shadow Defense (Defense focus) - Variable boost for realistic defense
        shadow_defense = Playlist(
            name="Shadow Defense",
            description="Practice defensive positioning and timing",
            scenarios=[
                ScenarioConfig(offensive_mode=OffensiveMode.POSSESSION, defensive_mode=DefensiveMode.NEAR_SHADOW, player_role=PlayerRole.DEFENSE),
                ScenarioConfig(offensive_mode=OffensiveMode.BREAKOUT, defensive_mode=DefensiveMode.FAR_SHADOW, player_role=PlayerRole.DEFENSE),
                ScenarioConfig(offensive_mode=OffensiveMode.CARRY, defensive_mode=DefensiveMode.NEAR_SHADOW, player_role=PlayerRole.DEFENSE),
            ],
            settings=PlaylistSettings(boost_range=(30, 80))  # Moderate boost for defense
        )
        
        # 1v1 Mixed (Both roles) - Full boost range for varied scenarios
        ones_mixed = Playlist(
            name="1v1 Mixed",
            description="Balanced offensive and defensive scenarios",
            scenarios=[
                ScenarioConfig(offensive_mode=OffensiveMode.POSSESSION, defensive_mode=DefensiveMode.NEAR_SHADOW, player_role=PlayerRole.OFFENSE),
                ScenarioConfig(offensive_mode=OffensiveMode.CORNER, defensive_mode=DefensiveMode.CORNER, player_role=PlayerRole.DEFENSE),
                ScenarioConfig(offensive_mode=OffensiveMode.SIDEWALL, defensive_mode=DefensiveMode.FAR_SHADOW, player_role=PlayerRole.OFFENSE),
                ScenarioConfig(offensive_mode=OffensiveMode.BREAKOUT, defensive_mode=DefensiveMode.NET, player_role=PlayerRole.DEFENSE),
            ]
            # No boost_range specified - uses default (12, 100)
        )
        
        # Mechanical (Complex offensive plays) - High boost for mechanical execution
        mechanical = Playlist(
            name="Mechanical",
            description="Practice complex mechanical plays and wall work",
            offensive_modes=[
                OffensiveMode.SIDEWALL,
                OffensiveMode.SIDEWALL_BREAKOUT,
                OffensiveMode.BACKPASS,
                OffensiveMode.BACK_CORNER_BREAKOUT
            ],
            defensive_modes=[
                DefensiveMode.NEAR_SHADOW,
                DefensiveMode.FAR_SHADOW,
                DefensiveMode.NET,
                DefensiveMode.CORNER
            ],
            player_role=PlayerRole.OFFENSE,
            settings=PlaylistSettings(timeout=10.0, shuffle=True, boost_range=(74, 100))  # High boost for mechanics
        )
        
        # Front Intercept Defense - Practice intercepting offensive plays
        front_intercept_defense = Playlist(
            name="Front Intercept Defense",
            description="Practice intercepting and challenging offensive plays from an advanced defensive position",
            offensive_modes=[
                OffensiveMode.POSSESSION,
                OffensiveMode.BREAKOUT,
                OffensiveMode.CARRY,
                OffensiveMode.BACKPASS,
                OffensiveMode.SIDEWALL,
                OffensiveMode.SIDEWALL_BREAKOUT,
                OffensiveMode.BACK_CORNER_BREAKOUT,
            ],
            defensive_modes=[
                DefensiveMode.FRONT_INTERCEPT
            ],
            player_role=PlayerRole.DEFENSE,
            settings=PlaylistSettings(timeout=8.0, shuffle=True, boost_range=(40, 90), rule_zero=True)  # Rule zero for realistic challenge timing
        )
        
        self.register_playlist(free_goal)
        self.register_playlist(shadow_defense)
        self.register_playlist(ones_mixed)
        self.register_playlist(mechanical)
        self.register_playlist(front_intercept_defense) 
