import json
import os

class InputEngine:
    def __init__(self, data_path="data/combos.json", config_path="data/config.json"):
        self.buffer_size = 60
        self.frame_buffer = []
        self.combo_data = {}
        self.data_path = data_path
        self.config_path = config_path
        
        # Load data first, then config/prefs
        self.load_data()
        self.load_config()
        
        self.current_combo = None
        self.combo_step = 0
        self.last_input_frame = 0

    def load_data(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r') as f:
                self.combo_data = json.load(f).get("characters", {})

    def load_config(self):
        # Default fallback map now includes a RESET utility key mapping (e.g., Space)
        # and distinct arrow mappings for directions for full keyboard realism
        default_map = {
            'w': 'up', 'a': 'left', 's': 'down', 'd': 'right',
            'u': 'P', 'i': 'K', 'o': 'S', 'j': 'H', 'k': 'D',
            'space': 'RESET',
            # Add explicit arrow keys for direction keys visual/logic parity if drawn separately
            'Up': 'up', 'Down': 'down', 'Left': 'left', 'Right': 'right' 
        }
        
        # Default fallback preferences now include the visualizer type (hitbox/keyboard)
        default_prefs = {"visualizer": "hitbox"}
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.key_map = data.get("keybinds", default_map)
                    self.prefs = data.get("prefs", default_prefs)
            except json.JSONDecodeError:
                self.key_map = default_map
                self.prefs = default_prefs
        else:
            self.key_map = default_map
            self.prefs = default_prefs
            self.save_config()

    def save_config(self, new_map=None, new_prefs=None):
        if new_map:
            self.key_map = new_map
        if new_prefs:
            self.prefs = new_prefs
            
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            # Save both bindings and preferences in a nested structure
            json.dump({
                "keybinds": self.key_map,
                "prefs": self.prefs
            }, f, indent=4)

    def get_characters(self):
        return list(self.combo_data.keys())

    def get_combos(self, char):
        return [c["name"] for c in self.combo_data.get(char, [])]

    def load_combo(self, char, combo_name):
        for c in self.combo_data.get(char, []):
            if c["name"] == combo_name:
                self.current_combo = c
                self.combo_step = 0
                self.frame_buffer.clear()
                return True
        return False

    def get_numpad_dir(self, held_keys):
        up = 'up' in held_keys
        down = 'down' in held_keys
        left = 'left' in held_keys
        right = 'right' in held_keys

        if left and right: left = right = False
        if up and down: up = down = False

        if up and left: return '7'
        if up and right: return '9'
        if down and left: return '1'
        if down and right: return '3'
        if up: return '8'
        if down: return '2'
        if left: return '4'
        if right: return '6'
        return '5'

    def update_buffer(self, held_keys):
        numpad_dir = self.get_numpad_dir(held_keys)
        self.frame_buffer.append(numpad_dir)
        if len(self.frame_buffer) > self.buffer_size:
            self.frame_buffer.pop(0)

    def check_input(self, pressed_button, current_frame):
        if not self.current_combo:
            return None, "No combo loaded."

        target = self.current_combo["sequence"][self.combo_step]
        expected_full = target["expected"]
        max_frames = target["max_frames"]
        
        clean_expected = expected_full.replace("c.", "").replace("f.", "").replace("j.", "")
        expected_button = clean_expected[-1] 
        expected_motion = clean_expected[:-1] if len(clean_expected) > 1 else "5"

        if pressed_button != expected_button:
            self.combo_step = 0
            return False, f"Wrong button. Expected {expected_button}, got {pressed_button}."

        frames_since_last = current_frame - self.last_input_frame
        # Account for early spawning/timing beat, maybe add some leniency, 
        # but stick to the max_frames rule
        if self.combo_step > 0 and frames_since_last > max_frames:
            self.combo_step = 0
            return False, f"Too slow! Took {frames_since_last}f (Max {max_frames}f)."

        if expected_motion != "5":
            if not self._check_motion_in_buffer(expected_motion):
                self.combo_step = 0
                return False, f"Failed motion. Expected {expected_motion}."

        self.last_input_frame = current_frame
        self.combo_step += 1
        
        is_finished = self.combo_step >= len(self.current_combo["sequence"])
        if is_finished:
            self.combo_step = 0 
            return True, "COMBO_COMPLETE"
            
        return True, f"Hit: {expected_full}"

    def _check_motion_in_buffer(self, target_motion):
        search_index = len(target_motion) - 1
        lookback_window = self.frame_buffer[-30:] 
        
        for frame_dir in reversed(lookback_window):
            if frame_dir == target_motion[search_index]:
                search_index -= 1
                if search_index < 0:
                    return True 
        return False