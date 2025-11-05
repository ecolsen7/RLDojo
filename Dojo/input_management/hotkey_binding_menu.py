"""
Custom hotkey management menu for Dojo.

This module provides functionality for users to create, edit, and save
custom keyboard and controller hotkey bindings.
"""

import time

from .custom_hotkey_manager import HotkeyAction, CustomHotkeyManager
from menu import MenuRenderer, UIElement

class HotkeyBindingMenu:
    def __init__(self, renderer: MenuRenderer, main_menu_renderer: MenuRenderer, hotkey_manager: CustomHotkeyManager):
        self.renderer = renderer
        self.main_menu_renderer = main_menu_renderer
        self.hotkey_manager = hotkey_manager
        self.binding_started = None

    def create_menu_elements(self):
        menu = MenuRenderer(self.renderer, columns=1)
        menu.add_element(UIElement("Change Hotkey Bindings", header=True))

        for hotkey in HotkeyAction:
            timeout = 5
            show_value = lambda x=hotkey: self.hotkey_manager.get_currently_bound_keys(x)
            show_time_out = lambda x=hotkey: f"{self.binding_started + timeout - time.time():.0f} seconds"
            submenu = MenuRenderer(self.renderer, columns=1)
            submenu.add_element(UIElement(f"Rebinding action: {hotkey.value}",
                                          header=True))
            submenu.add_element(UIElement(f"Press any button on controller or keyboard to bind",
                                          header=False))
            submenu.add_element(UIElement(f"To cancel, wait ", display_value_function=show_time_out,
                                          header=False))
            menu.add_element(UIElement(hotkey.value,
                                       function=self._change_hotkey,
                                       function_args=(hotkey, timeout),
                                       display_value_function=show_value,
                                       submenu=submenu,
                                       ))

        menu.add_element(UIElement("Save/Load", header=True))
        menu.add_element(UIElement("Reset all to default", function=self.hotkey_manager.reset_default_bindings))
        menu.add_element(UIElement("Clear all bindings", function=self.hotkey_manager.clear_all_bindings))
        menu.add_element(UIElement("Undo changes", function=self.hotkey_manager.load))
        menu.add_element(UIElement("Save changes", function=self.hotkey_manager.save))

        return menu

    def _change_hotkey(self, hotkey, timeout=5):
        """Starts asynchronous rebinding for a hotkey action.
        Waits for user to bind a key, but allows the menu to display information in the mean time."""
        # Just a timer to show the user how long they have to bind a key
        self.binding_started = time.time()
        # Create a callback that goes back to previous menu when user binds a key
        callback = lambda _hotkey, new_bind: self.main_menu_renderer.handle_back_key()
        self.hotkey_manager.start_interactive_rebind_for_action(hotkey, callback=callback, timeout=timeout)
