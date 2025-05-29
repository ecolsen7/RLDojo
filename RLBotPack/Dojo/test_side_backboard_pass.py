#!/usr/bin/env python3
"""
Test script for the new SIDE_BACKBOARD_PASS offensive scenario
"""

from scenario import OffensiveMode, DefensiveMode, Scenario

def test_side_backboard_pass():
    """Test the new SIDE_BACKBOARD_PASS scenario"""
    print("Testing SIDE_BACKBOARD_PASS scenario...")
    
    try:
        # Create a scenario with the new mode
        scenario = Scenario(OffensiveMode.SIDE_BACKBOARD_PASS, DefensiveMode.NEAR_SHADOW)
        
        print("✓ Scenario created successfully")
        
        # Check that all required components are created
        assert scenario.offensive_car_state is not None, "Offensive car state not created"
        assert scenario.defensive_car_state is not None, "Defensive car state not created"
        assert scenario.ball_state is not None, "Ball state not created"
        
        print("✓ All scenario components created")
        
        # Check positioning logic
        ball_x = scenario.ball_state.physics.location.x
        car_x = scenario.offensive_car_state.physics.location.x
        
        # Ball and car should be on opposite sides
        assert (ball_x > 0 and car_x < 0) or (ball_x < 0 and car_x > 0), "Ball and car should be on opposite sides"
        
        print("✓ Ball and car positioned on opposite sides")
        
        # Check that ball is near the back wall
        ball_y = scenario.ball_state.physics.location.y
        assert ball_y > 2000, "Ball should be near the back wall"
        
        print("✓ Ball positioned near back wall")
        
        # Check that ball has appropriate velocity toward goal
        ball_vel_y = scenario.ball_state.physics.velocity.y
        assert ball_vel_y < 0, "Ball should be moving toward goal"
        
        print("✓ Ball moving toward goal")
        
        # Check boost levels are in correct range
        assert 12 <= scenario.offensive_car_state.boost_amount <= 100, "Offensive car boost out of range"
        assert 12 <= scenario.defensive_car_state.boost_amount <= 100, "Defensive car boost out of range"
        
        print("✓ Boost levels in correct range (12-100)")
        
        print("\n🎉 All tests passed! SIDE_BACKBOARD_PASS scenario is working correctly.")
        
        # Print scenario details for verification
        print("\nScenario Details:")
        print(f"Ball position: ({ball_x:.0f}, {ball_y:.0f}, {scenario.ball_state.physics.location.z:.0f})")
        print(f"Ball velocity: ({scenario.ball_state.physics.velocity.x:.0f}, {ball_vel_y:.0f}, {scenario.ball_state.physics.velocity.z:.0f})")
        print(f"Offensive car position: ({car_x:.0f}, {scenario.offensive_car_state.physics.location.y:.0f}, {scenario.offensive_car_state.physics.location.z:.0f})")
        print(f"Offensive car boost: {scenario.offensive_car_state.boost_amount}")
        print(f"Defensive car boost: {scenario.defensive_car_state.boost_amount}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        raise

if __name__ == "__main__":
    test_side_backboard_pass() 
