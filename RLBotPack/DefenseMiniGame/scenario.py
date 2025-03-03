import numpy as np
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
import matplotlib.pyplot as plt
from enum import Enum

class OffensiveMode(Enum):
    POSSESSION = 0
    BREAKOUT = 1
    PASS = 2
    CARRY = 3
    CORNER = 4
    SIDEWALL = 5
    LOB_ON_GOAL = 6
    BACKWALL_BOUNCE = 7

class DefensiveMode(Enum):
    NEAR_SHADOW = 0
    FAR_SHADOW = 1
    NET = 2
    CORNER = 3

SIDE_WALL=4096

# From perspective of default scenario - blue team defending
BACK_WALL=-5120

class Scenario:
    '''
    Scenario represents all initial states of a game mode
    Comprised of a BallState and two CarStates (or more, to be added)
    '''
    def __init__(self, offensive_mode, defensive_mode):
        '''
        Create a new scenario based on the game mode
        '''
        self.offensive_team = 0
        match offensive_mode:
            case OffensiveMode.POSSESSION:
                self.__setup_possession_offense(self.random_between(-2500, 1500))
            case OffensiveMode.BREAKOUT:
                self.__setup_possession_offense(self.random_between(2000, 3000))
            case OffensiveMode.PASS:
                self.__setup_pass_offense()
            case OffensiveMode.CARRY:
                self.__setup_carry_offense()
            case OffensiveMode.CORNER:
                self.__setup_corner_offense()
            case OffensiveMode.SIDEWALL:
                self.__setup_sidewall_offense()
            case OffensiveMode.LOB_ON_GOAL:
                self.__setup_lob_on_goal_offense()
            case OffensiveMode.BACKWALL_BOUNCE:
                self.__setup_backwall_bounce_offense()


        match defensive_mode:
            case DefensiveMode.NEAR_SHADOW:
                self.__setup_shadow_defense(self.random_between(1500, 2500))
            case DefensiveMode.FAR_SHADOW:
                self.__setup_shadow_defense(self.random_between(3000, 4000))
            case DefensiveMode.NET:
                self.__setup_net_defense()
            case DefensiveMode.CORNER:
                self.__setup_corner_defense()

        self.__sanity_check_objects()

    def GetGameState(self):
        '''
        Set the game state to the scenario
        '''
        # Car 0 = Blue, Car 1 = Orange
        car_states = {}
        if self.offensive_team == 0:
            car_states[1] = self.offensive_car_state
            car_states[0] = self.defensive_car_state
        else:
            car_states[0] = self.offensive_car_state
            car_states[1] = self.defensive_car_state
        return GameState(ball=self.ball_state, cars=car_states)


    def Mirror(self):
        '''
        Mirror the scenario across the Y axis, turning defensive scenarios into offensive scenarios
        Involves flipping the Y aspects of the car + ball locations, velocity, and yaw
        '''
        self.offensive_car_state.physics.location.y = -self.offensive_car_state.physics.location.y
        self.defensive_car_state.physics.location.y = -self.defensive_car_state.physics.location.y
        self.ball_state.physics.location.y = -self.ball_state.physics.location.y

        self.offensive_car_state.physics.rotation.yaw = -self.offensive_car_state.physics.rotation.yaw
        self.defensive_car_state.physics.rotation.yaw = -self.defensive_car_state.physics.rotation.yaw

        self.offensive_car_state.physics.velocity.y = -self.offensive_car_state.physics.velocity.y
        self.defensive_car_state.physics.velocity.y = -self.defensive_car_state.physics.velocity.y
        self.ball_state.physics.velocity.y = -self.ball_state.physics.velocity.y

        self.offensive_team = 1 - self.offensive_team
    
    def Draw(self):
        '''
        Plot the scenario against a simulated field, for debugging purposes
        '''
        plt.figure()
        # Rocket League uses a coordinate system (X, Y, Z), where Z is upwards. Note also that negative Y is towards Blue's goal (team 0).

        # Floor: 0
        # Center field: (0, 0)
        # Side wall: x=±4096
        # Side wall length: 7936
        # Back wall: y=±5120
        # Back wall length: 5888
        # Ceiling: z=2044
        # Goal height: z=642.775
        # Goal center-to-post: 892.755
        # Goal depth: 880
        # Corner wall length: 1629.174
        # The corner planes intersect the axes at ±8064 at a 45 degrees angle

        # Draw the field
        
        # Add vertical lines from at X=-4096 and X=4096, each from Y=-5120 to Y=5120
        # Stop 1152 units short from each wall to leave room for the corners
        corner_start = 5120 - 1152
        plt.plot([-4096, -4096], [-corner_start, corner_start], 'k-')
        plt.plot([4096, 4096], [-corner_start, corner_start], 'k-')

        # Add horizontal lines from at Y=-5120 and Y=5120, each from X=-4096 to X=4096
        corner_start = 4096 - 1152
        plt.plot([-corner_start, corner_start], [-5120, -5120], 'k-')
        plt.plot([-corner_start, corner_start], [5120, 5120], 'k-')

        # Draw lines representing the corners
        # Top left goes from X=-4096, Y=(5120-1152) to X=(-4096+1152), Y=-5120
        plt.plot([-4096, -4096+1152], [5120-1152, 5120], 'k-')
        # Top right goes from X=4096, Y=(5120-1152) to X=(4096-1152), Y=-5120
        plt.plot([4096, 4096-1152], [5120-1152, 5120], 'k-')
        # Bottom left goes from X=-4096, Y=-5120 to X=(-4096+1152), Y=(-5120+1152)
        plt.plot([-4096, -4096+1152], [-5120+1152, -5120], 'k-')
        # Bottom right goes from X=4096, Y=-5120 to X=(4096-1152), Y=(-5120+1152)
        plt.plot([4096, 4096-1152], [-5120+1152, -5120], 'k-')

        # Goal extends from -893 to +893 in X, and 880 past the goal line in Y, which is at Y=+-5120
        plt.plot([-893, -893], [-5120-880, -5120], 'k-')
        plt.plot([893, 893], [-5120-880, -5120], 'k-')
        plt.plot([-893, 893], [-5120-880, -5120-880], 'k-')

        plt.plot([-893, -893], [5120, 5120+880], 'k-')
        plt.plot([893, 893], [5120, 5120+880], 'k-')
        plt.plot([-893, 893], [5120+880, 5120+880], 'k-')


        # Draw a dotted line across the center of the field at Y=0, make it opaque
        plt.plot([-4096, 4096], [0, 0], 'k--', alpha=0.5)

        # Draw the offensive car as a blue triangle
        # Car is 200 units long, 100 units wide
        # Draw an arrow from center -100 to center +100 units in the direction of the car's yaw
        car_length = 200
        car_width = 100
        offensive_x_component = car_length * np.cos(self.offensive_car_state.physics.rotation.yaw)
        offensive_y_component = car_width * np.sin(self.offensive_car_state.physics.rotation.yaw)
        offensive_arrow_x_start = self.offensive_car_state.physics.location.x 
        offensive_arrow_y_start = self.offensive_car_state.physics.location.y 

        plt.arrow(offensive_arrow_x_start,
                 offensive_arrow_y_start,
                 offensive_x_component,
                 offensive_y_component,
                 head_width=200, head_length=400, fc='b', ec='b', length_includes_head=True)
        
        defensive_x_component = car_length * np.cos(self.defensive_car_state.physics.rotation.yaw)
        defensive_y_component = car_width * np.sin(self.defensive_car_state.physics.rotation.yaw)
        defensive_arrow_x_start = self.defensive_car_state.physics.location.x 
        defensive_arrow_y_start = self.defensive_car_state.physics.location.y 
        plt.arrow(defensive_arrow_x_start,
                 defensive_arrow_y_start,
                 defensive_x_component,
                 defensive_y_component,
                 head_width=200, head_length=400, fc='r', ec='r', length_includes_head=True)
        
        # plt.plot(self.offensive_car_state.physics.location.x, self.offensive_car_state.physics.location.y, 'bo', markersize=10)
        # Draw the defensive car as a red triangle
        # plt.plot(self.defensive_car_state.physics.location.x, self.defensive_car_state.physics.location.y, 'ro', markersize=10)
        
        # Draw the ball as a gray circle
        plt.plot(self.ball_state.physics.location.x, self.ball_state.physics.location.y, 'ko', markersize=10)

        # Draw the offensive car's velocity vector
        plt.arrow(self.offensive_car_state.physics.location.x, self.offensive_car_state.physics.location.y,
                 self.offensive_car_state.physics.velocity.x, self.offensive_car_state.physics.velocity.y,
                 head_width=50, head_length=50, fc='b', ec='b')
        
        # Draw the defensive car's velocity vector
        plt.arrow(self.defensive_car_state.physics.location.x, self.defensive_car_state.physics.location.y,
                 self.defensive_car_state.physics.velocity.x, self.defensive_car_state.physics.velocity.y,
                 head_width=50, head_length=50, fc='r', ec='r')
        
        # Draw the ball's velocity vector
        plt.arrow(self.ball_state.physics.location.x, self.ball_state.physics.location.y,
                 self.ball_state.physics.velocity.x, self.ball_state.physics.velocity.y,
                 head_width=50, head_length=50, fc='k', ec='k')
        
        # Enforce same scale on both axes
        ax = plt.gca()
        ax.get_xaxis().get_major_formatter().set_scientific(False)
        ax.get_yaxis().get_major_formatter().set_scientific(False)
        plt.axis('equal')

        plt.show()

    def __setup_possession_offense(self, distance_from_net):
        self.play_yaw, play_yaw_mir = self.get_play_yaw()

        # Add a small random angle to the yaw of each car
        offensive_car_yaw = self.play_yaw + self.random_between(-0.1*np.pi, 0.1*np.pi)
        offensive_car_velocity = self.get_velocity_from_yaw(offensive_car_yaw, min_velocity=800, max_velocity=1200)
        ball_velocity = self.get_velocity_from_yaw(self.play_yaw, min_velocity=800, max_velocity=1200)

        offensive_x_location = self.random_between(-2000, 2000)
        offensive_y_location = distance_from_net
        offensive_car_position = Vector3(offensive_x_location, offensive_y_location, 17)

        # Ball should be ~600 units "in front" of offensive car, with 200 variance in either direction
        ball_offset = 600
        ball_x_location = offensive_x_location + (ball_offset * np.cos(offensive_car_yaw)) + self.random_between(-100, 100)
        ball_y_location = offensive_y_location + (ball_offset * np.sin(offensive_car_yaw)) + self.random_between(-100, 100)

        ball_z_location = 93 + self.random_between(0, 200)
        ball_position = Vector3(ball_x_location, ball_y_location, ball_z_location)

        self.offensive_car_state = CarState(boost_amount=100, physics=Physics(location=offensive_car_position, rotation=Rotator(yaw=offensive_car_yaw, pitch=0, roll=0), velocity=offensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))
        self.ball_state = BallState(Physics(location=ball_position, velocity=ball_velocity))

    def __setup_carry_offense(self):
       # Mostly same as possession, but ball starts on top of the car
       self.play_yaw, play_yaw_mir = self.get_play_yaw()

       offensive_car_yaw = self.play_yaw + self.random_between(-0.1*np.pi, 0.1*np.pi)
       offensive_car_velocity = self.get_velocity_from_yaw(offensive_car_yaw, min_velocity=800, max_velocity=1200)
       ball_velocity = offensive_car_velocity

       offensive_x_location = self.random_between(-2000, 2000)
       offensive_y_location = self.random_between(-2500, 2500)
       offensive_car_position = Vector3(offensive_x_location, offensive_y_location, 17)

       ball_position = Vector3(offensive_x_location, offensive_y_location, 120)

       self.offensive_car_state = CarState(boost_amount=100, physics=Physics(location=offensive_car_position, rotation=Rotator(yaw=offensive_car_yaw, pitch=0, roll=0), velocity=offensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))
       
       self.ball_state = BallState(Physics(location=ball_position, velocity=ball_velocity))

    def __setup_corner_offense(self):
        # Offensive car starts heading toward the corner
        # This will be ~1000 units from the back wall, ~500 units from the side wall
        # X side should be randomized
        offensive_x_location = self.random_between(SIDE_WALL - 500, SIDE_WALL - 1000)
        offensive_y_location = self.random_between(BACK_WALL + 1500, BACK_WALL + 2500)

        offensive_x_target = SIDE_WALL - 2000
        offensive_y_target = BACK_WALL + 500

        # Yaw should be facing halfway between the corner boost and back post
        offensive_car_yaw = np.arctan2(offensive_y_target - offensive_y_location, offensive_x_target - offensive_x_location)
        self.play_yaw = offensive_car_yaw

        # Velocity should be toward the existing yaw
        offensive_car_velocity = self.get_velocity_from_yaw(offensive_car_yaw, min_velocity=800, max_velocity=1200)
        offensive_car_position = Vector3(offensive_x_location, offensive_y_location, 17)

        # Ball should be ~600 units "in front" of offensive car, with 200 variance in either direction
        ball_offset = 600
        ball_x_location = offensive_x_location + (ball_offset * np.cos(offensive_car_yaw)) + self.random_between(-100, 100)
        ball_y_location = offensive_y_location + (ball_offset * np.sin(offensive_car_yaw)) + self.random_between(-100, 100)

        ball_z_location = 93 + self.random_between(0, 200)
        ball_position = Vector3(ball_x_location, ball_y_location, ball_z_location)
        ball_velocity = self.get_velocity_from_yaw(offensive_car_yaw, min_velocity=800, max_velocity=1200)

        self.offensive_car_state = CarState(boost_amount=100, physics=Physics(location=offensive_car_position, rotation=Rotator(yaw=offensive_car_yaw, pitch=0, roll=0), velocity=offensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))
        
        self.ball_state = BallState(Physics(location=ball_position, velocity=ball_velocity))

        # Flip X position, velocity, and yaw randomly 50% of the time
        self.__randomly_mirror_offense_x()

    def __setup_pass_offense(self):
        self.play_yaw, play_yaw_mir = self.get_play_yaw()

        # Add a small random angle to the yaw of each car
        offensive_car_yaw = self.play_yaw + self.random_between(-0.1*np.pi, 0.1*np.pi)

        # Get the starting velocity from the yaw
        offensive_car_velocity = self.get_velocity_from_yaw(offensive_car_yaw, 800, 1200)

        # Get the starting position of each car
        # Want to randomize between:
        # - X: -2000 to 2000
        # - Y: -2500 to 0
        offensive_x_location = self.random_between(-2000, 2000)
        offensive_y_location = self.random_between(-1000, 1500)
        offensive_car_position = Vector3(offensive_x_location, offensive_y_location, 17)

        # Ball should start from the wall on the opposite X side as the offensive car
        if offensive_x_location < 0:
            ball_x_location = 3500
        else:
            ball_x_location = -3500

        # Ball should start close to the goal 
        ball_y_location = self.random_between(-4500, -3500)
        ball_z_location = 93 + self.random_between(0, 2000)
        ball_position = Vector3(ball_x_location, ball_y_location, ball_z_location)

        # Ball should be heading in front of the offensive car
        # calculate 1500 total units in the direction the offensive car is facing
        x_component = 1500 * np.cos(offensive_car_yaw)
        y_component = 1500 * np.sin(offensive_car_yaw)
        ball_target_x_location = offensive_x_location + x_component
        ball_target_y_location = offensive_y_location + y_component
        delta_x = ball_target_x_location - ball_x_location
        delta_y = ball_target_y_location - ball_y_location
        velocity_magnitude = self.random_between(0.4, 0.5)

        # Cap Y velocity component, or else it goes past the offensive car sometimes
        ball_velocity = Vector3(delta_x*velocity_magnitude, min(delta_y*velocity_magnitude, 750), self.random_between(0, 300))

        self.offensive_car_state = CarState(boost_amount=100, physics=Physics(location=offensive_car_position, rotation=Rotator(yaw=offensive_car_yaw, pitch=0, roll=0), velocity=offensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))
        
        self.ball_state = BallState(Physics(location=ball_position, velocity=ball_velocity))

    def __setup_sidewall_offense(self):
        # Play yaw is going to be slightly toward the net but mostly toward the side wall
        self.play_yaw = self.random_between(5.8, 6.2)

        # Offensive car should be 1000 units from the side wall
        offensive_x_location = SIDE_WALL - self.random_between(1500, 2500)

        # Sidewall setups shouldn't be too close to the goal
        offensive_y_location = self.random_between(-1500, 1500)

        # Add a small random angle to the yaw of each car
        offensive_car_yaw = self.play_yaw + self.random_between(-0.1*np.pi, 0.1*np.pi)
        offensive_car_velocity = self.get_velocity_from_yaw(offensive_car_yaw, min_velocity=800, max_velocity=1200)
        ball_velocity = self.get_velocity_from_yaw(self.play_yaw, min_velocity=1500, max_velocity=2000)

        offensive_car_position = Vector3(offensive_x_location, offensive_y_location, 17)

        # Ball should be ~600 units "in front" of offensive car, with 200 variance in either direction
        ball_offset = 600
        ball_x_location = offensive_x_location + (ball_offset * np.cos(offensive_car_yaw)) + self.random_between(-100, 100)
        ball_y_location = offensive_y_location + (ball_offset * np.sin(offensive_car_yaw)) + self.random_between(-100, 100)

        ball_z_location = 93 + self.random_between(0, 30)
        ball_position = Vector3(ball_x_location, ball_y_location, ball_z_location)

        self.offensive_car_state = CarState(boost_amount=100, physics=Physics(location=offensive_car_position, rotation=Rotator(yaw=offensive_car_yaw, pitch=0, roll=0), velocity=offensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))
        self.ball_state = BallState(Physics(location=ball_position, velocity=ball_velocity))

        # Flip X position, velocity, and yaw randomly 50% of the time
        self.__randomly_mirror_offense_x()

    def __setup_lob_on_goal_offense(self):
        # Yaw is going to be toward the goal, that's going to be 1.5pi
        self.play_yaw = 1.5*np.pi
        offensive_car_yaw = self.play_yaw + self.random_between(-0.1*np.pi, 0.1*np.pi)

        offensive_car_velocity = self.get_velocity_from_yaw(offensive_car_yaw, min_velocity=800, max_velocity=1200)
        offensive_car_x = self.random_between(-500, 500)
        offensive_car_y = self.random_between(-1000, 1000)
        offensive_car_position = Vector3(offensive_car_x, offensive_car_y, 17)

        # Ball should be ahead of offensive car, flying toward back wall
        ball_x_location = offensive_car_x
        ball_y_location = offensive_car_y + 1000
        ball_z_location = 93 + self.random_between(1000, 2000)
        ball_position = Vector3(ball_x_location, ball_y_location, ball_z_location)

        # X should be opposite direction of starting position
        ball_velocity_x = self.random_between(400, 500) * (ball_x_location > 0)
        ball_velocity_y = self.random_between(-2000, -3000)
        ball_velocity_z = self.random_between(0, 300)
        ball_velocity = Vector3(ball_velocity_x, ball_velocity_y, ball_velocity_z)

        self.offensive_car_state = CarState(boost_amount=100, physics=Physics(location=offensive_car_position, rotation=Rotator(yaw=offensive_car_yaw, pitch=0, roll=0), velocity=offensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))
        self.ball_state = BallState(Physics(location=ball_position, velocity=ball_velocity))

    def __setup_backwall_bounce_offense(self):
         # Yaw is going to be toward the goal, that's going to be 1.5pi
        self.play_yaw = 1.5*np.pi
        offensive_car_yaw = self.play_yaw + self.random_between(-0.1*np.pi, 0.1*np.pi)

        offensive_car_velocity = self.get_velocity_from_yaw(offensive_car_yaw, min_velocity=800, max_velocity=1200)
        offensive_car_x = self.random_between(-500, 500)
        offensive_car_y = self.random_between(-1000, 1000)
        offensive_car_position = Vector3(offensive_car_x, offensive_car_y, 17)

        # Ball should be ahead of offensive car, flying toward back wall
        ball_x_location = offensive_car_x
        ball_y_location = offensive_car_y - 1000
        ball_z_location = 93 + self.random_between(1000, 2000)
        ball_position = Vector3(ball_x_location, ball_y_location, ball_z_location)

        # X should be opposite direction of starting position
        ball_velocity_x = self.random_between(400, 500) * (ball_x_location > 0)
        ball_velocity_y = self.random_between(-2000, -3000)
        ball_velocity_z = self.random_between(300, 500)
        ball_velocity = Vector3(ball_velocity_x, ball_velocity_y, ball_velocity_z)

        self.offensive_car_state = CarState(boost_amount=100, physics=Physics(location=offensive_car_position, rotation=Rotator(yaw=offensive_car_yaw, pitch=0, roll=0), velocity=offensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))
        self.ball_state = BallState(Physics(location=ball_position, velocity=ball_velocity))

    def __setup_shadow_defense(self, distance_from_offensive_car):
        '''
        Setup the shadow defense scenario
        Shadow defense is based off of offensive car stats
        '''

        # Add a small random angle to the yaw of each car
        defensive_car_yaw = self.play_yaw + self.random_between(-0.1*np.pi, 0.1*np.pi)

        # Get the starting velocity from the yaw
        defensive_car_velocity = self.get_velocity_from_yaw(defensive_car_yaw, min_velocity=800, max_velocity=1200)

        # Defensive location should be +-300 X units away from offensive car, and given distance away towards the goal
        defensive_x_location = self.random_between(self.offensive_car_state.physics.location.x - 300, self.offensive_car_state.physics.location.x + 300)
        defensive_y_location = self.offensive_car_state.physics.location.y - distance_from_offensive_car
            
        defensive_car_position = Vector3(defensive_x_location, defensive_y_location, 17)

        self.defensive_car_state = CarState(boost_amount=100, physics=Physics(location=defensive_car_position, rotation=Rotator(yaw=defensive_car_yaw, pitch=0, roll=0), velocity=defensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))

    def __setup_net_defense(self):
        # Car is stationary
        defensive_car_velocity = Vector3(0, 0, 0)

        # Let's do -200 to 200 range for X, Y is -5600 (or +5600 if mirrored)
        defensive_x_location = self.random_between(-200, 200)
        defensive_y_location = -5600

        defensive_car_position = Vector3(defensive_x_location, defensive_y_location, 27)

        # In net mode, defensive car yaw should be facing the offensive car
        # Get the difference between the defensive car and the offensive car
        defensive_car_x = defensive_x_location
        defensive_car_y = defensive_y_location
        offensive_car_x = self.offensive_car_state.physics.location.x
        offensive_car_y = self.offensive_car_state.physics.location.y
        radians_to_offensive_car = np.arctan2(offensive_car_y - defensive_car_y, offensive_car_x - defensive_car_x)
        defensive_car_yaw = radians_to_offensive_car

        self.defensive_car_state = CarState(boost_amount=100, physics=Physics(location=defensive_car_position, rotation=Rotator(yaw=defensive_car_yaw, pitch=0, roll=0), velocity=defensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))

    def __setup_corner_defense(self):
        # Defensive car should be heading around the defensive corner

        # This will be ~1000 units from the back wall, ~500 units from the side wall
        # X side should be randomized
        defensive_x_location = self.random_between(SIDE_WALL - 500, SIDE_WALL - 1000)
        defensive_y_location = self.random_between(BACK_WALL + 1500, BACK_WALL + 2500)

        defensive_x_target = SIDE_WALL - 2000
        defensive_y_target = BACK_WALL + 500

        # Yaw should be facing halfway between the corner boost and back post
        defensive_car_yaw = np.arctan2(defensive_y_target - defensive_y_location, defensive_x_target - defensive_x_location)

        # Velocity should be toward the existing yaw
        defensive_car_velocity = self.get_velocity_from_yaw(defensive_car_yaw, min_velocity=800, max_velocity=1200)
        defensive_car_position = Vector3(defensive_x_location, defensive_y_location, 17)

        # Car is stationary
        self.defensive_car_state = CarState(boost_amount=100, physics=Physics(location=defensive_car_position, rotation=Rotator(yaw=defensive_car_yaw, pitch=0, roll=0), velocity=defensive_car_velocity,
                        angular_velocity=Vector3(0, 0, 0)))

        # Flip X position, velocity, and yaw randomly 50% of the time
        self.__randomly_mirror_defensive_x()

    def __sanity_check_objects(self):
        '''If any of the objects have been placed outside of the map, move them to the nearest edge of the map'''
        # Back wall is biased toward the negative end, which makes this math a little fucky
        for object in [self.offensive_car_state, self.defensive_car_state, self.ball_state]:
            if object.physics.location.x < -SIDE_WALL:
                object.physics.location.x = -(SIDE_WALL-100)
            elif object.physics.location.x > SIDE_WALL:
                object.physics.location.x = SIDE_WALL-100
            if object.physics.location.y > -BACK_WALL:
                # Make an exception if in the goal, which is between -/+893 x
                if not (object.physics.location.x > -893 and object.physics.location.x < 893):
                    object.physics.location.y = -(BACK_WALL+100)
            elif object.physics.location.y < BACK_WALL:
                # Make an exception if in the goal, which is between -/+893 x
                if not (object.physics.location.x > -893 and object.physics.location.x < 893):
                    object.physics.location.y = BACK_WALL+100

            # Also account for corners, which is going to suck
            # Corners start 1152 units in from the side walls and back walls
            # That translates to 4096 - 1152 = 2944 in X axis
            # And 5120 - 1152 = 3968 in Y axis
            # So if the object is outside of both of those, move it inside
            if object.physics.location.x > 2944 and object.physics.location.y > 3968:
                object.physics.location.x = 2944
                object.physics.location.y = 3968
            elif object.physics.location.x < -2944 and object.physics.location.y > 3968:
                object.physics.location.x = -2944
                object.physics.location.y = 3968
            elif object.physics.location.x > 2944 and object.physics.location.y < -3968:
                object.physics.location.x = 2944
                object.physics.location.y = -3968
            elif object.physics.location.x < -2944 and object.physics.location.y < -3968:
                object.physics.location.x = -2944
                object.physics.location.y = -3968

    def __randomly_mirror_offense_x(self):
        if np.random.random() < 0.5:
            self.offensive_car_state.physics.location.x = -self.offensive_car_state.physics.location.x
            self.offensive_car_state.physics.velocity.x = -self.offensive_car_state.physics.velocity.x
            self.offensive_car_state.physics.rotation.yaw = (2*np.pi-self.offensive_car_state.physics.rotation.yaw) + np.pi
            self.ball_state.physics.location.x = -self.ball_state.physics.location.x
            self.ball_state.physics.velocity.x = -self.ball_state.physics.velocity.x
    
    def __randomly_mirror_defensive_x(self):
        if np.random.random() < 0.5:
            self.defensive_car_state.physics.location.x = -self.defensive_car_state.physics.location.x
            self.defensive_car_state.physics.velocity.x = -self.defensive_car_state.physics.velocity.x
            self.defensive_car_state.physics.rotation.yaw = (2*np.pi-self.defensive_car_state.physics.rotation.yaw) + np.pi


    # move to utils?
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

    # move to utils?
    def random_between(self, min_value, max_value):
        return min_value + np.random.random() * (max_value - min_value)

    # move to utils?
    def get_velocity_from_yaw(self, yaw, min_velocity, max_velocity):
        # yaw is in radians, use this to get the ratio of x/y velocity
        # X = cos(yaw) 
        # Y = sin(yaw)
        # Z = 0
        velocity_factor = self.random_between(min_velocity, max_velocity)
        velocity_x = velocity_factor * np.cos(yaw)
        velocity_y = velocity_factor * np.sin(yaw)
        return Vector3(velocity_x, velocity_y, 0)
