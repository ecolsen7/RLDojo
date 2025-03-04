import numpy as np
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState

def get_velocity_from_yaw(yaw, min_velocity, max_velocity):
    # yaw is in radians, use this to get the ratio of x/y velocity
    # X = cos(yaw) 
    # Y = sin(yaw)
    # Z = 0
    return np.array([np.cos(yaw) * min_velocity, np.sin(yaw) * min_velocity, 0])

def add_vector3(vector1, vector2):
    return Vector3(vector1.x + vector2.x, vector1.y + vector2.y, vector1.z + vector2.z)

def vector3_to_list(vector3):
    return [vector3.x, vector3.y, vector3.z]

def subtract_vector3(vector1, vector2):
    return Vector3(vector1.x - vector2.x, vector1.y - vector2.y, vector1.z - vector2.z)

def get_play_yaw():
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
def random_between(min_value, max_value):
    return min_value + np.random.random() * (max_value - min_value)

# move to utils?
def get_velocity_from_yaw(yaw, min_velocity, max_velocity):
    # yaw is in radians, use this to get the ratio of x/y velocity
    # X = cos(yaw) 
    # Y = sin(yaw)
    # Z = 0
    velocity_factor = random_between(min_velocity, max_velocity)
    velocity_x = velocity_factor * np.cos(yaw)
    velocity_y = velocity_factor * np.sin(yaw)
    return Vector3(velocity_x, velocity_y, 0)

# Rotation consists of pitch, yaw, roll
# Yaw is on the x/y plane
# Pitch is radians above/below the x/y plane
# Roll is irrelevant
# We want to convert this to a velocity vector
def get_velocity_from_rotation(rotation, min_velocity, max_velocity):
    # Get the yaw from the rotation
    yaw = rotation.yaw
    # Get the pitch from the rotation
    pitch = rotation.pitch
    
    velocity_factor = random_between(min_velocity, max_velocity)
    velocity_x = (velocity_factor * np.cos(yaw)) * np.cos(pitch)
    velocity_y = (velocity_factor * np.sin(yaw)) * np.cos(pitch)
    velocity_z = velocity_factor * np.sin(pitch)
    return Vector3(velocity_x, velocity_y, velocity_z)
