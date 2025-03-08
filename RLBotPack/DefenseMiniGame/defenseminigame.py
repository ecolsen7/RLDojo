import numpy as np
from enum import Enum
import keyboard

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
from scenario import Scenario, OffensiveMode, DefensiveMode
import utils
class Phase(Enum):
    PAUSED = -1
    SETUP = 0
    ACTIVE = 1
    SCORED = 2
    MENU = 3
    CUSTOM_OFFENSE = 4
    CUSTOM_BALL = 5
    CUSTOM_DEFENSE = 6

CUSTOM_MODES = [
    Phase.CUSTOM_OFFENSE,
    Phase.CUSTOM_BALL,
    Phase.CUSTOM_DEFENSE
]

class CarIndex(Enum):
    BLUE = 0
    ORANGE = 1
    HUMAN = 0
    BOT = 1

class CustomUpDownSelection(Enum):
    Y = 1
    Z = 2
    PITCH = 3
    VELOCITY = 4

class CustomLeftRightSelection(Enum):
    X = 1
    YAW = 2
    ROLL = 3

class DefenseMiniGame(BaseScript):
    '''
    Defense MiniGame is a RLBot script
    the goal it to defend
    '''
    def __init__(self):
        super().__init__("DefenseMiniGame")
        self.game_phase = Phase.SETUP
        self.offensive_mode = OffensiveMode.POSSESSION
        self.defensive_mode = DefensiveMode.NEAR_SHADOW
        self.custom_updown_selection = CustomUpDownSelection.Y
        self.custom_leftright_selection = CustomLeftRightSelection.X
        self.scenario_history = []
        self.freeze_scenario = False
        self.freeze_scenario_index = 0
        self.timeout = 10.0
        self.mirrored = False
        self.scoreDiff_prev = 0
        self.omusDefeat_prev = 0
        self.prev_ticks = 0
        self.ticks = 0
        self.disable_goal_reset = False
        self.pause_time = 1 # Can increase if hard coded kickoffs are causing issues
        self.cur_time = 0
        self.scored_time = 0
        self.first_kickoff = True
        self.state_buffer = np.empty((0,37))
        self.blue_omus = False
        self.record_omus = False
        self.text2 = self.kickoff_countdown = ""
        # self.circle = [(round(np.cos(2*np.pi/120*x)*1200),round(np.sin(2*np.pi/120*x)*1200),15) for x in range(0,120+1)]
        self.horz_ball_var = 'Off' # horizontal ball variance
        self.vert_ball_var = 'Off' # vertical ball variance
        self.ball_preview = 'Off' # show how the ball will move before kickoff commences
        self.standard_kickoffs = 'Off'
        self.error_timer = 0
        self.circle = [(round(np.cos(2*np.pi/120*x)*1200),round(np.sin(2*np.pi/120*x)*1200),15) for x in range(0,120+1)]

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
                # initialise reading keyboard for menu selection
                keyboard.add_hotkey('m', self.menu_toggle)
                keyboard.add_hotkey('0', self.clear_score)
                keyboard.add_hotkey('1', self.mirror_toggle)
                keyboard.add_hotkey('o', self.cycle_offensive_mode)
                keyboard.add_hotkey('d', self.cycle_defensive_mode)
                keyboard.add_hotkey('f', self.freeze_scenario_toggle)
                # keyboard.add_hotkey('z', self.decrease_freeze_scenario_index)
                # keyboard.add_hotkey('x', self.increase_freeze_scenario_index)
                keyboard.add_hotkey('i', self.decrease_timeout)
                keyboard.add_hotkey('u', self.increase_timeout)
                keyboard.add_hotkey('c', self.create_custom_mode)
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
                keyboard.add_hotkey('y', self.custom_select_yaw)
                keyboard.add_hotkey('r', self.custom_select_roll)
                keyboard.add_hotkey('v', self.custom_select_velocity)
                keyboard.add_hotkey('+', self.increase_velocity)
                keyboard.add_hotkey('-', self.decrease_velocity)
            self.pause_time = 1

            # rendering
            if self.game_phase not in [Phase.MENU, *CUSTOM_MODES]:
                self.do_rendering()

            match self.game_phase:
                case Phase.SCORED:
                    self.game_phase = Phase.SETUP

                # This is where we set up the scenario and set the game state
                case Phase.SETUP:
                    self.set_next_game_state()

                    self.prev_time = self.cur_time
                    self.game_phase = Phase.PAUSED

                # Freeze the game while the menu is open
                case Phase.MENU:
                    self.set_game_state(self.game_state)
                    self.menu_rendering()

                # A small pause to prep the player and wait for goal scored to expire
                case Phase.PAUSED:
                    if (self.cur_time - self.prev_time) < self.pause_time or self.goal_scored(packet) or packet.game_info.is_kickoff_pause:
                        self.set_game_state(self.game_state)
                    else:
                        self.game_phase = Phase.ACTIVE

                # Phase in which the scenario plays out
                case Phase.ACTIVE:
                    if self.disable_goal_reset == True:
                        if self.goal_scored(packet):
                            self.game_phase = Phase.SETUP
                    if packet.game_info.is_kickoff_pause:
                        self.game_phase = Phase.SETUP

                    # Only timeout if the ball has touched the ground
                    if (self.cur_time - self.prev_time) > self.timeout:
                        if packet.game_ball.physics.location.z < 100:
                            # Add a goal to the defensive team
                            self.score_for_team(1 if self.mirrored else 0)
                            self.game_phase = Phase.SCORED
                            self.scored_time = self.cur_time
                
                case Phase.CUSTOM_OFFENSE:
                    self.custom_sandbox_rendering()
                    self.set_game_state(self.game_state)

                case Phase.CUSTOM_BALL:
                    self.custom_sandbox_rendering()
                    self.set_game_state(self.game_state)

                case Phase.CUSTOM_DEFENSE:
                    self.custom_sandbox_rendering()
                    self.set_game_state(self.game_state)

                case _:
                    pass

    def set_next_game_state(self):
        if not self.freeze_scenario:
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
        color = self.renderer.yellow()
        color2 = self.renderer.lime()
        text = f"Welcome to the HumanGym. Press 'm' to enter menu"
        self.game_interface.renderer.begin_rendering()
        self.game_interface.renderer.draw_polyline_3d(self.circle, color)
        self.game_interface.renderer.draw_string_2d(20, 50, 1, 1, text, color)
        self.game_interface.renderer.end_rendering()

    def menu_rendering(self):
        text = f"Welcome to the HumanGym! Press [m] to exit menu\r\n\
        \n[0] reset score\
        \n[1] toggle human on offense: {self.mirrored}\
        \n[d/i] decrease/increase timeout seconds: {self.timeout}\
        \n[f] freeze scenario: {self.freeze_scenario}\
        \n[z/x] cycle through scenarios {self.freeze_scenario_index}\
        \n[o] cycle offensive mode\
        \n[d] cycle defensive mode\
        "
        offensive_text = "Offense Mode:"
        for mode in OffensiveMode:
            offensive_text += f"\n{mode.name} {'<--' if self.offensive_mode == mode else ''}"
        defensive_text = "Defense Mode:"
        for mode in DefensiveMode:
            defensive_text += f"\n{mode.name} {'<--' if self.defensive_mode == mode else ''}"
        custom_modes_text = "Custom Modes:"
        # for mode in CustomMode:
        #     custom_modes_text += f"\n{mode.name} {'<--' if self.custom_mode == mode else ''}"
        self.game_interface.renderer.begin_rendering()
        MENU_START_X = 20
        MENU_START_Y = 400
        MENU_WIDTH = 500
        MENU_HEIGHT = 500
        self.renderer.draw_rect_2d(MENU_START_X, MENU_START_Y, MENU_WIDTH, MENU_HEIGHT, False, self.renderer.black())
        self.game_interface.renderer.draw_string_2d(MENU_START_X + 20, MENU_START_Y + 20, 1, 1, text, self.renderer.white())
        self.game_interface.renderer.draw_string_2d(MENU_START_X + 20, MENU_START_Y + 220, 1, 1, offensive_text, self.renderer.white())
        self.game_interface.renderer.draw_string_2d(MENU_START_X + 200, MENU_START_Y + 220, 1, 1, defensive_text, self.renderer.white())
        self.game_interface.renderer.draw_string_2d(MENU_START_X + 380, MENU_START_Y + 220, 1, 1, custom_modes_text, self.renderer.white())
        self.game_interface.renderer.end_rendering()

    def custom_sandbox_rendering(self):
        object_name = ""
        if self.game_phase == Phase.CUSTOM_OFFENSE:
            object_name = "Offensive Car"
        elif self.game_phase == Phase.CUSTOM_BALL:
            object_name = "Ball"
        elif self.game_phase == Phase.CUSTOM_DEFENSE:
            object_name = "Defensive Car"
        # text = f"Custom Mode Sandbox: {object_name}\
        # \n[left/right] move object X\
        # \n[up/down] move object Y\
        # \n[w/s] move object Z\
        # \n[n] next step\
        # \n[b] previous step\
        # \n[p/y/r] change pitch/yaw/roll\
        # "
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
        \n[+/-] increase/decrease velocity\
        "
        CUSTOM_MODE_MENU_START_X = 20
        CUSTOM_MODE_MENU_START_Y = 600
        CUSTOM_MODE_MENU_WIDTH = 300
        CUSTOM_MODE_MENU_HEIGHT = 250
        self.game_interface.renderer.begin_rendering()
        self.renderer.draw_rect_2d(CUSTOM_MODE_MENU_START_X, CUSTOM_MODE_MENU_START_Y, CUSTOM_MODE_MENU_WIDTH, CUSTOM_MODE_MENU_HEIGHT, True, self.renderer.black())
        self.renderer.draw_string_2d(CUSTOM_MODE_MENU_START_X, CUSTOM_MODE_MENU_START_Y, 1, 1, text, self.renderer.white())

        # Render a small menu to show which controls are active
        CONTROLS_MENU_START_X = CUSTOM_MODE_MENU_START_X
        CONTROLS_MENU_START_Y = CUSTOM_MODE_MENU_START_Y + CUSTOM_MODE_MENU_HEIGHT + 100
        CONTROLS_MENU_WIDTH = 500
        CONTROLS_MENU_HEIGHT = CUSTOM_MODE_MENU_HEIGHT
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
    
    def menu_toggle(self):
        if self.game_phase == Phase.MENU:
            self.game_phase = Phase.PAUSED
        else:
            self.game_phase = Phase.MENU

    def down_handler(self):
        if self.custom_updown_selection == CustomUpDownSelection.Y:
            self.decrease_object_y()
        elif self.custom_updown_selection == CustomUpDownSelection.Z:
            self.decrease_object_z()
        elif self.custom_updown_selection == CustomUpDownSelection.PITCH:
            self.modify_pitch(0.1)

    def up_handler(self):
        if self.custom_updown_selection == CustomUpDownSelection.Y:
            self.increase_object_y()
        elif self.custom_updown_selection == CustomUpDownSelection.Z:
            self.increase_object_z()
        elif self.custom_updown_selection == CustomUpDownSelection.PITCH:
            self.modify_pitch(-0.1)

    def left_handler(self):
        if self.custom_leftright_selection == CustomLeftRightSelection.X:
            self.decrease_object_x()
        elif self.custom_leftright_selection == CustomLeftRightSelection.YAW:
            self.modify_yaw(-0.1)
        elif self.custom_leftright_selection == CustomLeftRightSelection.ROLL:
            self.modify_roll(-0.1)

    def right_handler(self):
        if self.custom_leftright_selection == CustomLeftRightSelection.X:
            self.increase_object_x()
        elif self.custom_leftright_selection == CustomLeftRightSelection.YAW:
            self.modify_yaw(0.1)
        elif self.custom_leftright_selection == CustomLeftRightSelection.ROLL:
            self.modify_roll(0.1)


    def create_custom_mode(self):
        self.game_phase = Phase.CUSTOM_OFFENSE

    def modify_object_x(self, x):
        if self.game_phase == Phase.CUSTOM_OFFENSE:
            self.game_state.cars[CarIndex.HUMAN.value].physics.location.x += x
        elif self.game_phase == Phase.CUSTOM_BALL:
            self.game_state.ball.physics.location.x += x
        elif self.game_phase == Phase.CUSTOM_DEFENSE:
            self.game_state.cars[CarIndex.BOT.value].physics.location.x += x
        else:
            pass
        self.set_game_state(self.game_state)

    def decrease_object_x(self):
        self.modify_object_x(-100)

    def increase_object_x(self):
        self.modify_object_x(100)

    def modify_object_y(self, y):
        if self.game_phase == Phase.CUSTOM_OFFENSE:
            self.game_state.cars[CarIndex.HUMAN.value].physics.location.y += y
        elif self.game_phase == Phase.CUSTOM_BALL:
            self.game_state.ball.physics.location.y += y
        elif self.game_phase == Phase.CUSTOM_DEFENSE:
            self.game_state.cars[CarIndex.BOT.value].physics.location.y += y
        else:
            pass
        self.set_game_state(self.game_state)

    def decrease_object_y(self):
        self.modify_object_y(-100)
    
    def increase_object_y(self):
        self.modify_object_y(100)

    def modify_object_z(self, z):
        if self.game_phase == Phase.CUSTOM_OFFENSE:
            self.game_state.cars[CarIndex.HUMAN.value].physics.location.z += z
        elif self.game_phase == Phase.CUSTOM_BALL:
            self.game_state.ball.physics.location.z += z
        elif self.game_phase == Phase.CUSTOM_DEFENSE:
            self.game_state.cars[CarIndex.BOT.value].physics.location.z += z    
        else:
            pass
        self.set_game_state(self.game_state)
    
    def decrease_object_z(self):
        self.modify_object_z(-100)

    def increase_object_z(self):
        self.modify_object_z(100)

    def increase_velocity(self):
        self.modify_velocity(100)

    def decrease_velocity(self):
        self.modify_velocity(-100)

    def next_custom_step(self):
        if self.game_phase == Phase.CUSTOM_OFFENSE:
            self.game_phase = Phase.CUSTOM_BALL
        elif self.game_phase == Phase.CUSTOM_BALL:
            self.game_phase = Phase.CUSTOM_DEFENSE
        elif self.game_phase == Phase.CUSTOM_DEFENSE:
            scenario = Scenario.FromGameState(self.game_state)
            self.scenario_history.append(scenario)
            self.freeze_scenario_index = len(self.scenario_history) - 1
            self.game_phase = Phase.MENU
    
    def prev_custom_step(self):
        if self.game_phase == Phase.CUSTOM_OFFENSE:
            self.game_phase = Phase.MENU
        elif self.game_phase == Phase.CUSTOM_BALL:
            self.game_phase = Phase.CUSTOM_OFFENSE
        elif self.game_phase == Phase.CUSTOM_DEFENSE:
            self.game_phase = Phase.CUSTOM_BALL


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
        
    def modify_velocity(self, velocity):
        # if self.game_phase == Phase.CUSTOM_OFFENSE:
        #     # Scale the 3D velocity vector by the velocity amount
        #     self.game_state.cars[CarIndex.HUMAN.value].physics.velocity = utils.modify_velocity_3d(self.game_state.cars[CarIndex.HUMAN.value].physics.velocity, -10)
        # elif self.game_phase == Phase.CUSTOM_BALL:
        #     self.game_state.ball.physics.velocity = utils.modify_velocity_3d(self.game_state.ball.physics.velocity, -10)
        # elif self.game_phase == Phase.CUSTOM_DEFENSE:
        #     self.game_state.cars[CarIndex.BOT.value].physics.velocity = utils.modify_velocity_3d(self.game_state.cars[CarIndex.BOT.value].physics.velocity, -10)
        
        # self.set_game_state(self.game_state)
        pass
    
    def modify_pitch(self, pitch):
        if self.game_phase == Phase.CUSTOM_OFFENSE:
            self.game_state.cars[CarIndex.HUMAN.value].physics.rotation.pitch += pitch
            self.game_state.cars[CarIndex.HUMAN.value].physics.velocity = utils.get_velocity_vector_from_rotation(self.game_state.cars[CarIndex.HUMAN.value].physics.rotation, 1000, 2000)
        elif self.game_phase == Phase.CUSTOM_BALL:
            # Ball doesn't have rotation, use the velocity components to determine and modify trajectory
            yaw = np.arctan2(self.game_state.ball.physics.velocity.y, self.game_state.ball.physics.velocity.x)
            pitch = np.arctan2(self.game_state.ball.physics.velocity.z, np.sqrt(self.game_state.ball.physics.velocity.x**2 + self.game_state.ball.physics.velocity.y**2))

            # Increase pitch by 0.1
            pitch += 0.1

            # Convert back to velocity components
            self.game_state.ball.physics.velocity = utils.get_velocity_vector_from_rotation(Rotator(yaw=yaw, pitch=pitch, roll=0), 1000, 2000)

        elif self.game_phase == Phase.CUSTOM_DEFENSE:
            self.game_state.cars[CarIndex.BOT.value].physics.rotation.pitch += 0.1
            self.game_state.cars[CarIndex.BOT.value].physics.velocity = utils.get_velocity_vector_from_rotation(self.game_state.cars[CarIndex.BOT.value].physics.rotation, 1000, 2000)

        self.set_game_state(self.game_state)

    def modify_yaw(self, yaw):
        if self.game_phase == Phase.CUSTOM_OFFENSE:
            self.game_state.cars[CarIndex.HUMAN.value].physics.rotation.yaw += yaw
            self.game_state.cars[CarIndex.HUMAN.value].physics.velocity = utils.get_velocity_vector_from_rotation(self.game_state.cars[CarIndex.HUMAN.value].physics.rotation, 1000, 2000)
        elif self.game_phase == Phase.CUSTOM_BALL:
            # Ball doesn't have rotation, use the velocity components to determine and modify trajectory
            yaw = np.arctan2(self.game_state.ball.physics.velocity.y, self.game_state.ball.physics.velocity.x)
            pitch = np.arctan2(self.game_state.ball.physics.velocity.z, np.sqrt(self.game_state.ball.physics.velocity.x**2 + self.game_state.ball.physics.velocity.y**2))

            # Increase yaw by 0.1
            yaw += 0.1

            # Convert back to velocity components
            self.game_state.ball.physics.velocity = utils.get_velocity_vector_from_rotation(Rotator(yaw=yaw, pitch=pitch, roll=0), 1000, 2000)
            
        elif self.game_phase == Phase.CUSTOM_DEFENSE:
            self.game_state.cars[CarIndex.BOT.value].physics.rotation.yaw += yaw
            self.game_state.cars[CarIndex.BOT.value].physics.velocity = utils.get_velocity_vector_from_rotation(self.game_state.cars[CarIndex.BOT.value].physics.rotation, 1000, 2000)

        
        self.set_game_state(self.game_state)

    def modify_roll(self, roll):
        if self.game_phase == Phase.CUSTOM_OFFENSE:
            self.game_state.cars[CarIndex.HUMAN.value].physics.rotation.roll += roll
        elif self.game_phase == Phase.CUSTOM_BALL:
            return
        elif self.game_phase == Phase.CUSTOM_DEFENSE:
            self.game_state.cars[CarIndex.BOT.value].physics.rotation.roll += roll
        self.set_game_state(self.game_state)

    def clear_score(self):
        # This isn't really possible per Discord, no-op for now
        # Will be able to relaunch game in rlbot v5
        pass

    def mirror_toggle(self):
        if self.mirrored:
            self.mirrored = False
        else:
            self.mirrored = True
        
        if self.game_phase != Phase.MENU:
            self.game_phase = Phase.SETUP
        else:
            self.set_next_game_state()

    def cycle_offensive_mode(self):
        if self.game_phase in CUSTOM_MODES:
            return
        
        # Go to the next mode in the enum
        mode_int = OffensiveMode(self.offensive_mode).value
        if mode_int == len(OffensiveMode) - 1:
            self.offensive_mode = OffensiveMode(0)
        else:
            self.offensive_mode = OffensiveMode(mode_int + 1)

        if self.game_phase != Phase.MENU:
            self.game_phase = Phase.SETUP
        else:
            self.set_next_game_state()

    def cycle_defensive_mode(self):
        if self.game_phase in CUSTOM_MODES:
            return
        
        # Go to the next mode in the enum
        mode_int = DefensiveMode(self.defensive_mode).value
        if mode_int == len(DefensiveMode) - 1:
            self.defensive_mode = DefensiveMode(0)
        else:
            self.defensive_mode = DefensiveMode(mode_int + 1)

        if self.game_phase != Phase.MENU:
            self.game_phase = Phase.SETUP
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

        if self.game_phase != Phase.MENU:
            self.game_phase = Phase.SETUP
        else:
            self.set_next_game_state()

    def increase_freeze_scenario_index(self):   
        if self.game_phase in CUSTOM_MODES:
            return
        
        if self.freeze_scenario_index < len(self.scenario_history) - 1:
            self.freeze_scenario_index += 1

        if self.game_phase != Phase.MENU:
            self.game_phase = Phase.SETUP
        else:
            self.set_next_game_state()

# You can use this __name__ == '__main__' thing to ensure that the script doesn't start accidentally if you
# merely reference its module from somewhere
if __name__ == "__main__":
    script = DefenseMiniGame()
    script.run()
