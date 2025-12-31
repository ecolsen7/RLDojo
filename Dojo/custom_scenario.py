import json
import os
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field, ValidationError
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator

import utils


class Vector3Model(BaseModel):
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)

class RotatorModel(BaseModel):
    pitch: float = Field(default=0.0)
    yaw: float = Field(default=0.0)
    roll: float = Field(default=0.0)

class PhysicsModel(BaseModel):
    location: Vector3Model = Field(default_factory=Vector3Model)
    rotation: RotatorModel = Field(default_factory=RotatorModel)
    velocity: Vector3Model = Field(default_factory=Vector3Model)
    angular_velocity: Optional[Vector3Model] = None

class CarStateModel(BaseModel):
    physics: PhysicsModel = Field(default_factory=PhysicsModel)
    boost_amount: float = Field(default=0.0)
    jumped: bool = Field(default=False)
    double_jumped: bool = Field(default=False)

class BallStateModel(BaseModel):
    physics: PhysicsModel = Field(default_factory=PhysicsModel)

class TypedGameState(BaseModel):
    cars: Dict[int, CarStateModel] = Field(default_factory=dict)
    ball: Optional[BallStateModel] = None

    @classmethod
    def from_game_state(cls, game_state: GameState) -> 'TypedGameState':
        """Convert RLBot GameState to TypedGameState"""
        cars = {}
        if game_state.cars is not None:
            for idx, car in game_state.cars.items():
                if car is None:
                    continue
                
                cars[idx] = CarStateModel(
                    # Check all members of car.physics are not None
                    physics=PhysicsModel(
                        location=Vector3Model(
                            x=car.physics.location.x if car.physics.location is not None else 0.0,
                            y=car.physics.location.y if car.physics.location is not None else 0.0,
                            z=car.physics.location.z if car.physics.location is not None else 0.0
                        ),
                        rotation=RotatorModel(
                            pitch=car.physics.rotation.pitch if car.physics.rotation is not None else 0.0,
                            yaw=car.physics.rotation.yaw if car.physics.rotation is not None else 0.0,
                            roll=car.physics.rotation.roll if car.physics.rotation is not None else 0.0
                        ),
                        velocity=Vector3Model(
                            x=car.physics.velocity.x if car.physics.velocity is not None else 0.0,
                            y=car.physics.velocity.y if car.physics.velocity is not None else 0.0,
                            z=car.physics.velocity.z if car.physics.velocity is not None else 0.0
                        ),
                        angular_velocity=Vector3Model(
                            x=car.physics.angular_velocity.x if car.physics.angular_velocity is not None else 0.0,
                            y=car.physics.angular_velocity.y if car.physics.angular_velocity is not None else 0.0,
                            z=car.physics.angular_velocity.z if car.physics.angular_velocity is not None else 0.0
                        )
                    ),
                    boost_amount=car.boost_amount if car.boost_amount is not None else 0.0,
                    jumped=car.jumped if car.jumped is not None else False,
                    double_jumped=car.double_jumped if car.double_jumped is not None else False
                )

        ball = None
        if game_state.ball is not None:
            ball = BallStateModel(
                physics=PhysicsModel(
                    location=Vector3Model(
                        x=game_state.ball.physics.location.x if game_state.ball.physics.location is not None else 0.0,
                        y=game_state.ball.physics.location.y if game_state.ball.physics.location is not None else 0.0,
                        z=game_state.ball.physics.location.z if game_state.ball.physics.location is not None else 0.0
                    ),
                    rotation=RotatorModel(
                        pitch=game_state.ball.physics.rotation.pitch if game_state.ball.physics.rotation is not None else 0.0,
                        yaw=game_state.ball.physics.rotation.yaw if game_state.ball.physics.rotation is not None else 0.0,
                        roll=game_state.ball.physics.rotation.roll if game_state.ball.physics.rotation is not None else 0.0
                    ),
                    velocity=Vector3Model(
                        x=game_state.ball.physics.velocity.x if game_state.ball.physics.velocity is not None else 0.0,
                        y=game_state.ball.physics.velocity.y if game_state.ball.physics.velocity is not None else 0.0,
                        z=game_state.ball.physics.velocity.z if game_state.ball.physics.velocity is not None else 0.0
                    ),
                    angular_velocity=Vector3Model(
                        x=game_state.ball.physics.angular_velocity.x if game_state.ball.physics.angular_velocity is not None else 0.0,
                        y=game_state.ball.physics.angular_velocity.y if game_state.ball.physics.angular_velocity is not None else 0.0,
                        z=game_state.ball.physics.angular_velocity.z if game_state.ball.physics.angular_velocity is not None else 0.0
                    )
                )
            )

        return cls(cars=cars, ball=ball)

    def to_game_state(self) -> GameState:
        """Convert TypedGameState back to RLBot GameState"""
        cars = {}
        for idx, car in self.cars.items():
            cars[idx] = CarState(
                physics=Physics(
                    location=Vector3(
                        x=car.physics.location.x,
                        y=car.physics.location.y,
                        z=car.physics.location.z
                    ),
                    rotation=Rotator(
                        pitch=car.physics.rotation.pitch,
                        yaw=car.physics.rotation.yaw,
                        roll=car.physics.rotation.roll
                    ),
                    velocity=Vector3(
                        x=car.physics.velocity.x,
                        y=car.physics.velocity.y,
                        z=car.physics.velocity.z
                    ),
                    angular_velocity=Vector3(
                        x=car.physics.angular_velocity.x,
                        y=car.physics.angular_velocity.y,
                        z=car.physics.angular_velocity.z
                    )
                ),
                boost_amount=car.boost_amount,
                jumped=car.jumped,
                double_jumped=car.double_jumped
            )

        ball = None
        if self.ball is not None:
            ball = BallState(
                physics=Physics(
                    location=Vector3(
                        x=self.ball.physics.location.x,
                        y=self.ball.physics.location.y,
                        z=self.ball.physics.location.z
                    ),
                    rotation=Rotator(
                        pitch=self.ball.physics.rotation.pitch,
                        yaw=self.ball.physics.rotation.yaw,
                        roll=self.ball.physics.rotation.roll
                    ),
                    velocity=Vector3(
                        x=self.ball.physics.velocity.x,
                        y=self.ball.physics.velocity.y,
                        z=self.ball.physics.velocity.z
                    ),
                    angular_velocity=Vector3(
                        x=self.ball.physics.angular_velocity.x,
                        y=self.ball.physics.angular_velocity.y,
                        z=self.ball.physics.angular_velocity.z
                    )
                )
            )

        return GameState(cars=cars, ball=ball)

class CustomScenario(BaseModel):
    """A custom scenario that can be saved to and loaded from disk.
    
    Attributes:
        name: The name of the scenario
        game_state: The game state for this scenario
    """
    name: str
    game_state: TypedGameState

    @classmethod
    def from_rlbot_game_state(cls, name: str, game_state: GameState) -> 'CustomScenario':
        """Create a CustomScenario from an RLBot GameState"""
        return cls(
            name=name,
            game_state=TypedGameState.from_game_state(game_state)
        )

    def to_rlbot_game_state(self) -> GameState:
        """Convert this scenario back to an RLBot GameState"""
        return self.game_state.to_game_state()

    def get_number_of_cars(self) -> int:
        return len(self.game_state.cars)

    def create_randomized_copy(self) -> 'CustomScenario':
        """Add random variance to the game state"""
        # TODO: Finetune these or make them configurable
        yaw_variance = 0.5 * np.pi
        velocity_variance = 0.5
        boost_variance = 0.5

        randomized_scenario = CustomScenario.model_copy(self, deep=True)
        for car in randomized_scenario.game_state.cars.values():
            # Randomize yaw
            yaw = car.physics.rotation.yaw
            yaw = yaw + utils.random_between(-yaw_variance, yaw_variance)
            car.physics.rotation.yaw = yaw

            # Randomize velocity (TODO: If we rotate yaw, we might want to rotate velocity as well?)
            velocity = car.physics.velocity
            velocity.z *= utils.random_between(1-velocity_variance, 1+velocity_variance)
            velocity.x *= utils.random_between(1-velocity_variance, 1+velocity_variance)
            velocity.y *= utils.random_between(1-velocity_variance, 1+velocity_variance)
            car.physics.velocity = velocity

            # Randomize boost amount
            car.boost_amount =  car.boost_amount * utils.random_between(1-boost_variance, 1+boost_variance)

        if randomized_scenario.game_state.ball is not None:
            # Randomize ball velocity
            ball = randomized_scenario.game_state.ball
            ball.physics.velocity.z *= utils.random_between(1-velocity_variance, 1+velocity_variance)
            ball.physics.velocity.x *= utils.random_between(1-velocity_variance, 1+velocity_variance)
            ball.physics.velocity.y *= utils.random_between(1-velocity_variance, 1+velocity_variance)
            randomized_scenario.game_state.ball = ball

            # Randomize ball yaw
            pass # Implement if needed

        return randomized_scenario

    def adjust_to_target_player_amount(self, target_red_team_size: int, target_blue_team_size: int) -> 'CustomScenario':
        # Let's assume typical 1v1, 2v2, 3v3, 4v4 scenarios with equally large teams
        import math
        new_scenario = CustomScenario.model_copy(self, deep=True)

        # Get specs of the current scenario
        num_players = len(self.game_state.cars)
        blue_team_size = math.ceil(num_players / 2)  # Blue team is filled first in case we have uneven amount
        red_team_size = num_players - blue_team_size  # Rest are on red
        blue_cars = list(self.game_state.cars.values())[:blue_team_size]
        red_cars = list(self.game_state.cars.values())[blue_team_size:]

        # Get specs of the desired scenario
        # target_blue_team_size = math.ceil(target_player_amount / 2)
        # target_red_team_size = target_player_amount - target_blue_team_size
        new_cars = {}
        padded_car = CarStateModel(physics=PhysicsModel(
            location=Vector3Model(x=50000, y=50000, z=50000), # Just move the car so far it cannot get back
            angular_velocity=Vector3Model(x=0, y=0, z=0)))

        # Reorder cars to fit target player amount
        for i in range(target_blue_team_size):
            if i < len(blue_cars):
                new_cars[i] = blue_cars[i]
            else:
                new_cars[i] = padded_car
        for i_offset in range(target_red_team_size):
            i = target_blue_team_size + i_offset
            if i_offset < len(red_cars):
                new_cars[i] = red_cars[i_offset]
            else:
                new_cars[i] = padded_car

        new_scenario.game_state.cars = new_cars
        return new_scenario




    def save(self) -> None:
        """Save this scenario to disk"""
        if not self.name:
            raise ValueError("Scenario must have a name before saving")
        
        # Ensure the scenarios directory exists
        os.makedirs(_get_custom_scenarios_path(), exist_ok=True)
        
        # Save to file
        file_path = os.path.join(_get_custom_scenarios_path(), f"{self.name}.json")
        with open(file_path, "w") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, name: str) -> 'CustomScenario':
        """Load a specific scenario by name"""
        file_path = os.path.join(_get_custom_scenarios_path(), f"{name}.json")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No scenario found with name '{name}'")
        
        with open(file_path, "r") as f:
            return cls.model_validate_json(f.read())



def get_custom_scenarios():
    """Get all custom scenarios"""
    custom_scenarios = {}
    for file in os.listdir(_get_custom_scenarios_path()):
        if file.endswith(".json"):
            custom_scenarios[file.replace(".json", "")] = CustomScenario.load(file.replace(".json", ""))
    return custom_scenarios

def _get_custom_scenarios_path():
    appdata_path = os.path.expandvars("%APPDATA%")
    if not os.path.exists(os.path.join(appdata_path, "RLBot", "Dojo", "Scenarios")):
        os.makedirs(os.path.join(appdata_path, "RLBot", "Dojo", "Scenarios"))
    return os.path.join(appdata_path, "RLBot", "Dojo", "Scenarios")
