import numpy as np
from enum import Enum
import keyboard
import time

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
from scenario import Scenario, OffensiveMode, DefensiveMode
from menu import MenuRenderer, UIElement
import utils
import race
import records

class CustomUpDownSelection(Enum):
    Y = 1
    Z = 2
    PITCH = 3
    VELOCITY = 4

class CustomLeftRightSelection(Enum):
    X = 1
    YAW = 2
    ROLL = 3

class GymMode(Enum):
    SCENARIO = 1
    RACE = 2


class ScenarioPhase(Enum):
    PAUSED = -1
    SETUP = 0
    ACTIVE = 1
    MENU = 2
    CUSTOM_OFFENSE = 3
    CUSTOM_BALL = 4
    CUSTOM_DEFENSE = 5

class RacePhase(Enum):
    INIT = -1
    SETUP = 0
    ACTIVE = 1
    MENU = 2
    FINISHED = 3

CUSTOM_MODES = [
    ScenarioPhase.CUSTOM_OFFENSE,
    ScenarioPhase.CUSTOM_BALL,
    ScenarioPhase.CUSTOM_DEFENSE
]

class CarIndex(Enum):
    BLUE = 0
    ORANGE = 1
    HUMAN = 0
    BOT = 1

class DefenseMiniGame(BaseScript):
    '''
    Defense MiniGame is a RLBot script
    the goal it to defend
    '''
    def __init__(self):
        super().__init__("HumanGym")
        self.game_phase = ScenarioPhase.SETUP
        # self.ui = HumanGymUI()
        self.menu_renderer = MenuRenderer(self.game_interface.renderer)
        self.offensive_mode = OffensiveMode.POSSESSION
        self.defensive_mode = DefensiveMode.NEAR_SHADOW
        self.custom_updown_selection = CustomUpDownSelection.Y
        self.custom_leftright_selection = CustomLeftRightSelection.X
        self.human_score = 0
        self.bot_score = 0
        self.scenario_history = []
        self.freeze_scenario = False
        self.freeze_scenario_index = 0
        self.timeout = 10.0
        self.mirrored = False
        self.scoreDiff_prev = 0
        self.score_human_prev = 0
        self.score_bot_prev = 0
        self.prev_ticks = 0
        self.ticks = 0
        self.disable_goal_reset = False
        self.pause_time = 1 # Can increase if hard coded kickoffs are causing issues
        self.cur_time = 0
        self.scored_time = 0
        self.started_time = 0
        self.gym_mode = GymMode.SCENARIO
        self.race = None
        self.race_mode_trials = 100
        self.race_mode_previous_record = None

    def run(self):
        while True:
            # when packet available
            packet = self.wait_game_tick_packet()

            # updating packet and tick count
            packet = self.get_game_tick_packet()
            self.cur_time = packet.game_info.seconds_elapsed
            self.ticks += 1

            # check if 'disable goal reset' mutator is active
            if self.ticks == 1:
                match_settings = self.get_match_settings()
                mutators = match_settings.MutatorSettings()
                if mutators.RespawnTimeOption() == 3:
                    self.disable_goal_reset = True
                self.menu_renderer.add_element(UIElement('Main Menu', header=True))
                self.menu_renderer.add_element(UIElement('Reset Score', function=self.clear_score))
                self.menu_renderer.add_element(UIElement('Toggle Mirror', function=self.mirror_toggle))
                self.menu_renderer.add_element(UIElement('Freeze Scenario', function=self.freeze_scenario_toggle))
                self.menu_renderer.add_element(UIElement('Create Custom Mode', function=self.create_custom_mode))

                self.preset_mode_menu = MenuRenderer(self.game_interface.renderer, columns=2)
                self.preset_mode_menu.add_element(UIElement('Offensive Mode', header=True), column=0)
                for mode in OffensiveMode:
                    self.preset_mode_menu.add_element(UIElement(mode.name, function=self.select_offensive_mode, function_args=mode), column=0)
                self.preset_mode_menu.add_element(UIElement('Defensive Mode', header=True), column=1)
                for mode in DefensiveMode:
                    self.preset_mode_menu.add_element(UIElement(mode.name, function=self.select_defensive_mode, function_args=mode), column=1)
                self.menu_renderer.add_element(UIElement('Select Preset Mode', submenu=self.preset_mode_menu))
                # self.menu_renderer.add_element(UIElement('Race Mode', function=self.set_race_mode))
                self.race_mode_menu = MenuRenderer(self.game_interface.renderer)
                self.race_mode_menu.add_element(UIElement('Number of Trials', header=True))
                for option in (1, 10, 25, 50, 100):
                    self.race_mode_menu.add_element(UIElement(str(option), function=self.set_race_mode, function_args=option))
                self.menu_renderer.add_element(UIElement('Race Mode', submenu=self.race_mode_menu))

                # initialise reading keyboard for menu selection
                keyboard.add_hotkey('m', self.menu_toggle)
                keyboard.add_hotkey('left', self.left_handler)
                keyboard.add_hotkey('right', self.right_handler)
                keyboard.add_hotkey('down', self.down_handler)
                keyboard.add_hotkey('up', self.up_handler)
                keyboard.add_hotkey('n', self.next_custom_step)
                keyboard.add_hotkey('b', self.prev_custom_step)
                keyboard.add_hotkey('x', self.custom_select_x)
                keyboard.add_hotkey('y', self.custom_select_y)
                keyboard.add_hotkey('z', self.custom_select_z)
                keyboard.add_hotkey('p', self.custom_select_pitch)
                keyboard.add_hotkey('Y', self.custom_select_yaw)
                keyboard.add_hotkey('r', self.custom_select_roll)
                keyboard.add_hotkey('v', self.custom_select_velocity)
                keyboard.add_hotkey('enter', self.enter_handler)
                
            self.pause_time = 1

            # rendering
            if self.game_phase not in [ScenarioPhase.MENU, *CUSTOM_MODES]:
                self.do_rendering()

            if self.gym_mode == GymMode.RACE:
                self.race_mode(packet)

            elif self.gym_mode == GymMode.SCENARIO:
                self.scenario_mode(packet)

    def race_mode(self, packet):
        match self.game_phase:
            case RacePhase.INIT:
                # Seed the random number generator to get reproducible setups
                np.random.seed(0)

                self.human_score = 0
                self.bot_score = 0

                # Set scored time to now
                self.started_time = self.cur_time
                
                car_states = {}

                # Spawn the player car in the middle of the map
                player_car_state = CarState(physics=Physics(location=Vector3(0, 0, 0), velocity=Vector3(0, 0, 0), rotation=Rotator(0, 0, 0)))
                # Tuck the bot above the map 
                bot_car_state = CarState(physics=Physics(location=Vector3(0, 0, 2500), velocity=Vector3(0, 0, 0), rotation=Rotator(0, 0, 0)))

                car_states[CarIndex.HUMAN.value] = player_car_state
                car_states[CarIndex.BOT.value] = bot_car_state

                self.game_state = GameState(
                    cars=car_states
                )
                self.set_game_state(self.game_state)
                self.game_phase = RacePhase.SETUP
                
            case RacePhase.SETUP:
                self.race = race.Race()
                player_car_state = CarState(physics=packet.game_cars[CarIndex.HUMAN.value].physics)
                ball_state = self.race.BallState()
   
                self.game_state = GameState(
                    ball=ball_state
                )
                self.set_game_state(self.game_state)
                self.game_phase = RacePhase.ACTIVE

            case RacePhase.ACTIVE:
                # Check if the current ball location has moved by 5 or more units, which would set up the next race
                if abs(self.game_state.ball.physics.location.x - packet.game_ball.physics.location.x) > 2 \
                    or abs(self.game_state.ball.physics.location.y - packet.game_ball.physics.location.y) > 2 \
                    or abs(self.game_state.ball.physics.location.z - packet.game_ball.physics.location.z) > 2:
                    self.human_score += 1
                    self.game_phase = RacePhase.SETUP

                    if self.human_score >= self.race_mode_trials:
                        self.game_phase = RacePhase.FINISHED
                        
                # Continue setting the ball location to the race ball location
                ball_state = self.race.BallState()
                car_states = {}
                human_loc_x = packet.game_cars[CarIndex.HUMAN.value].physics.location.x
                human_loc_y = packet.game_cars[CarIndex.HUMAN.value].physics.location.y
                human_loc_z = packet.game_cars[CarIndex.HUMAN.value].physics.location.z
                human_vel_x = packet.game_cars[CarIndex.HUMAN.value].physics.velocity.x
                human_vel_y = packet.game_cars[CarIndex.HUMAN.value].physics.velocity.y
                human_vel_z = packet.game_cars[CarIndex.HUMAN.value].physics.velocity.z
                human_rot_x = packet.game_cars[CarIndex.HUMAN.value].physics.rotation.pitch
                human_rot_y = packet.game_cars[CarIndex.HUMAN.value].physics.rotation.yaw
                human_rot_z = packet.game_cars[CarIndex.HUMAN.value].physics.rotation.roll
                human_car_state = CarState(physics=Physics(location=Vector3(human_loc_x, human_loc_y, human_loc_z), velocity=Vector3(human_vel_x, human_vel_y, human_vel_z), rotation=Rotator(human_rot_x, human_rot_y, human_rot_z)))
                car_states[CarIndex.HUMAN.value] = human_car_state
                car_states[CarIndex.BOT.value] = CarState(physics=Physics(location=Vector3(0, 0, 2500), velocity=Vector3(0, 0, 0), rotation=Rotator(0, 0, 0)))
                self.game_state = GameState(
                    cars=car_states,
                    ball=ball_state
                )
                self.set_game_state(self.game_state)

            case RacePhase.MENU:
                self.set_game_state(self.game_state)
                self.menu_renderer.render_menu()

            case RacePhase.FINISHED:
                self.set_game_state(self.game_state)

                # Save the record
                print("Cur time: ", self.cur_time)
                print("Started time: ", self.started_time)
                print("Time was: ", self.cur_time - self.started_time)
                if self.human_score >= self.race_mode_trials:
                    record = records.RaceRecord(
                        number_of_trials=self.race_mode_trials, 
                        total_time_to_finish=float(self.cur_time - self.started_time)
                    )
                    records.update_race_record_if_faster(record)

                time.sleep(10)
                self.game_phase = RacePhase.INIT

    def scenario_mode(self, packet):
        match self.game_phase:
            # This is where we set up the scenario and set the game state
            case ScenarioPhase.SETUP:
                self.set_next_game_state()

                self.prev_time = self.cur_time
                self.game_phase = ScenarioPhase.PAUSED

            # Freeze the game while the menu is open
            case ScenarioPhase.MENU:
                self.set_game_state(self.game_state)
                # self.menu_rendering()
                self.menu_renderer.render_menu()

            # A small pause to prep the player and wait for goal scored to expire
            case ScenarioPhase.PAUSED:
                if (self.cur_time - self.prev_time) < self.pause_time or self.goal_scored(packet) or packet.game_info.is_kickoff_pause:
                    self.set_game_state(self.game_state)
                else:
                    self.game_phase = ScenarioPhase.ACTIVE

            # Phase in which the scenario plays out
            case ScenarioPhase.ACTIVE:
                if self.disable_goal_reset == True:
                    if self.goal_scored(packet):
                        # Add goal to whichever team scored
                        team_scored = self.get_team_scored(packet)
                        if team_scored == CarIndex.HUMAN.value:
                            self.human_score += 1
                        else:
                            self.bot_score += 1
                        self.game_phase = ScenarioPhase.SETUP
                        return
                    
                if packet.game_info.is_kickoff_pause:
                    self.game_phase = ScenarioPhase.SETUP

                # Only timeout if the ball has touched the ground
                if (self.cur_time - self.prev_time) > self.timeout:
                    if packet.game_ball.physics.location.z < 100:
                        # Add a goal to the defensive team
                        self.score_for_team(CarIndex.BOT.value if self.mirrored else CarIndex.HUMAN.value)
                        if self.mirrored:
                            self.bot_score += 1
                        else:
                            self.human_score += 1
                        self.game_phase = ScenarioPhase.SETUP
                        self.scored_time = self.cur_time
            
            case ScenarioPhase.CUSTOM_OFFENSE:
                self.custom_sandbox_rendering()
                self.set_game_state(self.game_state)

            case ScenarioPhase.CUSTOM_BALL:
                self.custom_sandbox_rendering()
                self.set_game_state(self.game_state)

            case ScenarioPhase.CUSTOM_DEFENSE:
                self.custom_sandbox_rendering()
                self.set_game_state(self.game_state)

            case _:
                pass


    def set_next_game_state(self):
        if not self.freeze_scenario:
            print("setting next game state: ", self.offensive_mode, self.defensive_mode)
            scenario = Scenario(self.offensive_mode, self.defensive_mode)
            if self.mirrored:
                scenario.Mirror()
            self.scenario_history.append(scenario)
            self.freeze_scenario_index = len(self.scenario_history) - 1
        else:
            scenario = self.scenario_history[self.freeze_scenario_index]
        self.game_state = scenario.GetGameState()
        self.set_game_state(self.game_state)
            
    def score_for_team(self, team):
        if team == 0:
            ball_y_side = 1
        else:
            ball_y_side = -1
        ball_state = BallState(Physics(location=Vector3(0, 5500 * ball_y_side, 325)))
        self.set_game_state(GameState(ball=ball_state))

    def do_rendering(self):
        minutes_since_start = int((self.cur_time - self.started_time) // 60)
        seconds_since_start = int((self.cur_time - self.started_time) % 60)
        seconds_str = str(seconds_since_start)
        if seconds_since_start < 10:
            seconds_str = "0" + seconds_str
        color = self.renderer.yellow()
        score_box_start_x = 50
        score_box_start_y = 100
        score_box_width = 240
        score_box_height = 130
        text = f"Welcome to the HumanGym. Press 'm' to enter menu"
        previous_record = f"No record"
        if self.gym_mode == GymMode.SCENARIO:
            scores = f"Human: {self.human_score} Bot: {self.bot_score}"
            total_score = f"Total: {self.human_score + self.bot_score}"
            time_since_start = f"Time: {minutes_since_start}:{seconds_str}"
            previous_record = ""
        elif self.gym_mode == GymMode.RACE:
            scores = f"Completed: {self.human_score}"
            total_score = f"Out of: {self.race_mode_trials}"
            time_since_start = f"Time: {minutes_since_start}:{seconds_str}"
            if self.race_mode_previous_record:
                minutes_previous_record_str = str(int(self.race_mode_previous_record // 60))
                seconds_previous_record_str = str(int(self.race_mode_previous_record % 60))
                previous_record = f"Previous Record: {minutes_previous_record_str}:{seconds_previous_record_str}"
        self.game_interface.renderer.begin_rendering()
        self.game_interface.renderer.draw_string_2d(20, 50, 1, 1, text, color)
        self.game_interface.renderer.draw_rect_2d(score_box_start_x, score_box_start_y, score_box_width, score_box_height, True, self.renderer.white())
        self.game_interface.renderer.draw_string_2d(score_box_start_x + 10, score_box_start_y + 10, 1, 1, scores, self.renderer.black())
        self.game_interface.renderer.draw_string_2d(score_box_start_x + 10, score_box_start_y + 40, 1, 1, total_score, self.renderer.black())
        self.game_interface.renderer.draw_string_2d(score_box_start_x + 10, score_box_start_y + 70, 1, 1, time_since_start, self.renderer.black())
        self.game_interface.renderer.draw_string_2d(score_box_start_x + 10, score_box_start_y + 100, 1, 1, previous_record, self.renderer.black())

        self.game_interface.renderer.end_rendering()

    def custom_sandbox_rendering(self):
        object_name = ""
        if self.game_phase == ScenarioPhase.CUSTOM_OFFENSE:
            object_name = "Offensive Car"
        elif self.game_phase == ScenarioPhase.CUSTOM_BALL:
            object_name = "Ball"
        elif self.game_phase == ScenarioPhase.CUSTOM_DEFENSE:
            object_name = "Defensive Car"
        text = f"Custom Mode Sandbox: {object_name}\
        \n[x] modify x coordinate\
        \n[y] modify y coordinate\
        \n[z] modify z coordinate\
        \n[p] modify pitch\
        \n[y] modify yaw\
        \n[r] modify roll\
        \n[v] modify velocity\
        \n[n] next step\
        \n[b] previous step\
        "
        CUSTOM_MODE_MENU_START_X = 20
        CUSTOM_MODE_MENU_START_Y = 600
        CUSTOM_MODE_MENU_WIDTH = 400
        CUSTOM_MODE_MENU_HEIGHT = 200
        self.game_interface.renderer.begin_rendering()
        self.renderer.draw_rect_2d(CUSTOM_MODE_MENU_START_X, CUSTOM_MODE_MENU_START_Y, CUSTOM_MODE_MENU_WIDTH, CUSTOM_MODE_MENU_HEIGHT, True, self.renderer.black())
        self.renderer.draw_string_2d(CUSTOM_MODE_MENU_START_X, CUSTOM_MODE_MENU_START_Y, 1, 1, text, self.renderer.white())

        # Render a small menu to show which controls are active
        CONTROLS_MENU_START_X = CUSTOM_MODE_MENU_START_X
        CONTROLS_MENU_START_Y = CUSTOM_MODE_MENU_START_Y + CUSTOM_MODE_MENU_HEIGHT + 100
        CONTROLS_MENU_WIDTH = 350
        CONTROLS_MENU_HEIGHT = 200
        self.renderer.draw_rect_2d(CONTROLS_MENU_START_X, CONTROLS_MENU_START_Y, CONTROLS_MENU_WIDTH, CONTROLS_MENU_HEIGHT, True, self.renderer.black())
        controls_text = f"Controls (use arrow keys)\
        \n           ^ +{self.custom_updown_selection.name}\
        \n -{self.custom_leftright_selection.name}<            >+{self.custom_leftright_selection.name}\
        \n           v -{self.custom_updown_selection.name}\
        "
        self.renderer.draw_string_2d(CONTROLS_MENU_START_X, CONTROLS_MENU_START_Y, 1, 1, controls_text, self.renderer.white())
        # Also render the velocity of all objects 
        # Do this by adding the velocity vector to the location vector
        human_car_start_vector = self.game_state.cars[CarIndex.HUMAN.value].physics.location
        human_car_start = utils.vector3_to_list(human_car_start_vector)
        human_car_end_vector = utils.add_vector3(human_car_start_vector, self.game_state.cars[CarIndex.HUMAN.value].physics.velocity)
        human_car_end = utils.vector3_to_list(human_car_end_vector)
        self.renderer.draw_line_3d(human_car_start, human_car_end, self.renderer.white())

        ball_start_vector = self.game_state.ball.physics.location
        ball_start = utils.vector3_to_list(ball_start_vector)
        ball_end_vector = utils.add_vector3(ball_start_vector, self.game_state.ball.physics.velocity)
        ball_end = utils.vector3_to_list(ball_end_vector)
        self.renderer.draw_line_3d(ball_start, ball_end, self.renderer.white())

        bot_car_start_vector = self.game_state.cars[CarIndex.BOT.value].physics.location
        bot_car_start = utils.vector3_to_list(bot_car_start_vector)
        bot_car_end_vector = utils.add_vector3(bot_car_start_vector, self.game_state.cars[CarIndex.BOT.value].physics.velocity)
        bot_car_end = utils.vector3_to_list(bot_car_end_vector)
        self.renderer.draw_line_3d(bot_car_start, bot_car_end, self.renderer.white())

        self.game_interface.renderer.end_rendering()
        
    def goal_scored(self, packet):
        # check if goal in last tick
        teamScores = tuple(map(lambda x: x.score, packet.teams))
        scoreDiff = max(teamScores) - min(teamScores)

        if scoreDiff != self.scoreDiff_prev:
            self.scoreDiff_prev = scoreDiff
            return True
        return False

    def get_team_scored(self, packet):
        teamScores = tuple(map(lambda x: x.score, packet.teams))
        human_score = teamScores[CarIndex.HUMAN.value]
        bot_score = teamScores[CarIndex.BOT.value]
        
        team = CarIndex.HUMAN.value if human_score > self.score_human_prev else CarIndex.BOT.value
        
        self.score_human_prev = human_score
        self.score_bot_prev = bot_score
        return team
    
    def menu_toggle(self):
        match self.gym_mode:
            case GymMode.RACE:
                if self.game_phase == RacePhase.MENU:
                    self.game_phase = RacePhase.ACTIVE
                else:
                    self.game_phase = RacePhase.MENU
            case GymMode.SCENARIO:
                if self.game_phase == ScenarioPhase.MENU:
                    self.game_phase = ScenarioPhase.PAUSED
                else:
                    self.game_phase = ScenarioPhase.MENU


    ##################################
    ### Directional Input Handlers ###
    ##################################
    
    def down_handler(self):
        if self.game_phase in CUSTOM_MODES:
            # Get object to modify
            object_to_modify = None
            match self.game_phase:
                case ScenarioPhase.CUSTOM_OFFENSE:
                    object_to_modify = self.game_state.cars[CarIndex.HUMAN.value]
                case ScenarioPhase.CUSTOM_BALL:
                    object_to_modify = self.game_state.ball
                case ScenarioPhase.CUSTOM_DEFENSE:
                    object_to_modify = self.game_state.cars[CarIndex.BOT.value]
            
            match self.custom_updown_selection:
                case CustomUpDownSelection.Y:
                    self.modify_object_y(object_to_modify, -100)
                case CustomUpDownSelection.Z:
                    self.modify_object_z(object_to_modify, -100)
                case CustomUpDownSelection.PITCH:
                    self.modify_pitch(object_to_modify, 0.1)
                case CustomUpDownSelection.VELOCITY:
                    self.modify_velocity(object_to_modify, -0.1)
            self.set_game_state(self.game_state)
        else:
            # self.decrease_timeout()
            self.menu_renderer.select_next_element()

    def up_handler(self):
        if self.game_phase in CUSTOM_MODES:
            # Get object to modify
            object_to_modify = None
            match self.game_phase:
                case ScenarioPhase.CUSTOM_OFFENSE:
                    object_to_modify = self.game_state.cars[CarIndex.HUMAN.value]
                case ScenarioPhase.CUSTOM_BALL:
                    object_to_modify = self.game_state.ball
                case ScenarioPhase.CUSTOM_DEFENSE:
                    object_to_modify = self.game_state.cars[CarIndex.BOT.value]
            
            match self.custom_updown_selection:
                case CustomUpDownSelection.Y:
                    self.modify_object_y(object_to_modify, 100)
                case CustomUpDownSelection.Z:
                    self.modify_object_z(object_to_modify, 100)
                case CustomUpDownSelection.PITCH:
                    self.modify_pitch(object_to_modify, -0.1)
                case CustomUpDownSelection.VELOCITY:
                    self.modify_velocity(object_to_modify, 0.1)
            self.set_game_state(self.game_state)
        else:
            # self.increase_timeout()
            self.menu_renderer.select_last_element()

    def left_handler(self):
        if self.game_phase in CUSTOM_MODES:
            # Get object to modify
            object_to_modify = None
            match self.game_phase:
                case ScenarioPhase.CUSTOM_OFFENSE:
                    object_to_modify = self.game_state.cars[CarIndex.HUMAN.value]
                case ScenarioPhase.CUSTOM_BALL:
                    object_to_modify = self.game_state.ball
                case ScenarioPhase.CUSTOM_DEFENSE:
                    object_to_modify = self.game_state.cars[CarIndex.BOT.value]
            
            match self.custom_leftright_selection:
                case CustomLeftRightSelection.X:
                    self.modify_object_x(object_to_modify, -100)
                case CustomLeftRightSelection.YAW:
                    self.modify_yaw(object_to_modify, -0.1)
                case CustomLeftRightSelection.ROLL:
                    self.modify_roll(object_to_modify, -0.1)
            self.set_game_state(self.game_state)
        else:
            # self.decrease_freeze_scenario_index()
            self.menu_renderer.move_to_prev_column()

    def right_handler(self):
        if self.game_phase in CUSTOM_MODES:
            # Get object to modify
            object_to_modify = None
            match self.game_phase:
                case ScenarioPhase.CUSTOM_OFFENSE:
                    object_to_modify = self.game_state.cars[CarIndex.HUMAN.value]
                case ScenarioPhase.CUSTOM_BALL:
                    object_to_modify = self.game_state.ball
                case ScenarioPhase.CUSTOM_DEFENSE:
                    object_to_modify = self.game_state.cars[CarIndex.BOT.value]
            
            match self.custom_leftright_selection:
                case CustomLeftRightSelection.X:
                    self.modify_object_x(object_to_modify, 100)
                case CustomLeftRightSelection.YAW:
                    self.modify_yaw(object_to_modify, 0.1)
                case CustomLeftRightSelection.ROLL:
                    self.modify_roll(object_to_modify, 0.1)
            self.set_game_state(self.game_state)
        else:
            # self.increase_freeze_scenario_index()
            self.menu_renderer.move_to_next_column()

    def enter_handler(self):
        self.menu_renderer.enter_element()


    ###########################
    ### Menu Input Handlers ###
    ###########################

    def clear_score(self):
        self.human_score = 0
        self.bot_score = 0

    def mirror_toggle(self):
        if self.mirrored:
            self.mirrored = False
        else:
            self.mirrored = True
        
        if self.game_phase != ScenarioPhase.MENU:
            self.game_phase = ScenarioPhase.SETUP
        else:
            self.set_next_game_state()

    def select_offensive_mode(self, mode):
        print(f"Selecting offensive mode: {mode}")
        self.offensive_mode = mode
        if self.game_phase != ScenarioPhase.MENU:
            self.game_phase = ScenarioPhase.SETUP
        else:
            self.set_next_game_state()

    def select_defensive_mode(self, mode):
        print(f"Selecting defensive mode: {mode}")
        self.defensive_mode = mode
        if self.game_phase != ScenarioPhase.MENU:
            self.game_phase = ScenarioPhase.SETUP
        else:
            self.set_next_game_state()


    def decrease_timeout(self):
        if self.game_phase in CUSTOM_MODES:
            return
        
        self.timeout -= 1

    def increase_timeout(self):
        if self.game_phase in CUSTOM_MODES:
            return
        
        self.timeout += 1
        
    def freeze_scenario_toggle(self):
        if self.game_phase in CUSTOM_MODES:
            return
        
        self.freeze_scenario = not self.freeze_scenario

    def decrease_freeze_scenario_index(self):
        if self.game_phase in CUSTOM_MODES:
            return
        
        if self.freeze_scenario_index > 0:
            self.freeze_scenario_index -= 1

        if self.game_phase != ScenarioPhase.MENU:
            self.game_phase = ScenarioPhase.SETUP
        else:
            self.set_next_game_state()

    def increase_freeze_scenario_index(self):   
        if self.game_phase in CUSTOM_MODES:
            return
        
        if self.freeze_scenario_index < len(self.scenario_history) - 1:
            self.freeze_scenario_index += 1

        if self.game_phase != ScenarioPhase.MENU:
            self.game_phase = ScenarioPhase.SETUP
        else:
            self.set_next_game_state()

    def create_custom_mode(self):
        self.game_phase = ScenarioPhase.CUSTOM_OFFENSE

    def set_race_mode(self, trials):
        print(f"Setting race mode")
        self.gym_mode = GymMode.RACE
        self.game_phase = RacePhase.INIT
        self.race_mode_trials = trials
        self.race_mode_previous_record = records.get_race_record(trials)


    #######################################
    ### Custom Mode Menu Input Handlers ###
    #######################################

    def next_custom_step(self):
        if self.game_phase == ScenarioPhase.CUSTOM_OFFENSE:
            self.game_phase = ScenarioPhase.CUSTOM_BALL
        elif self.game_phase == ScenarioPhase.CUSTOM_BALL:
            self.game_phase = ScenarioPhase.CUSTOM_DEFENSE
        elif self.game_phase == ScenarioPhase.CUSTOM_DEFENSE:
            scenario = Scenario.FromGameState(self.game_state)
            self.scenario_history.append(scenario)
            self.freeze_scenario_index = len(self.scenario_history) - 1
            self.game_phase = ScenarioPhase.MENU
    
    def prev_custom_step(self):
        if self.game_phase == ScenarioPhase.CUSTOM_OFFENSE:
            self.game_phase = ScenarioPhase.MENU
        elif self.game_phase == ScenarioPhase.CUSTOM_BALL:
            self.game_phase = ScenarioPhase.CUSTOM_OFFENSE
        elif self.game_phase == ScenarioPhase.CUSTOM_DEFENSE:
            self.game_phase = ScenarioPhase.CUSTOM_BALL


    def custom_select_x(self):
        self.custom_leftright_selection = CustomLeftRightSelection.X

    def custom_select_yaw(self):
        self.custom_leftright_selection = CustomLeftRightSelection.YAW

    def custom_select_roll(self):
        self.custom_leftright_selection = CustomLeftRightSelection.ROLL

    def custom_select_y(self):
        self.custom_updown_selection = CustomUpDownSelection.Y

    def custom_select_z(self):
        self.custom_updown_selection = CustomUpDownSelection.Z

    def custom_select_pitch(self):
        self.custom_updown_selection = CustomUpDownSelection.PITCH

    def custom_select_velocity(self):
        self.custom_updown_selection = CustomUpDownSelection.VELOCITY
        

# You can use this __name__ == '__main__' thing to ensure that the script doesn't start accidentally if you
# merely reference its module from somewhere
if __name__ == "__main__":
    script = DefenseMiniGame()
    script.run()
