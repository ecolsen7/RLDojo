import numpy as np
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
import matplotlib.pyplot as plt
from enum import Enum
import utils

class Race:
    def __init__(self):
        self.ball_state = None
        self.player_team = 0

        # Place the ball in a random location
        x_loc = utils.random_between(-4096, 4096)
        y_loc = utils.random_between(-5120, 5120)
        z_loc = utils.random_between(90, 1954)
        ball_velocity = Vector3(0, 0, 0)
        self.ball_state = BallState(Physics(location=Vector3(x_loc, y_loc, z_loc), velocity=ball_velocity))

        utils.sanity_check_objects([self.ball_state])

        
    def BallState(self):
        return self.ball_state