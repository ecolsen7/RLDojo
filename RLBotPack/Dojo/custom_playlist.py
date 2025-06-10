"""
Custom playlist creation and management system for Dojo.

This module provides functionality for users to create, edit, and save
custom playlists that persist between sessions.
"""

import json
import os
from typing import List, Dict, Any, Optional, Tuple
from playlist import Playlist, ScenarioConfig, PlaylistSettings, PlayerRole
from scenario import OffensiveMode, DefensiveMode
from menu import MenuRenderer, UIElement

CUSTOM_PLAYLISTS_FILE = "custom_playlists.json"

class CustomPlaylistManager:
    def __init__(self, renderer):
        self.renderer = renderer
        self.custom_playlists = {}
        self.load_custom_playlists()
        
        # Current playlist being created/edited
        self.current_playlist_name = ""
        self.current_scenarios = []
        self.current_boost_range = (12, 100)  # Default boost range
        self.current_timeout = 7.0
        self.current_rule_zero = False
        
    def load_custom_playlists(self):
        """Load custom playlists from disk"""
        if os.path.exists(CUSTOM_PLAYLISTS_FILE):
            try:
                with open(CUSTOM_PLAYLISTS_FILE, 'r') as f:
                    data = json.load(f)
                    
                for name, playlist_data in data.items():
                    scenarios = []
                    for scenario_data in playlist_data['scenarios']:
                        offensive_mode = OffensiveMode(scenario_data['offensive_mode'])
                        defensive_mode = DefensiveMode(scenario_data['defensive_mode'])
                        player_role = PlayerRole(scenario_data['player_role'])
                        weight = scenario_data.get('weight', 1.0)
                        scenarios.append(ScenarioConfig(offensive_mode, defensive_mode, player_role, weight))
                    
                    settings_data = playlist_data['settings']
                    boost_range = tuple(settings_data['boost_range']) if settings_data['boost_range'] else None
                    settings = PlaylistSettings(
                        timeout=settings_data['timeout'],
                        shuffle=settings_data['shuffle'],
                        loop=settings_data['loop'],
                        boost_range=boost_range,
                        rule_zero=settings_data['rule_zero']
                    )
                    
                    playlist = Playlist(
                        name=name,
                        description=playlist_data['description'],
                        scenarios=scenarios,
                        settings=settings
                    )
                    self.custom_playlists[name] = playlist
                    
            except Exception as e:
                print(f"Error loading custom playlists: {e}")
                self.custom_playlists = {}
    
    def save_custom_playlists(self):
        """Save custom playlists to disk"""
        try:
            data = {}
            for name, playlist in self.custom_playlists.items():
                scenarios_data = []
                for scenario in playlist.scenarios:
                    scenarios_data.append({
                        'offensive_mode': scenario.offensive_mode.value,
                        'defensive_mode': scenario.defensive_mode.value,
                        'player_role': scenario.player_role.value,
                        'weight': scenario.weight
                    })
                
                settings_data = {
                    'timeout': playlist.settings.timeout,
                    'shuffle': playlist.settings.shuffle,
                    'loop': playlist.settings.loop,
                    'boost_range': list(playlist.settings.boost_range) if playlist.settings.boost_range else None,
                    'rule_zero': playlist.settings.rule_zero
                }
                
                data[name] = {
                    'description': playlist.description,
                    'scenarios': scenarios_data,
                    'settings': settings_data
                }
            
            with open(CUSTOM_PLAYLISTS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving custom playlists: {e}")
    
    def create_playlist_creation_menu(self):
        """Create the main playlist creation menu"""
        menu = MenuRenderer(self.renderer, columns=1)
        menu.add_element(UIElement("Create Custom Playlist", header=True))
        menu.add_element(UIElement("Set Playlist Name", function=self._start_name_input))
        menu.add_element(UIElement("Add Scenarios", submenu=self._create_scenario_selection_menu()))
        menu.add_element(UIElement("Set Boost Range", submenu=self._create_boost_range_menu()))
        menu.add_element(UIElement("Set Timeout", submenu=self._create_timeout_menu()))
        menu.add_element(UIElement("Toggle Rule Zero", function=self._toggle_rule_zero))
        menu.add_element(UIElement("Show Current Settings", function=self._show_current_settings))
        menu.add_element(UIElement("Save Playlist", function=self._save_current_playlist))
        menu.add_element(UIElement("Cancel", function=self._cancel_playlist_creation))
        return menu
    
    def _create_scenario_selection_menu(self):
        """Create menu for selecting scenarios to add"""
        menu = MenuRenderer(self.renderer, columns=3)
        
        # Column 1: Offensive modes
        menu.add_element(UIElement("Offensive Mode", header=True), column=0)
        for mode in OffensiveMode:
            menu.add_element(UIElement(
                mode.name.replace('_', ' ').title(),
                function=self._set_temp_offensive_mode,
                function_args=mode
            ), column=0)
        
        # Column 2: Defensive modes
        menu.add_element(UIElement("Defensive Mode", header=True), column=1)
        for mode in DefensiveMode:
            menu.add_element(UIElement(
                mode.name.replace('_', ' ').title(),
                function=self._set_temp_defensive_mode,
                function_args=mode
            ), column=1)
        
        # Column 3: Player role and actions
        menu.add_element(UIElement("Player Role", header=True), column=2)
        menu.add_element(UIElement("Offense", function=self._set_temp_player_role, function_args=PlayerRole.OFFENSE), column=2)
        menu.add_element(UIElement("Defense", function=self._set_temp_player_role, function_args=PlayerRole.DEFENSE), column=2)
        menu.add_element(UIElement("", header=True), column=2)  # Spacer
        menu.add_element(UIElement("Add Scenario", function=self._add_current_scenario), column=2)
        menu.add_element(UIElement("View Added Scenarios", function=self._show_scenario_list), column=2)
        menu.add_element(UIElement("Clear All Scenarios", function=self._clear_all_scenarios), column=2)
        
        return menu
    
    def _show_scenario_list(self):
        """Show the list of currently added scenarios"""
        if not self.current_scenarios:
            print("No scenarios added yet")
        else:
            print("Added scenarios:")
            for i, scenario in enumerate(self.current_scenarios):
                scenario_text = f"{i+1}. {scenario.offensive_mode.name.replace('_', ' ').title()} vs {scenario.defensive_mode.name.replace('_', ' ').title()} ({scenario.player_role.name})"
                print(scenario_text)
    
    def _create_boost_range_menu(self):
        """Create menu for setting boost range"""
        menu = MenuRenderer(self.renderer, columns=2)
        
        # Column 1: Min boost
        menu.add_element(UIElement("Min Boost", header=True), column=0)
        for boost in [0, 12, 20, 30, 40, 50, 60, 70]:
            menu.add_element(UIElement(
                str(boost),
                function=self._set_min_boost,
                function_args=boost
            ), column=0)
        
        # Column 2: Max boost
        menu.add_element(UIElement("Max Boost", header=True), column=1)
        for boost in [50, 60, 70, 80, 90, 100]:
            menu.add_element(UIElement(
                str(boost),
                function=self._set_max_boost,
                function_args=boost
            ), column=1)
        
        return menu
    
    def _create_timeout_menu(self):
        """Create menu for setting timeout"""
        menu = MenuRenderer(self.renderer, columns=1)
        menu.add_element(UIElement("Set Timeout (seconds)", header=True))
        
        for timeout in [5.0, 7.0, 10.0, 15.0, 20.0, 30.0]:
            menu.add_element(UIElement(
                f"{timeout}s",
                function=self._set_timeout,
                function_args=timeout
            ))
        
        return menu
    
    # Temporary variables for scenario creation
    temp_offensive_mode = None
    temp_defensive_mode = None
    temp_player_role = None
    
    def _set_temp_offensive_mode(self, mode):
        self.temp_offensive_mode = mode
        print(f"Selected offensive mode: {mode.name}")
    
    def _set_temp_defensive_mode(self, mode):
        self.temp_defensive_mode = mode
        print(f"Selected defensive mode: {mode.name}")
    
    def _set_temp_player_role(self, role):
        self.temp_player_role = role
        print(f"Selected player role: {role.name}")
    
    def _add_current_scenario(self):
        """Add the currently selected scenario configuration"""
        if self.temp_offensive_mode and self.temp_defensive_mode and self.temp_player_role:
            scenario = ScenarioConfig(
                self.temp_offensive_mode,
                self.temp_defensive_mode,
                self.temp_player_role
            )
            self.current_scenarios.append(scenario)
            print(f"Added scenario: {self.temp_offensive_mode.name} vs {self.temp_defensive_mode.name} ({self.temp_player_role.name})")
            
            # Reset temp variables
            self.temp_offensive_mode = None
            self.temp_defensive_mode = None
            self.temp_player_role = None
        else:
            print("Please select offensive mode, defensive mode, and player role first")
    
    def _clear_all_scenarios(self):
        """Clear all scenarios"""
        self.current_scenarios = []
        print("All scenarios cleared")
    
    def _remove_scenario(self, index):
        """Remove scenario at given index"""
        if 0 <= index < len(self.current_scenarios):
            removed = self.current_scenarios.pop(index)
            print(f"Removed scenario: {removed.offensive_mode.name} vs {removed.defensive_mode.name}")
    
    def _set_min_boost(self, boost):
        """Set minimum boost value"""
        self.current_boost_range = (boost, max(boost + 10, self.current_boost_range[1]))
        print(f"Set boost range: {self.current_boost_range}")
    
    def _set_max_boost(self, boost):
        """Set maximum boost value"""
        self.current_boost_range = (min(boost - 10, self.current_boost_range[0]), boost)
        print(f"Set boost range: {self.current_boost_range}")
    
    def _set_timeout(self, timeout):
        """Set scenario timeout"""
        self.current_timeout = timeout
        print(f"Set timeout: {timeout}s")
    
    def _toggle_rule_zero(self):
        """Toggle rule zero setting"""
        self.current_rule_zero = not self.current_rule_zero
        print(f"Rule zero: {'ON' if self.current_rule_zero else 'OFF'}")
    
    def _show_current_settings(self):
        """Show current playlist settings"""
        print("=== Current Playlist Settings ===")
        print(f"Name: {self.current_playlist_name or 'Not set'}")
        print(f"Scenarios: {len(self.current_scenarios)}")
        print(f"Boost Range: {self.current_boost_range[0]}-{self.current_boost_range[1]}")
        print(f"Timeout: {self.current_timeout}s")
        print(f"Rule Zero: {'ON' if self.current_rule_zero else 'OFF'}")
        print("==================================")
    
    def _start_name_input(self):
        """Start playlist name input (simplified for now)"""
        # For now, we'll use a simple counter-based naming
        # In a full implementation, you might want keyboard input
        counter = 1
        while f"Custom Playlist {counter}" in self.custom_playlists:
            counter += 1
        self.current_playlist_name = f"Custom Playlist {counter}"
        print(f"Playlist name set to: {self.current_playlist_name}")
    
    def _save_current_playlist(self):
        """Save the currently configured playlist"""
        if not self.current_playlist_name:
            print("Please set a playlist name first")
            return
        
        if not self.current_scenarios:
            print("Please add at least one scenario")
            return
        
        settings = PlaylistSettings(
            timeout=self.current_timeout,
            shuffle=True,
            loop=True,
            boost_range=self.current_boost_range,
            rule_zero=self.current_rule_zero
        )
        
        playlist = Playlist(
            name=self.current_playlist_name,
            description=f"Custom playlist with {len(self.current_scenarios)} scenarios",
            scenarios=self.current_scenarios.copy(),
            settings=settings
        )
        
        self.custom_playlists[self.current_playlist_name] = playlist
        self.save_custom_playlists()
        
        print(f"Saved playlist: {self.current_playlist_name}")
        
        # Reset current playlist data
        self._reset_current_playlist()
        
        # Notify that playlists have been updated (for menu refresh)
        print("Custom playlist saved! Return to main menu to see it in the playlist list.")
    
    def _cancel_playlist_creation(self):
        """Cancel playlist creation and reset"""
        self._reset_current_playlist()
        print("Playlist creation cancelled")
    
    def _reset_current_playlist(self):
        """Reset current playlist creation data"""
        self.current_playlist_name = ""
        self.current_scenarios = []
        self.current_boost_range = (12, 100)
        self.current_timeout = 7.0
        self.current_rule_zero = False
        self.temp_offensive_mode = None
        self.temp_defensive_mode = None
        self.temp_player_role = None
    
    def get_custom_playlists(self):
        """Get all custom playlists"""
        return self.custom_playlists
    
    def delete_custom_playlist(self, name):
        """Delete a custom playlist"""
        if name in self.custom_playlists:
            del self.custom_playlists[name]
            self.save_custom_playlists()
            print(f"Deleted playlist: {name}") 
