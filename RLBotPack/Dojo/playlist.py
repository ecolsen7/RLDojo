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

class PlayerRole(Enum):
    OFFENSE = 0
    DEFENSE = 1

class ScenarioConfig:
    def __init__(self, offensive_mode, defensive_mode, player_role, weight=1.0):
        self.offensive_mode = offensive_mode
        self.defensive_mode = defensive_mode
        self.player_role = player_role  # Which role the human player takes
        self.weight = weight

class PlaylistSettings:
    def __init__(self, timeout=7.0, shuffle=True, loop=True, boost_range=None, rule_zero=False):
        self.timeout = timeout
        self.shuffle = shuffle
        self.loop = loop
        self.boost_range = boost_range  # Tuple (min_boost, max_boost) or None for default (12, 100)
        self.rule_zero = rule_zero  # If True, scenarios don't end at timeout until ball touches ground

class Playlist:
    def __init__(self, name, description, scenarios=None, settings=None, 
                 offensive_modes=None, defensive_modes=None, player_role=None):
        self.name = name
        self.description = description
        self.settings = settings or PlaylistSettings()
        self.current_index = 0
        
        # If offensive_modes and defensive_modes are provided, generate all combinations
        if offensive_modes and defensive_modes and player_role is not None:
            self.scenarios = []
            for off_mode in offensive_modes:
                for def_mode in defensive_modes:
                    self.scenarios.append(ScenarioConfig(off_mode, def_mode, player_role))
        else:
            self.scenarios = scenarios or []
        
        if self.settings.shuffle:
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

class PlaylistRegistry:
    def __init__(self):
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
            "Free Goal",
            "Practice finishing with minimal defense",
            scenarios=[
                ScenarioConfig(OffensiveMode.BACKPASS, DefensiveMode.RECOVERING, PlayerRole.OFFENSE),
                ScenarioConfig(OffensiveMode.SIDEWALL_BREAKOUT, DefensiveMode.RECOVERING, PlayerRole.OFFENSE),
                ScenarioConfig(OffensiveMode.PASS, DefensiveMode.RECOVERING, PlayerRole.OFFENSE),
                ScenarioConfig(OffensiveMode.CORNER, DefensiveMode.RECOVERING, PlayerRole.OFFENSE),
                ScenarioConfig(OffensiveMode.SIDE_BACKBOARD_PASS, DefensiveMode.RECOVERING, PlayerRole.OFFENSE),
            ],
            settings=PlaylistSettings(boost_range=(20, 60), rule_zero=True)  # Lower boost for finishing practice, rule zero for natural endings
        )
        
        # Shadow Defense (Defense focus) - Variable boost for realistic defense
        shadow_defense = Playlist(
            "Shadow Defense",
            "Practice defensive positioning and timing",
            scenarios=[
                ScenarioConfig(OffensiveMode.POSSESSION, DefensiveMode.NEAR_SHADOW, PlayerRole.DEFENSE),
                ScenarioConfig(OffensiveMode.BREAKOUT, DefensiveMode.FAR_SHADOW, PlayerRole.DEFENSE),
                ScenarioConfig(OffensiveMode.CARRY, DefensiveMode.NEAR_SHADOW, PlayerRole.DEFENSE),
            ],
            settings=PlaylistSettings(boost_range=(30, 80))  # Moderate boost for defense
        )
        
        # 1v1 Mixed (Both roles) - Full boost range for varied scenarios
        ones_mixed = Playlist(
            "1v1 Mixed",
            "Balanced offensive and defensive scenarios",
            scenarios=[
                ScenarioConfig(OffensiveMode.POSSESSION, DefensiveMode.NEAR_SHADOW, PlayerRole.OFFENSE),
                ScenarioConfig(OffensiveMode.CORNER, DefensiveMode.CORNER, PlayerRole.DEFENSE),
                ScenarioConfig(OffensiveMode.SIDEWALL, DefensiveMode.FAR_SHADOW, PlayerRole.OFFENSE),
                ScenarioConfig(OffensiveMode.BREAKOUT, DefensiveMode.NET, PlayerRole.DEFENSE),
            ]
            # No boost_range specified - uses default (12, 100)
        )
        
        # Mechanical (Complex offensive plays) - High boost for mechanical execution
        mechanical = Playlist(
            "Mechanical",
            "Practice complex mechanical plays and wall work",
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
            "Front Intercept Defense",
            "Practice intercepting and challenging offensive plays from an advanced defensive position",
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
