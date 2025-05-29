import numpy as np
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator

from .base_mode import BaseGameMode
from state.game_state import ScenarioPhase, CarIndex, CUSTOM_MODES
from scenario import Scenario, OffensiveMode, DefensiveMode
from config.constants import BACK_WALL, GOAL_DETECTION_THRESHOLD, BALL_GROUND_THRESHOLD, FREE_GOAL_TIMEOUT
import utils


class ScenarioMode(BaseGameMode):
    """Handles scenario-based training mode"""
    
    def __init__(self, game_state, game_interface):
        super().__init__(game_state, game_interface)
        self.rlbot_game_state = None
        self.prev_time = 0
    
    def initialize(self):
        """Initialize scenario mode"""
        np.random.seed(0)
        self.game_state.started_time = self.game_state.cur_time
        self.game_state.game_phase = ScenarioPhase.SETUP
        
        if self.game_state.free_goal_mode:
            self.game_state.timeout = FREE_GOAL_TIMEOUT
            self.game_state.rule_zero_mode = False
    
    def cleanup(self):
        """Clean up scenario mode resources"""
        pass
    
    def update(self, packet):
        """Update scenario mode based on current game phase"""
        if self.game_state.paused:
            return
            
        phase_handlers = {
            ScenarioPhase.INIT: self._handle_init_phase,
            ScenarioPhase.SETUP: self._handle_setup_phase,
            ScenarioPhase.MENU: self._handle_menu_phase,
            ScenarioPhase.PAUSED: self._handle_paused_phase,
            ScenarioPhase.ACTIVE: self._handle_active_phase,
            ScenarioPhase.CUSTOM_OFFENSE: self._handle_custom_phase,
            ScenarioPhase.CUSTOM_BALL: self._handle_custom_phase,
            ScenarioPhase.CUSTOM_DEFENSE: self._handle_custom_phase,
        }
        
        handler = phase_handlers.get(self.game_state.game_phase)
        if handler:
            handler(packet)
    
    def get_rlbot_game_state(self):
        """Get the current RLBot game state"""
        return self.rlbot_game_state
    
    def _handle_init_phase(self, packet):
        """Handle initialization phase"""
        self.initialize()
    
    def _handle_setup_phase(self, packet):
        """Handle setup phase - create new scenario"""
        if self.game_state.free_goal_mode:
            self._setup_free_goal_mode()
        
        self._set_next_game_state()
        self.prev_time = self.game_state.cur_time
        self.game_state.game_phase = ScenarioPhase.PAUSED
    
    def _handle_menu_phase(self, packet):
        """Handle menu phase - freeze game state"""
        if self.rlbot_game_state:
            self.set_game_state(self.rlbot_game_state)
    
    def _handle_paused_phase(self, packet):
        """Handle paused phase - wait before starting scenario"""
        time_elapsed = self.game_state.cur_time - self.prev_time
        if (time_elapsed < self.game_state.pause_time or 
            self.goal_scored(packet) or 
            packet.game_info.is_kickoff_pause):
            if self.rlbot_game_state:
                self.set_game_state(self.rlbot_game_state)
        else:
            self.game_state.game_phase = ScenarioPhase.ACTIVE
    
    def _handle_active_phase(self, packet):
        """Handle active scenario phase"""
        # Handle goal reset disabled mode
        if self.game_state.disable_goal_reset:
            if self._check_ball_in_goal(packet):
                return
        
        # Handle kickoff pause
        if packet.game_info.is_kickoff_pause:
            self.game_state.game_phase = ScenarioPhase.SETUP
            return
        
        # Handle timeout
        time_elapsed = self.game_state.cur_time - self.prev_time
        if time_elapsed > self.game_state.timeout:
            if (packet.game_ball.physics.location.z < BALL_GROUND_THRESHOLD or 
                not self.game_state.rule_zero_mode):
                self._award_defensive_goal()
                self.game_state.game_phase = ScenarioPhase.SETUP
                self.game_state.scored_time = self.game_state.cur_time
    
    def _handle_custom_phase(self, packet):
        """Handle custom sandbox phases"""
        if self.rlbot_game_state:
            self.set_game_state(self.rlbot_game_state)
    
    def _setup_free_goal_mode(self):
        """Configure settings for free goal mode"""
        self.game_state.defensive_mode = DefensiveMode.RECOVERING
        valid_offensive_modes = [
            OffensiveMode.BACKPASS,
            OffensiveMode.SIDEWALL_BREAKOUT,
            OffensiveMode.PASS,
            OffensiveMode.BACKWALL_BOUNCE,
            OffensiveMode.CORNER,
            OffensiveMode.SIDE_BACKBOARD_PASS
        ]
        self.game_state.offensive_mode = np.random.choice(valid_offensive_modes)
    
    def _set_next_game_state(self):
        """Create and set the next scenario game state"""
        if not self.game_state.freeze_scenario:
            print(f"Setting next game state: {self.game_state.offensive_mode}, {self.game_state.defensive_mode}")
            scenario = Scenario(self.game_state.offensive_mode, self.game_state.defensive_mode)
            if self.game_state.mirrored:
                scenario.Mirror()
            self.game_state.scenario_history.append(scenario)
            self.game_state.freeze_scenario_index = len(self.game_state.scenario_history) - 1
        else:
            scenario = self.game_state.scenario_history[self.game_state.freeze_scenario_index]
        
        self.rlbot_game_state = scenario.GetGameState()
        self.set_game_state(self.rlbot_game_state)
    
    def _check_ball_in_goal(self, packet) -> bool:
        """Check if ball is in goal and award points accordingly"""
        ball_y = packet.game_ball.physics.location.y
        
        # Check if ball is in blue goal (negative Y)
        if ball_y < BACK_WALL - GOAL_DETECTION_THRESHOLD:
            if not self.game_state.mirrored:
                self.game_state.bot_score += 1
            else:
                self.game_state.human_score += 1
            self.game_state.game_phase = ScenarioPhase.SETUP
            return True
        
        # Check if ball is in orange goal (positive Y)
        elif ball_y > (-BACK_WALL + GOAL_DETECTION_THRESHOLD):
            if self.game_state.mirrored:
                self.game_state.bot_score += 1
            else:
                self.game_state.human_score += 1
            self.game_state.game_phase = ScenarioPhase.SETUP
            return True
        
        # Check for actual goal scored
        if self.goal_scored(packet):
            team_scored = self.get_team_scored(packet)
            if team_scored == CarIndex.HUMAN.value:
                self.game_state.human_score += 1
            else:
                self.game_state.bot_score += 1
            self.game_state.game_phase = ScenarioPhase.SETUP
            return True
        
        return False
    
    def _award_defensive_goal(self):
        """Award a goal to the defensive team"""
        if self.game_state.mirrored:
            self.game_state.bot_score += 1
        else:
            self.game_state.human_score += 1 
