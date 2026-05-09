import json
import os

class InputEngine:
    def __init__(self, config_path="data/config.json"):
        self.buffer_size = 60
        self.frame_buffer = []
        self.moves = {}
        self.characters = []
        
        # Get absolute path to data directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(os.path.dirname(script_dir), "data")
        self.config_path = os.path.join(self.data_dir, "config.json")
        
        # Load data first, then config/prefs
        self.load_data()
        self.load_config()
        
        self.current_char = None
        self.last_input_frame = 0

    def load_data(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.characters = config.get("characters", [])
            
            for char in self.characters:
                file_name = char.lower().replace(' ', '') + '.json'
                file_path = os.path.join(self.data_dir, file_name)
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        self.moves[char] = data.get(char, {})

    def load_config(self):
        # Default fallback map now includes a RESET utility key mapping (e.g., Space)
        # and distinct arrow mappings for directions for full keyboard realism
        default_map = {
            'w': 'up', 'a': 'left', 's': 'down', 'd': 'right',
            'u': 'P', 'i': 'K', 'o': 'S', 'j': 'H', 'k': 'D',
            'space': 'RESET',
            # Arrow keys should be lowercase to match event.keysym.lower()
            'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right'
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
            
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.config_path, 'w') as f:
            # Save both bindings and preferences in a nested structure
            json.dump({
                "keybinds": self.key_map,
                "prefs": self.prefs
            }, f, indent=4)

    def get_characters(self):
        return self.characters

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
        if not self.current_char:
            return False, "No character selected."

        # Try different motion lengths, from longest to shortest
        for length in range(4, -1, -1):
            motion = ''.join(self.frame_buffer[-length:]) if length > 0 else ''
            input_str = motion + pressed_button
            if input_str in self.moves.get(self.current_char, {}):
                move_name = self.moves[self.current_char][input_str]
                self.last_input_frame = current_frame
                return True, move_name

        return False, f"No move found for input ending with {pressed_button}"