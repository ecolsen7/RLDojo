# Dojo Refactoring Proposal

## Current Issues with the Codebase

### 1. **Over-Abstraction**
- `BaseGameMode` abstract class with minimal value
- Separate `ScenarioMode` and `RaceMode` classes that could be simple functions
- Complex state machine with `ScenarioPhase` and `RacePhase` enums
- Multiple layers of indirection between menu → mode → state

### 2. **Scattered Functionality**
- Logic spread across 8+ files in different directories
- Simple functionality broken into tiny files (e.g., `simulation.py` is 13 lines)
- Hard to follow the flow from user input to game state changes

### 3. **Complex State Management**
- `DojoGameState` class with tons of properties
- Multiple enums for phases that could be simple booleans
- State transitions handled by multiple different handlers

### 4. **Redundant Function Calls**
- Menu selection → calls mode handler → calls state updater → calls game interface
- Keyboard input → keyboard handler → callback registry → menu renderer → mode logic
- Too many layers for simple operations

### 5. **Hard-to-Follow Menu System**
- `MenuRenderer` with complex column logic and scrolling
- `UIElement` class with submenu nesting
- Separate menu setup in different functions

## Proposed Simplified Structure

### **Single Main File: `dojo_simple.py`**

Instead of:
```
dojo.py (426 lines)
├── game_modes/
│   ├── base_mode.py (57 lines)
│   ├── scenario_mode.py (213 lines) 
│   └── race_mode.py (177 lines)
├── state/
│   └── game_state.py (129 lines)
├── input/
│   └── keyboard_handler.py (123 lines)
├── rendering/
│   └── ui_renderer.py (168 lines)
└── menu.py (255 lines)
```

We get:
```
dojo_simple.py (400 lines) - Everything in one place
```

### **Key Simplifications**

#### 1. **Direct State Management**
```python
# Instead of complex state machine:
class DojoGameState:
    gym_mode: GymMode
    game_phase: Union[ScenarioPhase, RacePhase]
    # ... 50+ properties

# Simple direct properties:
self.mode = Mode.SCENARIO  # or Mode.RACE
self.in_menu = False
self.paused = False
```

#### 2. **Direct Keyboard Handling**
```python
# Instead of callback registry system:
keyboard_handler.register_callback('menu_toggle', self._menu_toggle)

# Direct keyboard setup:
keyboard.add_hotkey('m', self._toggle_menu)
```

#### 3. **Simple Menu System**
```python
# Instead of UIElement classes and MenuRenderer:
self.menu_items = [
    ("Reset Score", self._reset_score),
    ("Toggle Mirror", self._toggle_mirror),
    # ... simple (text, function) tuples
]
```

#### 4. **Inline Mode Logic**
```python
# Instead of separate mode classes:
if self.mode == Mode.SCENARIO:
    self._update_scenario_mode(packet)
elif self.mode == Mode.RACE:
    self._update_race_mode(packet)
```

## Benefits of Simplified Structure

### **1. Readability**
- All logic in one file - easy to see the full picture
- Clear flow from input → logic → rendering
- No need to jump between files to understand behavior

### **2. Maintainability**
- Fewer abstractions = fewer places for bugs to hide
- Direct function calls instead of callback registries
- Simple state instead of complex state machines

### **3. Debuggability**
- Can see the entire execution flow in one file
- No mysterious callbacks or phase transitions
- Easy to add print statements and debug

### **4. Performance**
- Fewer function call layers
- No callback lookup overhead
- Direct property access instead of state machine queries

### **5. Extensibility**
- Easy to add new features - just add a function and menu item
- No need to understand complex architecture patterns
- Clear where to make changes

## Migration Path

### **Phase 1: Create Simplified Version**
1. ✅ Create `dojo_simple.py` with core functionality
2. Keep existing files for reference
3. Test that simplified version works

### **Phase 2: Feature Parity**
1. Ensure all existing features work in simplified version
2. Add any missing functionality
3. Test thoroughly

### **Phase 3: Replace Original**
1. Replace `dojo.py` with simplified version
2. Remove unnecessary files:
   - `game_modes/` directory
   - `input/keyboard_handler.py`
   - `rendering/ui_renderer.py`
   - Complex parts of `menu.py`

### **Phase 4: Clean Up**
1. Keep only essential files:
   - `dojo.py` (simplified)
   - `scenario.py`
   - `playlist.py`
   - `records.py`
   - `utils.py`
   - `modifier.py` (for custom mode)

## Code Comparison

### **Menu Toggle - Current vs Simplified**

**Current (Complex):**
```python
# dojo.py
def _menu_toggle(self):
    if self.game_state.gym_mode == GymMode.RACE:
        if self.game_state.game_phase == RacePhase.MENU:
            self.game_state.game_phase = self.previous_phase or RacePhase.ACTIVE
        else:
            self.previous_phase = self.game_state.game_phase
            self.game_state.game_phase = RacePhase.MENU

# Plus keyboard_handler.py callback registration
# Plus menu_renderer.py rendering logic
```

**Simplified:**
```python
def _toggle_menu(self):
    self.in_menu = not self.in_menu
    if self.in_menu:
        self.menu_selection = 0
```

### **Mode Switching - Current vs Simplified**

**Current (Complex):**
```python
def _set_race_mode(self, trials):
    self.game_state.gym_mode = GymMode.RACE
    self.game_state.game_phase = RacePhase.INIT
    self.game_state.num_trials = trials
    if self.current_mode:
        self.current_mode.cleanup()
    self.current_mode = self.race_mode
```

**Simplified:**
```python
def _start_race(self, trials):
    self.mode = Mode.RACE
    self.race_trials = trials
    self.race_current_trial = 0
    self.race_times = []
    self._setup_next_race_trial()
```

## Conclusion

The simplified structure reduces the codebase from ~1550 lines across 8 files to ~400 lines in 1 file, while maintaining all functionality and making the code much more readable and maintainable.

**Next Steps:**
1. Test the simplified version to ensure it works correctly
2. Add any missing features from the original
3. Once confirmed working, replace the original structure 
