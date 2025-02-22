import numpy as np
from enum import Enum
import keyboard

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState

class Phase(Enum):
    PAUSED = -1
    SETUP = 0
    ACTIVE = 1

class DefenseMiniGame(BaseScript):
    '''
    Defense MiniGame is a RLBot script
    the goal it to defend
    '''
    def __init__(self):
        super().__init__("DefenseMiniGame")
        self.game_phase = Phase.SETUP
        self.scoreDiff_prev = 0
        self.omusDefeat_prev = 0
        self.prev_ticks = 0
        self.ticks = 0
        self.disable_goal_reset = False
        self.pause_time = 1 # Can increase if hard coded kickoffs are causing issues
        self.cur_time = 0
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
        try:
            self.defeats_buffer = np.load('Omus_replay_states.npy')
        except:
            self.defeats_buffer = np.empty((0,37))

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
                # keyboard.add_hotkey('1', self.menu_1_toggle) -Currently Unavailable
                keyboard.add_hotkey('2', self.menu_2_toggle)
                keyboard.add_hotkey('3', self.menu_3_toggle)
                keyboard.add_hotkey('4', self.menu_4_toggle)
                keyboard.add_hotkey('5', self.menu_5_toggle)
            
            # for standard kickoff, allow time for boost pads to respawn
            if self.standard_kickoffs == 'On':
                self.pause_time = 4
            else:
                self.pause_time = 1

            # rendering
            self.do_rendering()

            # setup round
            if self.game_phase == Phase.SETUP and packet.game_info.is_kickoff_pause:
                # self.setup_std_kickoff(packet) if self.standard_kickoffs == 'On' else self.setup_newround(packet)
                self.setup_newround(packet)

            # when 'disable goal reset' mutator active
            if self.disable_goal_reset == True:
                if self.goal_scored(packet):
                    self.setup_std_kickoff(packet) if self.standard_kickoffs == 'On' else self.setup_newround(packet)

            # pause for 'pause_time' then resume
            if self.game_phase == Phase.PAUSED and (self.cur_time - self.prev_time) < self.pause_time:
                if (self.cur_time - self.prev_time) < 0.5 and self.ball_preview == 'On':
                    self.set_game_state(GameState(cars=self.paused_car_states))
                else:
                    self.set_game_state(self.game_state)

                if self.standard_kickoffs == 'On': # show kickoff countdown
                    self.kickoff_countdown = f'{5-int(np.ceil(self.cur_time-self.prev_time))}'

                    if self.kickoff_countdown == '4' or self.kickoff_countdown == '5':
                        self.kickoff_countdown = ''

            elif self.game_phase == Phase.PAUSED:
                # self.game_phase = 1
                self.game_phase = Phase.ACTIVE

            else:
                self.kickoff_countdown = ''
            
            # phase 2(special case): when goal scored with no further touches, reset phase
            if self.game_phase == Phase.ACTIVE:
                if packet.game_info.is_kickoff_pause and packet.game_ball.latest_touch.time_seconds <= phase2_time:
                    self.game_phase = Phase.SETUP
                if (self.cur_time - self.prev_time) > 5.0:
                    self.game_phase = Phase.SETUP
                else:
                    print(f"Time active: {self.cur_time - self.prev_time}")
            


    def do_rendering(self):
        color = self.renderer.yellow()
        color2 = self.renderer.lime()
        text = f"Omus is about GrandChamp for the base 50-MiniGame\
        \nSearch 'omus setup' in RLBot discord if you are having issues\
        \n'2' add horizontal ball variance (~C-GC): {self.horz_ball_var}\
        \n'3' add vertical ball variance (~Plat):   {self.vert_ball_var}\
        \n'4' add ball velocity preview:            {self.ball_preview}\
        \n'5' for standard kickoffs (~Champ-GC):    {self.standard_kickoffs}"
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


    def omus_defeated(self, packet):
            # check if omus got scored on (omus must be on blue team)
            omusDefeat = packet.teams[1].score

            if omusDefeat != self.omusDefeat_prev:
                self.omusDefeat_prev = omusDefeat
                return True
            return False


    # Location is X, Y, Z
    # Y = 5100 is the goal line
    # X = 850 is the goal post
    def setup_newround(self, packet):
        car_states = {}
        yaw, yaw_mir = self.yaw_randomizer()
        for p in range(packet.num_cars):
            car = packet.game_cars[p]
            if car.team == 0:
                car_location = Vector3(0, -4800, 17)
                car_state = CarState(boost_amount=100, physics=Physics(location=car_location, rotation=Rotator(yaw=yaw_mir, pitch=0, roll=0), velocity=Vector3(0, 0, 0),
                        angular_velocity=Vector3(0, 0, 0)))
                car_states[p] = car_state
            elif car.team == 1:
                car_location = Vector3(0, -3800, 17)
                car_state = CarState(boost_amount=100, physics=Physics(location=car_location, rotation=Rotator(yaw=yaw_mir, pitch=0, roll=0), velocity=Vector3(0, 0, 0),
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
        ball_location = Vector3(0, -4000, ball_pos_z)
        ball_velocity = Vector3(ball_vel_x, ball_vel_y, ball_vel_z)
        ball_state = BallState(Physics(location=ball_location, velocity=ball_velocity))
        self.game_state = GameState(ball=ball_state, cars=car_states)
        self.set_game_state(self.game_state)
        self.prev_time = self.cur_time
        self.game_phase = -1

    # Set up car and ball states based on predefined scenarios
    def setup_scenario(self, packet):
        pass

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


    def menu_2_toggle(self):
        if self.horz_ball_var == 'Off':
            self.horz_ball_var = 'On'
            self.standard_kickoffs = 'Off'
        else:
            self.horz_ball_var = 'Off'


    def menu_3_toggle(self):
        if self.vert_ball_var == 'Off':
            self.vert_ball_var = 'On'
            self.standard_kickoffs = 'Off'
        else:
            self.vert_ball_var = 'Off'
    
    def menu_4_toggle(self):
        if self.ball_preview == 'Off':
            self.ball_preview = 'On'
            self.standard_kickoffs = 'Off'
        else:
            self.ball_preview = 'Off'
    
    def menu_5_toggle(self):
        if self.standard_kickoffs == 'Off':
            self.standard_kickoffs = 'On'
            self.record_omus = False
            self.state_buffer = np.empty((0,37))
            self.horz_ball_var = 'Off'
            self.vert_ball_var = 'Off'
            self.ball_preview = 'Off'
        else:
            self.standard_kickoffs = 'Off'

# You can use this __name__ == '__main__' thing to ensure that the script doesn't start accidentally if you
# merely reference its module from somewhere
if __name__ == "__main__":
    script = DefenseMiniGame()
    script.run()
