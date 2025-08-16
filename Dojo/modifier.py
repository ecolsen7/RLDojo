import numpy as np
from enum import Enum
import keyboard

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
from scenario import Scenario, OffensiveMode, DefensiveMode
import utils

#######################################
### Custom Sandbox Object Modifiers ###
#######################################

def modify_object_x(object_to_modify, x):
    object_to_modify.physics.location.x += x
    
def modify_object_y(object_to_modify, y):
    object_to_modify.physics.location.y += y

def modify_object_z(object_to_modify, z):
    object_to_modify.physics.location.z += z

def modify_pitch(object_to_modify, pitch):
    if hasattr(object_to_modify.physics, 'rotation'):
        object_to_modify.physics.rotation.pitch += pitch
        object_to_modify.physics.velocity = utils.get_velocity_from_rotation(object_to_modify.physics.rotation, 1000, 2000)
    else:
        # Ball doesn't have rotation, use the velocity components to determine and modify trajectory
        yaw = np.arctan2(object_to_modify.physics.velocity.y, object_to_modify.physics.velocity.x)
        pitch = np.arctan2(object_to_modify.physics.velocity.z, np.sqrt(object_to_modify.physics.velocity.x**2 + object_to_modify.physics.velocity.y**2))

        # Increase pitch by 0.1
        pitch += pitch

        # Convert back to velocity components
        object_to_modify.physics.velocity = utils.get_velocity_from_rotation(Rotator(yaw=yaw, pitch=pitch, roll=0), 1000, 2000)

def modify_yaw(object_to_modify, yaw):
    if hasattr(object_to_modify.physics, 'rotation'):
        object_to_modify.physics.rotation.yaw += yaw
        object_to_modify.physics.velocity = utils.get_velocity_from_rotation(object_to_modify.physics.rotation, 1000, 2000)
    else:
        # Ball doesn't have rotation, use the velocity components to determine and modify trajectory
        yaw = np.arctan2(object_to_modify.physics.velocity.y, object_to_modify.physics.velocity.x)
        pitch = np.arctan2(object_to_modify.physics.velocity.z, np.sqrt(object_to_modify.physics.velocity.x**2 + object_to_modify.physics.velocity.y**2))

        # Increase yaw by 0.1
        yaw += yaw

        # Convert back to velocity components
        object_to_modify.physics.velocity = utils.get_velocity_from_rotation(Rotator(yaw=yaw, pitch=pitch, roll=0), 1000, 2000)

def modify_roll(object_to_modify, roll):
    if hasattr(object_to_modify.physics, 'rotation'):
        object_to_modify.physics.rotation.roll += roll

def modify_velocity(object_to_modify, velocity_percentage_delta):
    # Velocity is a 3-dimensional vector, scale each component by the same percentage
    x = object_to_modify.physics.velocity.x
    y = object_to_modify.physics.velocity.y
    z = object_to_modify.physics.velocity.z

    x += x * velocity_percentage_delta
    y += y * velocity_percentage_delta
    z += z * velocity_percentage_delta

    object_to_modify.physics.velocity = Vector3(x, y, z)
