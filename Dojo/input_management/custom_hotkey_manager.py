import os
from enum import Enum
from typing import Dict, List, Callable, Optional
from pydantic import BaseModel, Field
import asyncio

from .async_event_loop_manager import AsyncManager
from .controller_manager import ControllerManager
from .keyboard_manager import KeyboardManager


class HotkeyAction(Enum):
    RESET_SHOT = "Reset shot"
    TOGGLE_TIMEOUT = "Toggle timeout"
    TOGGLE_FREEZE_SCENARIO = "Toggle freeze scenario"
    SAVE_STATE_TO_PLAYLIST = "Save game state to playlist"


class HotkeyConfig(BaseModel):
    """Pydantic model for saving/loading hotkey bindings"""
    bindings: Dict[str, List[str]] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class CustomHotkeyManager:
    """
    Manages hotkey bindings for actions. Supports multiple bindings per action.
    Users can bind both controller inputs and keyboard inputs to actions.
    """
    
    def __init__(self):
        self.controller_manager = ControllerManager()
        self.keyboard_manager = KeyboardManager()
        self.controller_manager.start()
        
        # Map from action to list of bindings (e.g., {"reset_scenario": ["A", "R", "Start"]})
        self.action_bindings: Dict[HotkeyAction, List[str]] = {action: [] for action in HotkeyAction}
        # Map from action to callback function
        self.action_callbacks: Dict[HotkeyAction, Optional[Callable]] = {action: None for action in HotkeyAction}
        # Track registered hotkeys to avoid duplicates
        self.registered_hotkeys = set()

    def is_initialized(self):
        return self.controller_manager.is_initialized() and self.keyboard_manager.is_initialized()

    def stop(self) -> None:
        """Stop the hotkey manager"""
        self.unregister_bindings()
        self.controller_manager.stop()
        self.keyboard_manager.stop()
        AsyncManager.get_instance().stop()

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
        self._add_binding(HotkeyAction.RESET_SHOT, f"{ControllerManager.CONTROLLER_PREFIX}Back")
        # self._add_binding(HotkeyAction.PREVIOUS_SCENARIO, "LB")
        # self._add_binding(HotkeyAction.TOGGLE_TIMEOUT, "X")
        # self._add_binding(HotkeyAction.TOGGLE_FREEZE_SCENARIO, "Y")
        # self._add_binding(HotkeyAction.CAPTURE_REPLAY_STATE, "Back")

        print("Reset to default hotkey bindings")

    def register_bindings(self) -> None:
        """Register all configured bindings with both managers"""
        # Unregister previous bindings first
        self.unregister_bindings()

        # Register each binding
        for action, bindings in self.action_bindings.items():
            callback = self.action_callbacks[action]
            if callback is None:
                continue

            for binding in bindings:
                # Try controller first, then keyboard
                if binding.startswith(ControllerManager.CONTROLLER_PREFIX):
                    self.controller_manager.register_hotkey(binding, callback)
                else:
                    self.keyboard_manager.register_hotkey(binding, callback)
                self.registered_hotkeys.add(binding)

        print(f"Registered {len(self.registered_hotkeys)} hotkey bindings")

    def unregister_bindings(self) -> None:
        """Unregister all bindings from both managers"""
        for binding in self.registered_hotkeys:
            if binding.startswith(ControllerManager.CONTROLLER_PREFIX):
                self.controller_manager.unregister_hotkey(binding)
            else:
                self.keyboard_manager.unregister_hotkey(binding)

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
        Interactively rebind an action by waiting for a controller button or keyboard key press.
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
        Waits for either a controller button or keyboard key press (whichever comes first).

        Args:
            action: The action to rebind
            callback: Callback function to call when binding is complete
            timeout: Timeout in seconds (None for no timeout)
        """
        print(f"Press a controller button or keyboard key to bind to '{action}'...")
    
        loop = asyncio.get_running_loop()
        
        # Create tasks for both controller and keyboard input
        controller_task = loop.run_in_executor(
            None,
            self.controller_manager.wait_for_rebind, 
            timeout
        )
        
        keyboard_task = loop.run_in_executor(
            None,
            self.keyboard_manager.wait_for_rebind,
            timeout
        )
        
        # Wait for whichever completes first
        done, pending = await asyncio.wait(
            [controller_task, keyboard_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel the other task
        for task in pending:
            task.cancel()
        
        # Get the result from the completed task
        binding = None
        for task in done:
            result = await task
            if result:
                binding = result
                break

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

        config = HotkeyConfig(bindings=bindings_dict)

        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Save to file
        with open(filepath, "w") as f:
            f.write(config.model_dump_json(indent=2))

        self.register_bindings()
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
            config = HotkeyConfig.model_validate_json(f.read())

        # Clear existing bindings
        self.clear_all_bindings()

        # Apply loaded bindings
        for action_str, bindings in config.bindings.items():
            try:
                action = HotkeyAction(action_str)
                self.action_bindings[action] = bindings.copy()
            except ValueError:
                print(f"Warning: Unknown action '{action_str}' in config file, skipping")

        self.register_bindings()
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
        # If binding already bound to some other action, remove it
        for act, bindings in self.action_bindings.items():
            if binding in bindings and act != action:
                bindings.remove(binding)
                print(f"Removed binding '{binding}' from action '{act.value}' due to rebind")

        # Bind the new key
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
