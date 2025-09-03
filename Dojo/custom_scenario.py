import json
import os
from typing import List, Dict, Any, Optional, Tuple
from playlist import Playlist, ScenarioConfig, PlaylistSettings, PlayerRole
from scenario import OffensiveMode, DefensiveMode
from menu import MenuRenderer, UIElement
from pydantic import BaseModel, Field, ValidationError
from rlbot.utils.game_state_util import GameState


class CustomScenario(BaseModel):
    name: str
    game_state: GameState


    def load_custom_scenarios(self):
        """Load custom scenarios from disk and return a list of all custom scenarios"""
        custom_scenarios = {}
        for file in os.listdir(_get_custom_scenarios_path()):
            if file.endswith(".json"):
                with open(os.path.join(_get_custom_scenarios_path(), file), "r") as f:
                    custom_scenarios[file.replace(".json", "")] = CustomScenario.model_validate_json(f.read())
                    
    def _save_current_scenario(self):
        """Save the currently configured scenario to file"""
        if not self.name:
            print("Please set a scenario name first")
            return
        
        # Register the playlist in the playlist registry 
        # and save it to file
        scenario = CustomScenario(
            name=self.name,
            game_state=self.game_state
        )
        
        with open(os.path.join(_get_custom_scenarios_path(), f"{self.name}.json"), "w") as f:
            f.write(self.model_dump_json())


def _get_custom_scenarios_path():
    appdata_path = os.path.expandvars("%APPDATA%")
    if not os.path.exists(os.path.join(appdata_path, "RLBot", "Dojo", "Scenarios")):
        os.makedirs(os.path.join(appdata_path, "RLBot", "Dojo", "Scenarios"))
    return os.path.join(appdata_path, "RLBot", "Dojo", "Scenarios")
