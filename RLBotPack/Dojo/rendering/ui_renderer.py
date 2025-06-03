from typing import Optional
from state.game_state import DojoGameState, GymMode, ScenarioPhase, CUSTOM_MODES
from config.constants import (
    SCORE_BOX_START_X, SCORE_BOX_START_Y, SCORE_BOX_WIDTH, SCORE_BOX_HEIGHT,
    CUSTOM_MODE_MENU_START_X, CUSTOM_MODE_MENU_START_Y, CUSTOM_MODE_MENU_WIDTH, CUSTOM_MODE_MENU_HEIGHT,
    CONTROLS_MENU_WIDTH, CONTROLS_MENU_HEIGHT, 
    PROGRESS_BAR_WIDTH, PROGRESS_BAR_HEIGHT, PROGRESS_BAR_START_X, PROGRESS_BAR_START_Y
)
import utils


class UIRenderer:
    """Handles all UI rendering for the Dojo application"""
    
    def __init__(self, renderer, game_state: DojoGameState):
        self.renderer = renderer
        self.game_state = game_state
    
    def render_main_ui(self):
        """Render the main UI elements (score, time, etc.)"""
        if self.game_state.game_phase in [ScenarioPhase.MENU, *CUSTOM_MODES]:
            return
        
        minutes, seconds = self.game_state.get_time_since_start()
        seconds_str = f"{seconds:02d}"
        
        # Prepare text content
        text = "Welcome to the Dojo. Press 'm' to enter menu"
        previous_record = "No record"
        
        if self.game_state.gym_mode == GymMode.SCENARIO:
            scores = f"Human: {self.game_state.human_score} Bot: {self.game_state.bot_score}"
            total_score = f"Total: {self.game_state.human_score + self.game_state.bot_score}"
            time_since_start = f"Time: {minutes}:{seconds_str}"
            previous_record = ""
        elif self.game_state.gym_mode == GymMode.RACE:
            scores = f"Completed: {self.game_state.human_score}"
            total_score = f"Out of: {self.game_state.num_trials}"
            time_since_start = f"Time: {minutes}:{seconds_str}"
            previous_record_data = self.game_state.get_previous_record()
            if previous_record_data:
                prev_minutes = int(previous_record_data // 60)
                prev_seconds = int(previous_record_data % 60)
                previous_record = f"Previous Record: {prev_minutes}:{prev_seconds:02d}"
        
        # Render UI elements
        self.renderer.begin_rendering()
        
        self.render_progress_bar()
        
        # Main instruction text
        self.renderer.draw_string_2d(20, 50, 1, 1, text, self.renderer.yellow())
        
        # Score box
        self.renderer.draw_rect_2d(
            SCORE_BOX_START_X, SCORE_BOX_START_Y, 
            SCORE_BOX_WIDTH, SCORE_BOX_HEIGHT, 
            True, self.renderer.white()
        )
        
        # Score box content
        self.renderer.draw_string_2d(
            SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 10, 
            1, 1, scores, self.renderer.black()
        )
        self.renderer.draw_string_2d(
            SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 40, 
            1, 1, total_score, self.renderer.black()
        )
        self.renderer.draw_string_2d(
            SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 70, 
            1, 1, time_since_start, self.renderer.black()
        )
        self.renderer.draw_string_2d(
            SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 100, 
            1, 1, previous_record, self.renderer.black()
        )
        
        self.renderer.end_rendering()

    def render_progress_bar(self):
        """Render the progress bar"""
        
        if self.game_state.gym_mode != GymMode.RACE:
            return

        # Calculate progress bar position
        progress_bar_x = PROGRESS_BAR_START_X
        progress_bar_y = PROGRESS_BAR_START_Y

        # Render progress bar background
        self.renderer.draw_rect_2d(
            progress_bar_x, progress_bar_y,
            PROGRESS_BAR_WIDTH, PROGRESS_BAR_HEIGHT,
            True, self.renderer.white()
        )
        
        # Calculate progress bar fill
        progress = self.game_state.human_score / self.game_state.num_trials
        fill_width = PROGRESS_BAR_WIDTH * progress

        # Render progress bar fill
        self.renderer.draw_rect_2d(
            progress_bar_x, progress_bar_y,
            int(fill_width), PROGRESS_BAR_HEIGHT,
            True, self.renderer.blue()
        )
        

    def render_custom_sandbox_ui(self, rlbot_game_state):
        """Render the custom sandbox UI"""
        if self.game_state.game_phase not in CUSTOM_MODES:
            return
        
        # Determine object name
        object_name = ""
        if self.game_state.game_phase == ScenarioPhase.CUSTOM_OFFENSE:
            object_name = "Offensive Car"
        elif self.game_state.game_phase == ScenarioPhase.CUSTOM_BALL:
            object_name = "Ball"
        elif self.game_state.game_phase == ScenarioPhase.CUSTOM_DEFENSE:
            object_name = "Defensive Car"
        
        # Instruction text
        text = f"""Custom Mode Sandbox: {object_name}
[x] modify x coordinate
[y] modify y coordinate
[z] modify z coordinate
[p] modify pitch
[y] modify yaw
[r] modify roll
[v] modify velocity
[n] next step
[b] previous step"""
        
        self.renderer.begin_rendering()
        
        # Main instruction box
        self.renderer.draw_rect_2d(
            CUSTOM_MODE_MENU_START_X, CUSTOM_MODE_MENU_START_Y,
            CUSTOM_MODE_MENU_WIDTH, CUSTOM_MODE_MENU_HEIGHT,
            True, self.renderer.black()
        )
        self.renderer.draw_string_2d(
            CUSTOM_MODE_MENU_START_X, CUSTOM_MODE_MENU_START_Y,
            1, 1, text, self.renderer.white()
        )
        
        # Controls box
        controls_start_y = CUSTOM_MODE_MENU_START_Y + CUSTOM_MODE_MENU_HEIGHT + 100
        self.renderer.draw_rect_2d(
            CUSTOM_MODE_MENU_START_X, controls_start_y,
            CONTROLS_MENU_WIDTH, CONTROLS_MENU_HEIGHT,
            True, self.renderer.black()
        )
        
        controls_text = f"""Controls (use arrow keys)
           ^ +{self.game_state.custom_updown_selection.name}
 -{self.game_state.custom_leftright_selection.name}<            >+{self.game_state.custom_leftright_selection.name}
           v -{self.game_state.custom_updown_selection.name}"""
        
        self.renderer.draw_string_2d(
            CUSTOM_MODE_MENU_START_X, controls_start_y,
            1, 1, controls_text, self.renderer.white()
        )
        
        # Render velocity vectors
        self._render_velocity_vectors(rlbot_game_state)
        
        self.renderer.end_rendering()
    
    def _render_velocity_vectors(self, rlbot_game_state):
        """Render velocity vectors for all objects in custom mode"""
        if not rlbot_game_state:
            return
        
        from state.game_state import CarIndex
        
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
