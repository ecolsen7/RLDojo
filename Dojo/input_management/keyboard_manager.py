
import threading
import keyboard as kb


class KeyboardManager:
    """Manages keyboard input using the keyboard library"""
    
    KEYBOARD_PREFIX = ""  # To separate keyboard hotkeys from other hotkeys (e.g., joystick A vs keyboard A)
    
    def __init__(self):
        self.hotkeys = {}
        self.keyboard_hooks = {}  # Map from hotkey name to hook object
        
        # Rebinding state
        self.rebind_mode = False
        self.rebind_result = None
        self.rebind_lock = threading.Lock()
        self.rebind_event = threading.Event()
        self.rebind_hook = None
    
    def get_keyboard_name(self, key_code):
        """Get a human-readable name for a keyboard key with prefix."""
        return f"{self.KEYBOARD_PREFIX}{key_code}"
    
    def register_hotkey(self, hotkey, callback):
        """Register a keyboard hotkey"""
        if not hotkey.startswith(self.KEYBOARD_PREFIX):
            return False  # Not a keyboard hotkey
        
        # Remove existing hotkey if it exists
        if hotkey in self.keyboard_hooks:
            try:
                kb.remove_hotkey(self.keyboard_hooks[hotkey])
            except:
                pass
            del self.keyboard_hooks[hotkey]
        
        self.hotkeys[hotkey] = callback
        
        # Register with keyboard library
        key_name = hotkey[len(self.KEYBOARD_PREFIX):]  # Remove prefix
        try:
            hook = kb.add_hotkey(key_name, callback, suppress=False)
            self.keyboard_hooks[hotkey] = hook
            print(f"Registered keyboard hotkey: {key_name}")
            return True
        except Exception as e:
            print(f"Failed to register keyboard hotkey '{key_name}': {e}")
            return False
    
    def unregister_hotkey(self, hotkey):
        """Unregister a specific keyboard hotkey"""
        if hotkey in self.hotkeys:
            del self.hotkeys[hotkey]
        
        if hotkey in self.keyboard_hooks:
            try:
                kb.remove_hotkey(self.keyboard_hooks[hotkey])
            except:
                pass
            del self.keyboard_hooks[hotkey]
    
    def wait_for_rebind(self, timeout=None):
        """
        Wait for a keyboard key press and return the key name.
        
        Args:
            timeout: Optional timeout in seconds. None means wait indefinitely.
            
        Returns:
            str: The name of the key that was pressed, or None if timeout occurred.
        """
        print("KeyboardManager.wait_for_rebind()")
        with self.rebind_lock:
            self.rebind_mode = True
            self.rebind_result = None
            self.rebind_event.clear()
        
        # Set up temporary keyboard listener for rebinding
        def on_key_event(event):
            with self.rebind_lock:
                if self.rebind_mode and event.event_type == 'down':
                    key_name = self.get_keyboard_name(event.name)
                    self.rebind_result = key_name
                    self.rebind_event.set()
        
        # Hook keyboard events temporarily
        self.rebind_hook = kb.hook(on_key_event)
        
        try:
            print("Waiting for keyboard input...")
            key_detected = self.rebind_event.wait(timeout=timeout)
            print("Wait complete")
            
            with self.rebind_lock:
                self.rebind_mode = False
                result = self.rebind_result
                self.rebind_result = None
            
            print("Returning keyboard result")
            return result if key_detected else None
        finally:
            # Unhook the temporary rebind hook
            if self.rebind_hook is not None:
                try:
                    kb.unhook(self.rebind_hook)
                except:
                    pass
                self.rebind_hook = None
    
    def stop(self):
        """Stop the keyboard manager and clean up"""
        for hotkey_name, hook in list(self.keyboard_hooks.items()):
            try:
                kb.remove_hotkey(hook)
            except:
                pass
        self.keyboard_hooks.clear()
        kb.unhook_all()
