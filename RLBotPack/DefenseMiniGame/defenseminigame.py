import numpy as np
from enum import Enum
import keyboard

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState

class Phase(Enum):
    PAUSED = -1
    SETUP = 0
    ACTIVE = 1
    SCORED = 2

class GameMode(Enum):
    SHADOW = 0
    NET = 1
    SHOT = 2
    SIDEWALL = 3
    CARRY = 4

class DefenseMiniGame(BaseScript):
    '''
    Defense MiniGame is a RLBot script
    the goal it to defend
    '''
    def __init__(self):
        super().__init__("DefenseMiniGame")
        self.game_phase = Phase.SETUP
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
                keyboard.add_hotkey('1', self.mirror_toggle) 
                keyboard.add_hotkey('2', self.set_shadow_mode)
                keyboard.add_hotkey('3', self.set_net_mode)
                keyboard.add_hotkey('4', self.set_shot_mode)
                keyboard.add_hotkey('5', self.set_sidewall_mode)
                keyboard.add_hotkey('6', self.set_carry_mode)
            
            # for standard kickoff, allow time for boost pads to respawn
            if self.standard_kickoffs == 'On':
                self.pause_time = 4
            else:
                self.pause_time = 1

            # rendering
            self.do_rendering()

            # match statement state machine for game phase
            match self.game_phase:
                case Phase.SCORED:
                    self.game_phase = Phase.SETUP
                case Phase.SETUP:
                    if self.game_mode == GameMode.SHADOW:
                        self.setup_shadow_defense(packet)
                    elif self.game_mode == GameMode.NET:
                        self.setup_net_defense(packet)
                    elif self.game_mode == GameMode.SHOT:
                        self.setup_shot_defense(packet)
                    elif self.game_mode == GameMode.SIDEWALL:
                        self.setup_sidewall_defense(packet)
                    elif self.game_mode == GameMode.CARRY:
                        self.setup_carry_defense(packet)
                    self.game_phase = Phase.PAUSED
                case Phase.PAUSED:
                    if (self.cur_time - self.prev_time) < self.pause_time or self.goal_scored(packet) or packet.game_info.is_kickoff_pause:
                        self.set_game_state(self.game_state)
                    else:
                        self.game_phase = Phase.ACTIVE
                case Phase.ACTIVE:
                    if self.disable_goal_reset == True:
                        if self.goal_scored(packet):
                            self.game_phase = Phase.SETUP
                    if packet.game_info.is_kickoff_pause:
                        self.game_phase = Phase.SETUP
                    if (self.cur_time - self.prev_time) > 10.0:
                        # Add a goal to the defensive team
                        self.score_for_team(1 if self.mirrored else 0)
                        self.game_phase = Phase.SCORED
                        self.scored_time = self.cur_time
                case _:
                    pass
            
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
        text = f"Omus is about GrandChamp for the base 50-MiniGame\
        \nSearch 'omus setup' in RLBot discord if you are having issues\
        \n'1' toggle mirrored: {self.mirrored}\
        \n'2' set gamemode to shadow: {self.game_mode}\
        \n'3' set gamemode to net: {self.game_mode}\
        \n'4' set gamemode to shot: {self.game_mode}\
        \n'5' set gamemode to sidewall: {self.game_mode}\
        \n'6' set gamemode carry: {self.game_mode}"
        self.game_interface.renderer.begin_rendering()
        self.game_interface.renderer.draw_polyline_3d(self.circle, color)
        self.game_interface.renderer.draw_string_2d(20, 50, 1, 1, text, color)
        self.game_interface.renderer.draw_string_2d(900, 420, 5, 5, self.kickoff_countdown, color2)
        self.game_interface.renderer.draw_string_2d(900, 420, 5, 5, self.kickoff_countdown, color2)
        self.game_interface.renderer.draw_string_2d(900, 420, 5, 5, self.kickoff_countdown, color2)
        # self.game_interface.renderer.draw_string_2d(20, 200, 1, 1, self.text2 if self.cur_time-self.error_timer < 3 else "" , color) - Currently Unavailable
        self.game_interface.renderer.end_rendering()

    def goal_scored(self, packet):
        # check if goal in last tick
        teamScores = tuple(map(lambda x: x.score, packet.teams))
        scoreDiff = max(teamScores) - min(teamScores)

        if scoreDiff != self.scoreDiff_prev:
            self.scoreDiff_prev = scoreDiff
            return True
        return False

    # Set up car and ball states based on predefined scenarios
    # Y = 5100 is the goal line
    # X = +/-850 is the goal post
    def setup_shadow_defense(self, packet):       
        car_states = {}
        play_yaw, play_yaw_mir = self.get_play_yaw()

        # Add a small random angle to the yaw of each car
        if self.mirrored:
            offensive_car_yaw = play_yaw_mir + self.random_between(-0.1*np.pi, 0.1*np.pi)
            defensive_car_yaw = play_yaw_mir + self.random_between(-0.1*np.pi, 0.1*np.pi)
        else:
            offensive_car_yaw = play_yaw + self.random_between(-0.1*np.pi, 0.1*np.pi)
            defensive_car_yaw = play_yaw + self.random_between(-0.1*np.pi, 0.1*np.pi)

        # Get the momentum from the yaw
        offensive_car_velocity = self.get_velocity_from_yaw(offensive_car_yaw, min_velocity=800, max_velocity=1200)
        defensive_car_velocity = self.get_velocity_from_yaw(defensive_car_yaw, min_velocity=800, max_velocity=1200)

        if self.mirrored:
            ball_velocity = self.get_velocity_from_yaw(play_yaw_mir)
        else:
            ball_velocity = self.get_velocity_from_yaw(play_yaw)

        # Get the starting position of each car
        # Want to randomize between:
        # - X: -2000 to 2000
        # - Y: -2500 to 2500
        offensive_x_location = self.random_between(-2000, 2000)
        offensive_y_location = self.random_between(-2500, 2500)
        offensive_car_position = Vector3(offensive_x_location, offensive_y_location, 17)

        # Defensive location should be +-300 X units away from offensive car, and 1000 to 1500 Y units away towards the goal
        defensive_x_location = offensive_x_location + self.random_between(-300, 300)
        if self.mirrored:
            defensive_y_location = offensive_y_location + self.random_between(1000, 1500)
        else:
            defensive_y_location = offensive_y_location - self.random_between(1000, 1500)
            
        defensive_car_position = Vector3(defensive_x_location, defensive_y_location, 17)

        # # Render the offensive and defensive coordinates
        # self.game_interface.renderer.begin_rendering()
        # self.game_interface.renderer.draw_string_2d(20, 400, 1, 1, f"Offensive Car: {offensive_x_location}, {offensive_y_location}", self.renderer.yellow())
        # self.game_interface.renderer.draw_string_2d(20, 460, 1, 1, f"Defensive Car: {defensive_x_location}, {defensive_y_location}", self.renderer.yellow())
        # self.game_interface.renderer.end_rendering()


        # Ball should be ~600 units "in front" of offensive car, with 200 variance in either direction
        ball_offset = 600
        ball_x_location = offensive_x_location + (ball_offset * np.cos(offensive_car_yaw)) + self.random_between(-100, 100)
        if self.mirrored:
            ball_y_location = offensive_y_location + (ball_offset * np.sin(offensive_car_yaw)) + self.random_between(-100, 100)
        else:
            ball_y_location = offensive_y_location + (ball_offset * np.sin(offensive_car_yaw)) + self.random_between(-100, 100)

        ball_z_location = 93 + self.random_between(0, 200)
        ball_position = Vector3(ball_x_location, ball_y_location, ball_z_location)

        offensive_car_state = CarState(boost_amount=100, physics=Physics(location=offensive_car_position, rotation=Rotator(yaw=offensive_car_yaw, pitch=0, roll=0), velocity=offensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))
        defensive_car_state = CarState(boost_amount=100, physics=Physics(location=defensive_car_position, rotation=Rotator(yaw=defensive_car_yaw, pitch=0, roll=0), velocity=defensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))

        if self.mirrored:
            car_states[0] = offensive_car_state
            car_states[1] = defensive_car_state
        else:
            car_states[0] = defensive_car_state
            car_states[1] = offensive_car_state
        ball_state = BallState(Physics(location=ball_position, velocity=ball_velocity))

        self.game_state = GameState(ball=ball_state, cars=car_states)
        self.set_game_state(self.game_state)
        self.prev_time = self.cur_time

    # Offense is the same as shadow defense, but defender always starts in the net
    def setup_net_defense(self, packet):
        car_states = {}
        play_yaw, play_yaw_mir = self.get_play_yaw()

        # Add a small random angle to the yaw of each car
        if self.mirrored:
            offensive_car_yaw = play_yaw_mir + self.random_between(-0.1*np.pi, 0.1*np.pi)
            defensive_car_yaw = play_yaw_mir + self.random_between(-0.1*np.pi, 0.1*np.pi)
        else:
            offensive_car_yaw = play_yaw + self.random_between(-0.1*np.pi, 0.1*np.pi)
            defensive_car_yaw = play_yaw + self.random_between(-0.1*np.pi, 0.1*np.pi)

        # Get the momentum from the yaw
        offensive_car_velocity = self.get_velocity_from_yaw(offensive_car_yaw, 800, 1200)
        defensive_car_velocity = 0

        if self.mirrored:
            ball_velocity = self.get_velocity_from_yaw(play_yaw_mir)
        else:
            ball_velocity = self.get_velocity_from_yaw(play_yaw)

        # Get the starting position of each car
        # Want to randomize between:
        # - X: -2000 to 2000
        # - Y: -2500 to 2500
        offensive_x_location = self.random_between(-2000, 2000)
        offensive_y_location = self.random_between(-2500, 2500)
        offensive_car_position = Vector3(offensive_x_location, offensive_y_location, 17)

        # Let's do -200 to 200 range for X, Y is -5300 (or +5300 if mirrored)
        defensive_x_location = self.random_between(-200, 200)
        if self.mirrored:
            defensive_y_location = 5300
        else:
            defensive_y_location = -5300

        defensive_car_position = Vector3(defensive_x_location, defensive_y_location, 17)

        # Ball should be ~600 units "in front" of offensive car, with 200 variance in either direction
        ball_offset = 600
        ball_x_location = offensive_x_location + (ball_offset * np.cos(offensive_car_yaw)) + self.random_between(-100, 100)
        if self.mirrored:
            ball_y_location = offensive_y_location + (ball_offset * np.sin(offensive_car_yaw)) + self.random_between(-100, 100)
        else:
            ball_y_location = offensive_y_location + (ball_offset * np.sin(offensive_car_yaw)) + self.random_between(-100, 100)

        ball_z_location = 93 + self.random_between(0, 200)
        ball_position = Vector3(ball_x_location, ball_y_location, ball_z_location)

        offensive_car_state = CarState(boost_amount=100, physics=Physics(location=offensive_car_position, rotation=Rotator(yaw=offensive_car_yaw, pitch=0, roll=0), velocity=offensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))
        defensive_car_state = CarState(boost_amount=100, physics=Physics(location=defensive_car_position, rotation=Rotator(yaw=defensive_car_yaw, pitch=0, roll=0), velocity=defensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))
        
        if self.mirrored:
            car_states[0] = offensive_car_state
            car_states[1] = defensive_car_state
        else:
            car_states[0] = defensive_car_state
            car_states[1] = offensive_car_state
        ball_state = BallState(Physics(location=ball_position, velocity=ball_velocity))

        self.game_state = GameState(ball=ball_state, cars=car_states)
        self.set_game_state(self.game_state)
        self.prev_time = self.cur_time

    def setup_shot_defense(self, packet):
        pass

    def setup_sidewall_defense(self, packet):
        pass

    def setup_carry_defense(self, packet):
        pass


    def get_play_yaw(self):
        rand1 = np.random.random()
        if rand1 < 1/7:
            play_yaw = -np.pi * 0.25
        elif rand1 < 2/7:
            play_yaw = -np.pi * 0.375
        elif rand1 < 5/7:
            play_yaw = -np.pi * 0.5
        elif rand1 < 6/7:
            play_yaw = -np.pi * 0.625
        elif rand1 < 7/7:
            play_yaw = -np.pi * 0.75
        # 50% parallel/mirrored yaw compared to other team
        if np.random.random() < 0.5:
            play_yaw_mir = play_yaw-np.pi
        else:
            play_yaw_mir = -play_yaw
        return play_yaw, play_yaw_mir
        

    def get_velocity_from_yaw(self, yaw, min_velocity, max_velocity):
        # yaw is in radians, use this to get the ratio of x/y velocity
        # X = cos(yaw) 
        # Y = sin(yaw)
        # Z = 0
        # Magnitude is the momentum
        rand1 = np.random.random()
        velocity_x = min_velocity + rand1 * (max_velocity - min_velocity) * np.cos(yaw)
        velocity_y = min_velocity + rand1 * (max_velocity - min_velocity) * np.sin(yaw)
        return Vector3(velocity_x, velocity_y, 0)

    def random_between(self, min_value, max_value):
        return min_value + np.random.random() * (max_value - min_value)

    def setup_std_kickoff(self, packet):
        car_states = {}
        rand1 = np.random.random()
        for p in range(packet.num_cars):
            car = packet.game_cars[p]
            if car.team == 0:
                if rand1 < 1/5:
                    pos = Vector3(-2048, -2560, 17)
                    yaw = np.pi * 0.25
                elif rand1 < 2/5:
                    pos = Vector3(2048, -2560, 17)
                    yaw = np.pi * 0.75
                elif rand1 < 3/5:
                    pos = Vector3(-256.0, -3840, 17)
                    yaw = np.pi * 0.5
                elif rand1 < 4/5:
                    pos = Vector3(256.0, -3840, 17)
                    yaw = np.pi * 0.5
                elif rand1 < 5/5:
                    pos = Vector3(0.0, -4608, 17)
                    yaw = np.pi * 0.5
                car_state = CarState(boost_amount=34, physics=Physics(location=pos, rotation=Rotator(yaw=yaw, pitch=0, roll=0), velocity=Vector3(0, 0, 0),
                        angular_velocity=Vector3(0, 0, 0)))
                car_states[p] = car_state
            elif car.team == 1:
                if rand1 < 1/5:
                    pos = Vector3(2048, 2560, 17)
                    yaw = np.pi * -0.75
                elif rand1 < 2/5:
                    pos = Vector3(-2048, 2560, 17)
                    yaw = np.pi * -0.25
                elif rand1 < 3/5:
                    pos = Vector3(256.0, 3840, 17)
                    yaw = np.pi * -0.5
                elif rand1 < 4/5:
                    pos = Vector3(-256.0, 3840, 17)
                    yaw = np.pi * -0.5
                elif rand1 < 5/5:
                    pos = Vector3(0.0, 4608, 17)
                    yaw = np.pi * -0.5
                car_state = CarState(boost_amount=34, physics=Physics(location=pos, rotation=Rotator(yaw=yaw, pitch=0, roll=0), velocity=Vector3(0, 0, 0),
                        angular_velocity=Vector3(0, 0, 0)))
                car_states[p] = car_state
        if self.horz_ball_var == 'Off':
            ball_vel_x = ball_vel_y = 0
        elif self.horz_ball_var == 'On':
            ball_vel_x = (np.random.random()*2-1)*500
            ball_vel_y = (np.random.random()*2-1)*300
        if self.vert_ball_var == 'Off':
            ball_vel_z = -1
            ball_pos_z = 93
        elif self.vert_ball_var == 'On':
            ball_vel_z = np.random.random()*360-460
            ball_pos_z = np.random.random()*200+500
        self.paused_car_states = car_states
        ball_state = BallState(Physics(location=Vector3(0, 0, ball_pos_z), velocity=Vector3(ball_vel_x,ball_vel_y,ball_vel_z)))
        self.game_state = GameState(ball=ball_state, cars=car_states)
        self.set_game_state(self.game_state)
        self.prev_time = self.cur_time
        self.game_phase = -1


    def yaw_randomizer(self):
        if not self .first_kickoff: # First kickoff will always be straight
            # yaw will have 5 possible values from pi*.25 to pi.75. Straght kickoffs weighted higher
            rand1 = np.random.random()
            if rand1 < 1/7:
                yaw = np.pi * 0.25
            elif rand1 < 2/7:
                yaw = np.pi * 0.375
            elif rand1 < 5/7:
                yaw = np.pi * 0.5
            elif rand1 < 6/7:
                yaw = np.pi * 0.625
            elif rand1 < 7/7:
                yaw = np.pi * 0.75
            # 50% parallel/mirrored yaw compared to other team
            if np.random.random() < 0.5:
                yaw_mir = yaw-np.pi
            else:
                yaw_mir = -yaw
            return yaw, yaw_mir
        else:
            self.first_kickoff = False
            yaw = np.pi * 0.5
            yaw_mir = -yaw
            return yaw, yaw_mir

    def save_gamestate(self, packet, b_has_flip, o_has_flip):
        blue_car = packet.game_cars[0]
        orange_car = packet.game_cars[1]
        ball = packet.game_ball
        cur_state = np.zeros(37)
        cur_state[0] = blue_car.physics.location.x
        cur_state[1] = blue_car.physics.location.y
        cur_state[2] = blue_car.physics.location.z
        cur_state[3] = blue_car.physics.rotation.pitch
        cur_state[4] = blue_car.physics.rotation.yaw
        cur_state[5] = blue_car.physics.rotation.roll
        cur_state[6] = blue_car.physics.velocity.x
        cur_state[7] = blue_car.physics.velocity.y
        cur_state[8] = blue_car.physics.velocity.z
        cur_state[9] = blue_car.physics.angular_velocity.x
        cur_state[10] = blue_car.physics.angular_velocity.y
        cur_state[11] = blue_car.physics.angular_velocity.z
        cur_state[12] = blue_car.boost
        cur_state[13] = b_has_flip
        cur_state[14] = orange_car.physics.location.x
        cur_state[15] = orange_car.physics.location.y
        cur_state[16] = orange_car.physics.location.z
        cur_state[17] = orange_car.physics.rotation.pitch
        cur_state[18] = orange_car.physics.rotation.yaw
        cur_state[19] = orange_car.physics.rotation.roll
        cur_state[20] = orange_car.physics.velocity.x
        cur_state[21] = orange_car.physics.velocity.y
        cur_state[22] = orange_car.physics.velocity.z
        cur_state[23] = orange_car.physics.angular_velocity.x
        cur_state[24] = orange_car.physics.angular_velocity.y
        cur_state[25] = orange_car.physics.angular_velocity.z
        cur_state[26] = orange_car.boost
        cur_state[27] = o_has_flip
        cur_state[28] = ball.physics.location.x
        cur_state[29] = ball.physics.location.y
        cur_state[30] = ball.physics.location.z
        cur_state[31] = ball.physics.velocity.x
        cur_state[32] = ball.physics.velocity.y
        cur_state[33] = ball.physics.velocity.z
        cur_state[34] = ball.physics.angular_velocity.x
        cur_state[35] = ball.physics.angular_velocity.y
        cur_state[36] = ball.physics.angular_velocity.z
        return np.expand_dims(cur_state, axis=0)

    # Currently Unavailable
    # def menu_1_toggle(self):
    #     if self.blue_omus:
    #         self.record_omus = not self.record_omus
    #         if not self.record_omus:
    #             self.state_buffer = np.empty((0,37))
    #             self.standard_kickoffs = 'Off'
    #     else:
    #         self.text2 = "Error: Please set Omus to Blue Team"
    #         self.error_timer = self.cur_time

    def mirror_toggle(self):
        if self.mirrored:
            self.mirrored = False
        else:
            self.mirrored = True


    def set_shadow_mode(self):
        self.game_mode = 'shadow'

    def set_net_mode(self):
        self.game_mode = 'net'

    def set_shot_mode(self):
        self.game_mode = 'shot'

    def set_sidewall_mode(self):
        self.game_mode = 'sidewall'

    def set_carry_mode(self):
        self.game_mode = 'carry'


# You can use this __name__ == '__main__' thing to ensure that the script doesn't start accidentally if you
# merely reference its module from somewhere
if __name__ == "__main__":
    script = DefenseMiniGame()
    script.run()
