# Dojo Architecture Documentation

## Overview

This document describes the architecture of the Dojo training application, a modular RLBot training system designed for maintainability, testability, and extensibility.

## Architecture Design

### Modular Structure
The Dojo application uses a modular architecture with clear separation of concerns:
- Focused modules with single responsibilities
- Improved separation of concerns
- Better testability and maintainability
- Easy to extend and modify

## Module Structure

```
dojo/
├── config/
│   ├── __init__.py
│   └── constants.py          # Centralized configuration and constants
├── state/
│   ├── __init__.py
│   └── game_state.py         # Game state management and enums
├── game_modes/
│   ├── __init__.py
│   ├── base_mode.py          # Abstract base class for game modes
│   ├── scenario_mode.py      # Scenario training mode
│   └── race_mode.py          # Race training mode
├── input/
│   ├── __init__.py
│   └── keyboard_handler.py   # Keyboard input management
├── rendering/
│   ├── __init__.py
│   └── ui_renderer.py        # UI rendering logic
├── dojo.py                   # Main application class
└── [existing files...]       # Supporting modules
```

## Key Features

### 1. Separation of Concerns

**Game State Management (`state/game_state.py`)**
- Centralized game state in `DojoGameState` dataclass
- All game state logic in one place
- Clear state transitions and validation
- Helper methods for common operations

**Game Mode Handling (`game_modes/`)**
- Abstract `BaseGameMode` class defines common interface
- `ScenarioMode` and `RaceMode` handle specific game logic
- Easy to add new game modes
- Shared functionality in base class

**Input Handling (`input/keyboard_handler.py`)**
- Dedicated keyboard input management
- Callback-based architecture
- Context-aware input handling
- Easy to modify or extend controls

**UI Rendering (`rendering/ui_renderer.py`)**
- Separated rendering logic from game logic
- Modular UI components
- Consistent rendering patterns
- Easy to modify UI without affecting game logic

### 2. Configuration Management

**Constants (`config/constants.py`)**
- All configuration values in one place
- Easy to modify game parameters
- Consistent naming conventions
- Clear documentation of values

### 3. Code Organization

**Clean Architecture**
- Each module has a single responsibility
- Eliminated large switch statements
- Clearer method names and documentation
- Logical grouping of related functionality

**Improved Readability**
- Consistent coding patterns
- Better variable and method naming
- Comprehensive documentation
- Clear interfaces between components

### 4. Enhanced Maintainability

**Easier Testing**
- Each module can be tested independently
- Clear interfaces between components
- Mocked dependencies for unit testing
- Isolated functionality

**Easier Extension**
- New game modes: inherit from `BaseGameMode`
- New input handlers: register callbacks
- New UI elements: extend `UIRenderer`
- New configuration: add to constants

## Usage

### Running the Application

```python
from dojo import Dojo

if __name__ == "__main__":
    script = Dojo()
    script.run()
```

### Adding a New Game Mode

```python
from game_modes.base_mode import BaseGameMode

class NewGameMode(BaseGameMode):
    def initialize(self):
        # Setup logic
        pass
    
    def update(self, packet):
        # Game loop logic
        pass
    
    def cleanup(self):
        # Cleanup logic
        pass
```

### Adding New Input Handlers

```python
# Register new callback
keyboard_handler.register_callback('new_action', self._handle_new_action)

def _handle_new_action(self):
    # Handle the action
    pass
```

### Modifying UI

```python
# Extend UIRenderer for new UI elements
class ExtendedUIRenderer(UIRenderer):
    def render_new_element(self):
        # New rendering logic
        pass
```

## Benefits

### For Developers

1. **Easier to Understand**: Each module has a clear purpose
2. **Faster Development**: Changes are isolated to relevant modules
3. **Better Testing**: Individual components can be tested in isolation
4. **Reduced Bugs**: Smaller, focused modules are less error-prone
5. **Code Reuse**: Common functionality is shared through base classes

### For Users

1. **Reliable Functionality**: Well-structured code reduces issues
2. **Better Performance**: Efficient code organization
3. **Consistent Experience**: Standardized patterns across features
4. **Future Features**: Architecture supports easy addition of new training modes

### For Maintenance

1. **Easier Debugging**: Issues are isolated to specific modules
2. **Simpler Updates**: Changes don't affect unrelated code
3. **Better Documentation**: Each module is self-documenting
4. **Consistent Patterns**: Standardized approaches across modules

## Development Guide

### For New Contributors
- Study the module structure
- Use the appropriate module for your changes
- Follow the established patterns
- Add tests for new functionality

### Code Standards
- Each module should have a single responsibility
- Use type hints for better code clarity
- Document all public methods and classes
- Follow consistent naming conventions

## Future Enhancements

The modular architecture makes several improvements easier:

1. **Plugin System**: Easy to add new game modes as plugins
2. **Configuration UI**: Settings can be modified through UI
3. **Replay System**: Game state management supports replays
4. **Analytics**: Centralized state makes data collection easier
5. **Multiplayer**: Architecture supports multiple players
6. **Custom Controls**: Input system supports custom key bindings

## Conclusion

The Dojo training application uses a well-structured, modular architecture that follows software engineering best practices. The design provides excellent separation of concerns, making the code easier to understand, test, and extend. This foundation supports both current functionality and future development needs. 
