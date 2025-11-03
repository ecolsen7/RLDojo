import os
from enum import Enum
from typing import Dict, List, Callable, Optional
from pydantic import BaseModel, Field
import asyncio

from .async_event_loop_manager import AsyncManager
from .controller_manager import ControllerManager

class HotkeyAction(Enum):
    # RESET_SCENARIO = "reset_scenario"
    NEXT_SCENARIO = "next_scenario"
    # PREVIOUS_SCENARIO = "previous_scenario"
    TOGGLE_TIMEOUT = "toggle_timeout"
    TOGGLE_FREEZE_SCENARIO = "toggle_freeze_scenario"
    # CAPTURE_REPLAY_STATE = "capture_replay_state"


class HotkeyBindingsConfig(BaseModel):
    """Pydantic model for saving/loading hotkey bindings"""
    bindings: Dict[str, List[str]] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class HotkeyBindingsManager:
    """
    Manages hotkey bindings for actions. Supports multiple bindings per action.
    Users can bind both controller inputs and keyboard inputs to actions.
    """
    
    def __init__(self):
        self.controller_manager = ControllerManager()
        self.controller_manager.start()
        # Map from action to list of bindings (e.g., {"reset_scenario": ["A", "R", "Start"]})
        self.action_bindings: Dict[HotkeyAction, List[str]] = {action: [] for action in HotkeyAction}
        # Map from action to callback function
        self.action_callbacks: Dict[HotkeyAction, Optional[Callable]] = {action: None for action in HotkeyAction}
        # Track registered hotkeys to avoid duplicates
        self.registered_hotkeys = set()

    def stop(self) -> None:
        """Stop the hotkey manager"""
        self.unregister_bindings()
        self.controller_manager.stop()

    def get_currently_bound_keys(self, action: HotkeyAction):
        return self.action_bindings[action]
    
    def set_action_callback(self, action: HotkeyAction, callback: Callable) -> None:
        """Set the callback function for an action"""
        self.action_callbacks[action] = callback
    
    def clear_action_bindings(self, action: HotkeyAction) -> None:
        """Clear all bindings for a specific action"""
        self.action_bindings[action] = []
        print(f"Cleared all bindings for action '{action.value}'")
    
    def clear_all_bindings(self) -> None:
        """Clear all bindings for all actions"""
        for action in HotkeyAction:
            self.action_bindings[action] = []
        print("Cleared all hotkey bindings")

    def reset_default_bindings(self) -> None:
        """Reset to default hotkey bindings"""
        self.clear_all_bindings()

        # Default controller bindings
        # self._add_binding(HotkeyAction.RESET_SCENARIO, "A")
        self._add_binding(HotkeyAction.NEXT_SCENARIO, "Back")
        # self._add_binding(HotkeyAction.PREVIOUS_SCENARIO, "LB")
        # self._add_binding(HotkeyAction.TOGGLE_TIMEOUT, "X")
        # self._add_binding(HotkeyAction.TOGGLE_FREEZE_SCENARIO, "Y")
        # self._add_binding(HotkeyAction.CAPTURE_REPLAY_STATE, "Back")

        print("Reset to default hotkey bindings")

    def register_bindings(self) -> None:
        """Register all configured bindings with the ControllerHotkeyManager"""
        # Unregister previous bindings first
        self.unregister_bindings()

        # Register each binding
        for action, bindings in self.action_bindings.items():
            callback = self.action_callbacks[action]
            if callback is None:
                continue

            for binding in bindings:
                self.controller_manager.register_hotkey(binding, callback)
                self.registered_hotkeys.add(binding)

        print(f"Registered {len(self.registered_hotkeys)} hotkey bindings")

    def unregister_bindings(self) -> None:
        """Unregister all bindings from the ControllerHotkeyManager"""
        # Clear the controller manager's hotkeys dict
        for hotkey in self.registered_hotkeys:
            if hotkey in self.controller_manager.hotkeys:
                del self.controller_manager.hotkeys[hotkey]

        self.registered_hotkeys.clear()
        print("Unregistered all hotkey bindings")
    
    def get_bindings(self, action: HotkeyAction) -> List[str]:
        """Get all bindings for an action"""
        return self.action_bindings[action].copy()

    def start_interactive_rebind_for_action(
            self,
            action: HotkeyAction,
            callback: Callable[[HotkeyAction, Optional[str]], None],
            timeout: Optional[float] = 10.0
    ) -> None:
        """
        Interactively rebind an action by waiting for a controller button press.
        This method returns immediately and runs the rebinding in the background.

        Args:
            action: The action to rebind
            callback: Callback function to call when binding is complete
            timeout: Timeout in seconds (None for no timeout)
        """
        async_manager = AsyncManager.get_instance()
    
        # Schedule the coroutine to run in the background (non-blocking)
        print("Starting interactive rebind...")
        future = async_manager.run_coroutine(
            self._rebind_action_interactively_async(action, callback, timeout)
        )
        
        # Add error handling
        def _done_callback(f):
            try:
                f.result()
            except Exception as e:
                print(f"Error in rebind coroutine: {e}")
                import traceback
                traceback.print_exc()
        
        future.add_done_callback(_done_callback)
        print("Rebind scheduled in background")

    async def _rebind_action_interactively_async(
            self,
            action: HotkeyAction,
            callback: Callable[[HotkeyAction, Optional[str]], None],
            timeout: Optional[float] = 10.0
    ) -> None:
        """
        Async implementation of interactive rebinding.

        Args:
            action: The action to rebind
            callback: Callback function to call when binding is complete
            timeout: Timeout in seconds (None for no timeout)
        """
        print(f"Press a button to bind to '{action}'...")
    
        # Run the blocking wait_for_rebind in a thread pool
        # Use asyncio.get_running_loop() instead of get_event_loop()
        loop = asyncio.get_running_loop()
        binding = await loop.run_in_executor(
            None,
            self.controller_manager.wait_for_rebind, 
            timeout
        )

        if binding:
            self._add_binding(action, binding)
            print(f"Action '{action}' bound to '{binding}'")
        else:
            print(f"Rebind timeout for action '{action}'")

        if callback:
            callback(action, binding)
    
    def save(self, filepath: Optional[str] = None) -> None:
        """
        Save the current bindings configuration to a JSON file.

        Args:
            filepath: Optional custom filepath. If None, uses default config path.
        """
        if filepath is None:
            filepath = self.get_hotkey_config_path()

        # Convert action_bindings to serializable format
        bindings_dict = {action.value: bindings for action, bindings in self.action_bindings.items()}

        config = HotkeyBindingsConfig(bindings=bindings_dict)

        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Save to file
        with open(filepath, "w") as f:
            f.write(config.model_dump_json(indent=2))

        print(f"Saved hotkey bindings to {filepath}")
    
    def load(self, filepath: Optional[str] = None) -> None:
        """
        Load bindings configuration from a JSON file.

        Args:
            filepath: Optional custom filepath. If None, uses default config path.
        """
        if filepath is None:
            filepath = self.get_hotkey_config_path()

        if not os.path.exists(filepath):
            print(f"No config file found at {filepath}, using defaults")
            self.reset_default_bindings()
            return

        # Load from file
        with open(filepath, "r") as f:
            config = HotkeyBindingsConfig.model_validate_json(f.read())

        # Clear existing bindings
        self.clear_all_bindings()

        # Apply loaded bindings
        for action_str, bindings in config.bindings.items():
            try:
                action = HotkeyAction(action_str)
                self.action_bindings[action] = bindings.copy()
            except ValueError:
                print(f"Warning: Unknown action '{action_str}' in config file, skipping")

        print(f"Loaded hotkey bindings from {filepath}")
    
    def print_bindings(self) -> None:
        """Print all current bindings"""
        print("\n=== Current Hotkey Bindings ===")
        for action in HotkeyAction:
            bindings = self.action_bindings[action]
            bindings_str = ", ".join(bindings) if bindings else "(none)"
            print(f"  {action.value:30s} -> {bindings_str}")
        print("=" * 50 + "\n")
    
    def get_hotkey_config_path(self) -> str:
        """Get the path to the hotkey configuration file"""
        appdata_path = os.path.expandvars("%APPDATA%")
        config_dir = os.path.join(appdata_path, "RLBot", "Dojo")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "hotkey_bindings.json")


    def _add_binding(self, action: HotkeyAction, binding: str) -> None:
        """
        Add a binding for an action. The binding can be a controller button name
        (e.g., "A", "Start", "D-Up") or keyboard key.

        Args:
            action: The action to bind
            binding: The input binding (button/key name)
        """
        if binding not in self.action_bindings[action]:
            self.action_bindings[action].append(binding)
            print(f"Added binding '{binding}' for action '{action.value}'")

    def _remove_binding(self, action: HotkeyAction, binding: str) -> None:
        """
        Remove a specific binding from an action.

        Args:
            action: The action to unbind from
            binding: The input binding to remove
        """
        if binding in self.action_bindings[action]:
            self.action_bindings[action].remove(binding)
            print(f"Removed binding '{binding}' from action '{action.value}'")

