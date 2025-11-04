import os
import threading
import time
import pygame

# This is needed to capture input even when Rocket League is in focus
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"


class ControllerManager:
    """Manages game controller input using pygame"""
    
    # Standard SDL Game Controller button mapping
    BUTTON_NAMES = {
        0: "A",  # Cross on PS, B on Nintendo
        1: "B",  # Circle on PS, A on Nintendo
        2: "X",  # Square on PS, Y on Nintendo
        3: "Y",  # Triangle on PS, X on Nintendo
        4: "LB",  # L1
        5: "RB",  # R1
        6: "Back",  # Select/Share
        7: "Start",  # Start/Options
        8: "LS",  # L3 (Left stick click)
        9: "RS",  # R3 (Right stick click)
        10: "Guide",  # Home/PS button (if accessible)
        11: "Misc1",  # Share/Capture button
    }

    # D-pad hat directions
    HAT_NAMES = {
        (0, 1): "D-Up",
        (0, -1): "D-Down",
        (-1, 0): "D-Left",
        (1, 0): "D-Right",
        (-1, 1): "D-Up-Left",
        (1, 1): "D-Up-Right",
        (-1, -1): "D-Down-Left",
        (1, -1): "D-Down-Right",
        (0, 0): None,
    }

    def __init__(self):
        self.thread = None
        self.running = False
        self.hotkeys = {}
        self.keys_pressed = []
        self.dpad_pressed = []
        self.joysticks = {}
        
        # Rebinding state
        self.rebind_mode = False
        self.rebind_result = None
        self.rebind_lock = threading.Lock()
        self.rebind_event = threading.Event()

        # Debug-only components
        self.screen = None
        self.clock = None
        self.text_print = None

    def get_button_name(self, button_index, joystick):
        """Get a human-readable name for a button."""
        if button_index in self.BUTTON_NAMES:
            return self.BUTTON_NAMES[button_index]
        else:
            return f"Button {button_index}"

    def get_hat_name(self, hat_position):
        """Get a human-readable name for a hat/d-pad position."""
        return self.HAT_NAMES.get(hat_position, None)

    def start(self):
        """Start the controller input thread"""
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.start()
        return self.thread

    def stop(self):
        """Stop the controller input thread"""
        self.running = False
        if self.thread:
            self.thread.join()

    def unregister_hotkey(self, hotkey):
        """Unregister a specific controller hotkey"""
        if hotkey in self.hotkeys:
            del self.hotkeys[hotkey]

    def get_keys_pressed(self):
        """Get list of currently pressed controller buttons"""
        return self.keys_pressed

    def register_hotkey(self, hotkey, callback):
        """Register a controller button hotkey"""
        self.hotkeys[hotkey] = callback

    def wait_for_rebind(self, timeout=None):
        """
        Wait for a controller button press and return the button name.
        
        Args:
            timeout: Optional timeout in seconds. None means wait indefinitely.
            
        Returns:
            str: The name of the button that was pressed, or None if timeout occurred.
        """
        print("ControllerManager.wait_for_rebind()")
        with self.rebind_lock:
            self.rebind_mode = True
            self.rebind_result = None
            self.rebind_event.clear()

        try:
            # Wait for the pygame thread to detect a button press
            print("Waiting for controller input...")
            button_detected = self.rebind_event.wait(timeout=timeout)
            print("Wait complete")

            with self.rebind_lock:
                self.rebind_mode = False
                result = self.rebind_result
                self.rebind_result = None

            print("Returning controller result")
            return result if button_detected else None
        finally:
            # Ensure rebind mode is disabled
            with self.rebind_lock:
                self.rebind_mode = False

    def _initialize_pygame(self):
        """Initialize pygame and debug window if debug mode is enabled."""
        pygame.init()
        self.clock = pygame.time.Clock()

    def _process_events(self):
        """Process all pygame events and update joystick state."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.JOYBUTTONDOWN:
                self._handle_button_down(event)
            elif event.type == pygame.JOYBUTTONUP:
                self._handle_button_up(event)
            elif event.type == pygame.JOYHATMOTION:
                self._handle_hat_motion(event)
            elif event.type == pygame.JOYDEVICEADDED:
                self._handle_device_added(event)
            elif event.type == pygame.JOYDEVICEREMOVED:
                self._handle_device_removed(event)

    def _handle_button_down(self, event):
        """Handle button press events."""
        joystick = self.joysticks[event.instance_id]
        button_name = self.get_button_name(event.button, joystick)
        print(f"Button pressed: {button_name} (index {event.button})")

        # Check if we're in rebind mode
        with self.rebind_lock:
            if self.rebind_mode:
                self.rebind_result = button_name
                self.rebind_event.set()
                return

        # Normal hotkey handling
        print(f"Checking if '{button_name}' is in hotkeys: {button_name in self.hotkeys}")
        if button_name in self.hotkeys:
            print(f"Calling callback for '{button_name}'")
            try:
                self.hotkeys[button_name]()
            except Exception as e:
                print(f"Error calling callback for '{button_name}': {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"Available hotkeys: {list(self.hotkeys.keys())}")

    def _handle_button_up(self, event):
        """Handle button release events."""
        joystick = self.joysticks[event.instance_id]
        button_name = self.get_button_name(event.button, joystick)
        print(f"Button released: {button_name} (index {event.button})")

    def _handle_hat_motion(self, event):
        """Handle D-pad motion events."""
        hat_name = self.get_hat_name(event.value)
        if hat_name:
            print(f"D-pad: {hat_name}")

            # Check if we're in rebind mode
            with self.rebind_lock:
                if self.rebind_mode:
                    self.rebind_result = hat_name
                    self.rebind_event.set()
                    return

    def _handle_device_added(self, event):
        """Handle joystick connection events."""
        joy = pygame.joystick.Joystick(event.device_index)
        self.joysticks[joy.get_instance_id()] = joy
        print(f"Joystick {joy.get_instance_id()} connected")

    def _handle_device_removed(self, event):
        """Handle joystick disconnection events."""
        del self.joysticks[event.instance_id]
        print(f"Joystick {event.instance_id} disconnected")

    def _update_input_state(self):
        """Update the current input state by polling all connected joysticks."""
        self.keys_pressed.clear()
        self.dpad_pressed.clear()

        for joystick in self.joysticks.values():
            # Check button states
            buttons = joystick.get_numbuttons()
            for i in range(buttons):
                if joystick.get_button(i) == 1:
                    button_name = self.get_button_name(i, joystick)
                    self.keys_pressed.append(button_name)

            # Check hat/D-pad states
            hats = joystick.get_numhats()
            for i in range(hats):
                hat = joystick.get_hat(i)
                hat_name = self.get_hat_name(hat)
                if hat_name:
                    self.dpad_pressed.append(hat_name)

    def _run(self):
        """Main loop for controller input handling."""
        self._initialize_pygame()

        while self.running:
            self._process_events()
            self._update_input_state()
            self.clock.tick(30)

        pygame.quit()


if __name__ == "__main__":
    # Enable debug mode when running standalone
    manager = ControllerManager()
    thread = manager.start()
    try:
        for i in range(10):
            time.sleep(10)
            print(manager.keys_pressed)
    except KeyboardInterrupt:
        manager.stop()
    manager.stop()