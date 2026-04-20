import tkinter as tk
from tkinter import ttk
import time
import math
import re
from input_engine import InputEngine

# Visual Configuration
PIXELS_PER_FRAME = 6
PLAYHEAD_X = 150 # Moved to the left for Rhythm Game style
TRACK_Y = 50

# Neon Cyberpunk Palette
BG_COLOR = "#0f0f15"
PANEL_COLOR = "#1a1a24"
TEXT_COLOR = "#00ffcc"
ACCENT_COLOR = "#ff007f"

# Neon Button colors matching block colors
BTN_COLORS = {
    'P': '#ff00bb', # Neon Pink
    'K': '#00d4ff', # Cyan
    'S': '#00ff88', # Neon Green
    'H': '#ff2a00', # Electric Red
    'D': '#ffaa00', # Orange
    'DIR': '#ffffff', # White for directions
    'RESET': '#ff33ff' 
}

class TrainerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GGST Combo Trainer V1.6 - Rhythm Engine & Full Keyboard")
        self.geometry("800x750")
        self.configure(bg=BG_COLOR)
        
        self.engine = InputEngine()
        
        # Timing State
        self.fps = 60
        self.frame_duration = 1.0 / self.fps
        self.current_frame = 0
        self.last_tick_time = time.perf_counter()
        
        # Training Environment State
        self.state = "IDLE" # IDLE, COUNTDOWN, PRACTICING, RESULT
        self.state_timer = 0
        self.result_timer = 0
        self.combo_timer = 0 
        self.target_timeline = [] 
        self.canvas_bg = "#050508"
        self.overlay_text = ""
        
        # Input State
        self.keys_held = set()
        
        self.create_widgets()
        self.populate_ui()
        
        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<KeyRelease>", self.on_key_release)
        
        self.tick()

    def create_widgets(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background=PANEL_COLOR)
        style.configure('TLabel', background=PANEL_COLOR, foreground="white")
        style.configure('TButton', background="#333", foreground="white", borderwidth=0, padding=5)
        style.map('TButton', background=[('active', ACCENT_COLOR)])
        
        # Top Menu
        menu_frame = ttk.Frame(self, padding=15)
        menu_frame.pack(fill=tk.X, pady=(0, 10))

        self.char_var = tk.StringVar()
        self.char_cb = ttk.Combobox(menu_frame, textvariable=self.char_var, state="readonly", width=15)
        self.char_cb.pack(side=tk.LEFT, padx=5)
        self.char_cb.bind("<<ComboboxSelected>>", self.on_char_select)

        self.combo_var = tk.StringVar()
        self.combo_cb = ttk.Combobox(menu_frame, textvariable=self.combo_var, state="readonly", width=30)
        self.combo_cb.pack(side=tk.LEFT, padx=5)
        self.combo_cb.bind("<<ComboboxSelected>>", self.on_combo_select)

        self.btn_settings = ttk.Button(menu_frame, text="⚙️ Settings", command=self.open_settings)
        self.btn_settings.pack(side=tk.RIGHT, padx=5)

        # Dynamic Target Display
        target_frame = tk.Frame(self, bg=BG_COLOR)
        target_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_status = tk.Label(target_frame, text="STANDBY", font=("Impact", 14), bg=BG_COLOR, fg="#555")
        self.lbl_status.pack()

        self.lbl_target = tk.Label(target_frame, text="Select a route", font=("Arial Black", 24), bg=BG_COLOR, fg="white")
        self.lbl_target.pack()

        # Canvas for Rhythm Track and Visualizer
        canvas_container = tk.Frame(self, bg=BG_COLOR, padx=15)
        canvas_container.pack(fill=tk.X)
        
        self.canvas = tk.Canvas(canvas_container, height=270, bg=self.canvas_bg, highlightthickness=2, highlightbackground="#333")
        self.canvas.pack(fill=tk.X, pady=5)
        self.canvas.create_round_rect = self._create_round_rect 

        # Event Log
        self.log = tk.Text(self, height=8, state=tk.DISABLED, bg=PANEL_COLOR, fg=TEXT_COLOR, font=("Consolas", 11), bd=0, padx=10, pady=10)
        self.log.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

    def log_message(self, msg, color=TEXT_COLOR):
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, f"[F:{self.current_frame:05d}] {msg}\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def populate_ui(self):
        chars = self.engine.get_characters()
        self.char_cb["values"] = chars
        if chars:
            self.char_cb.current(0)
            self.on_char_select(None)

    def on_char_select(self, event):
        combos = self.engine.get_combos(self.char_var.get())
        self.combo_cb["values"] = combos
        if combos:
            self.combo_cb.current(0)
            self.on_combo_select(None)

    def on_combo_select(self, event):
        if self.combo_var.get():
            self.engine.load_combo(self.char_var.get(), self.combo_var.get())
            self.log_message(f"Loaded Route: {self.combo_var.get()}", "#fff")
            self.trigger_reset()

    def update_target_display(self):
        if self.engine.current_combo and self.engine.combo_step < len(self.engine.current_combo["sequence"]):
            target = self.engine.current_combo["sequence"][self.engine.combo_step]
            self.lbl_target.config(text=f"{target['expected']} ({target['move']})", fg="white")

    # --- RHYTHM GAME LOGIC ---
    def calculate_rhythm_timeline(self):
        """Pre-calculates absolute frames for blocks so they can spawn early."""
        self.target_timeline = []
        if not self.engine.current_combo: return
        
        accumulated_frames = 0
        for i, step in enumerate(self.engine.current_combo["sequence"]):
            max_f = step["max_frames"]
            if i > 0:
                accumulated_frames += max_f if max_f > 0 else 30 
                
            clean_btn = step["expected"].replace("c.", "").replace("f.", "").replace("j.", "")[-1]
            self.target_timeline.append({
                "step_index": i,
                "abs_frame": accumulated_frames,
                "btn": clean_btn,
                "full_text": step["expected"],
                "hit": False 
            })

    def trigger_reset(self):
        self.state = "COUNTDOWN"
        self.state_timer = time.time()
        self.engine.combo_step = 0
        
        # Start timer at -150 frames (2.5s) so the first block rolls in from the right
        self.combo_timer = -150 
        self.calculate_rhythm_timeline()
        self.engine.last_input_frame = self.current_frame
        
        self.canvas_bg = "#050508"
        self.lbl_status.config(text="RESETTING...", fg="#ffaa00")
        self.update_target_display()
        self.log_message("--- POSITION RESET ---")

    def trigger_result(self, success, message):
        self.state = "RESULT"
        self.state_timer = time.time()
        if success:
            self.lbl_status.config(text="EXCELLENT", fg="#00ff88")
            self.lbl_target.config(text="COMBO COMPLETE!", fg="#00ff88")
            self.canvas_bg = "#002211" 
        else:
            self.lbl_status.config(text="DROPPED", fg="#ff2a00")
            self.lbl_target.config(text=message, fg="#ff2a00")
            self.canvas_bg = "#330000" 
            
        self.result_timer = 0 

    # --- INPUT LOGIC ---
    def on_key_press(self, event):
        key = event.keysym.lower()
        if key not in self.keys_held:
            self.keys_held.add(key)
            mapped_action = self.engine.key_map.get(key)
            
            if mapped_action == 'RESET':
                self.trigger_reset()
                return

            if mapped_action in ['P', 'K', 'S', 'H', 'D'] or mapped_action in ['up', 'down', 'left', 'right']:
                if self.state == "PRACTICING":
                    success, message = self.engine.check_input(mapped_action, self.current_frame)
                    
                    if success:
                        if self.engine.combo_step > 0:
                            self.target_timeline[self.engine.combo_step - 1]["hit"] = True
                            
                        if message == "COMBO_COMPLETE":
                            self.trigger_result(True, "")
                        else:
                            self.log_message(f"HIT: {message}")
                            self.update_target_display()
                    else:
                        self.log_message(f"MISS: {message}")
                        self.trigger_result(False, message)

    def on_key_release(self, event):
        key = event.keysym.lower()
        if key in self.keys_held:
            self.keys_held.remove(key)

    # --- SETTINGS MENU ---
    def open_settings(self):
        win = tk.Toplevel(self)
        win.title("Map Hardware Controls & Prefs")
        win.geometry("320x550")
        win.configure(bg=BG_COLOR)
        win.transient(self)
        win.grab_set() 
        
        ttk.Label(win, text="VISUALIZER TYPE", bg=BG_COLOR, fg=ACCENT_COLOR, font=("Arial", 10, "bold")).pack(pady=(15, 5))
        self.temp_vis = tk.StringVar(value=self.engine.prefs.get("visualizer", "hitbox"))
        
        vis_frame = tk.Frame(win, bg=BG_COLOR)
        vis_frame.pack()
        ttk.Radiobutton(vis_frame, text="Hitbox", variable=self.temp_vis, value="hitbox", bg=BG_COLOR, fg="white", selectcolor="#333").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(vis_frame, text="Keyboard", variable=self.temp_vis, value="keyboard", bg=BG_COLOR, fg="white", selectcolor="#333").pack(side=tk.LEFT, padx=10)

        tk.Label(win, text="-"*30, bg=BG_COLOR, fg="#333").pack(pady=10)
        ttk.Label(win, text="KEYBINDS: Click an action, press physical key.", bg=BG_COLOR, fg="white", pady=10).pack()
        
        self.temp_binds = self.engine.key_map.copy()
        action_to_key = {v: k for k, v in self.temp_binds.items()}
        actions = ['up', 'down', 'left', 'right', 'P', 'K', 'S', 'H', 'D', 'RESET']
        
        frame = tk.Frame(win, bg=BG_COLOR)
        frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        self.binding_buttons = {}
        for idx, action in enumerate(actions):
            ttk.Label(frame, text=f"{action.upper()}:", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")).grid(row=idx, column=0, pady=6, sticky=tk.E)
            current_key = action_to_key.get(action, "UNBOUND")
            
            btn = tk.Button(frame, text=current_key.upper(), bg="#333", fg="white", width=12, relief=tk.FLAT)
            btn.config(command=lambda a=action, b=btn: self.listen_for_bind(a, b, win))
            btn.grid(row=idx, column=1, padx=10, pady=6)
            self.binding_buttons[action] = btn

        save_btn = tk.Button(win, text="SAVE CONFIG", bg=ACCENT_COLOR, fg="white", font=("Arial", 12, "bold"), relief=tk.FLAT, command=lambda: self.save_settings(win))
        save_btn.pack(pady=20, fill=tk.X, padx=20)

    def listen_for_bind(self, action, btn, window):
        btn.config(text="PRESS KEY...", bg="#00d4ff", fg="black")
        bind_id = window.bind("<KeyPress>", lambda e: self.register_bind(e, action, btn, window))
        window.bind_id = bind_id

    def register_bind(self, event, action, btn, window):
        new_key = event.keysym.lower()
        keys_to_remove = [k for k, v in self.temp_binds.items() if v == action]
        for k in keys_to_remove: del self.temp_binds[k]
            
        if new_key in self.temp_binds:
            old_action = self.temp_binds[new_key]
            if old_action in self.binding_buttons:
                self.binding_buttons[old_action].config(text="UNBOUND", bg="#333", fg="white")
                
        self.temp_binds[new_key] = action
        btn.config(text=new_key.upper(), bg="#333", fg="white")
        window.unbind("<KeyPress>", window.bind_id)

    def save_settings(self, window):
        new_prefs = {"visualizer": self.temp_vis.get()}
        self.engine.save_config(self.temp_binds, new_prefs)
        self.keys_held.clear()
        window.destroy()

    # --- CORE LOOP ---
    def tick(self):
        now = time.perf_counter()
        elapsed = now - self.last_tick_time
        
        if elapsed >= self.frame_duration:
            self.current_frame += 1
            self.last_tick_time = now
            
            held_mapped = [self.engine.key_map[k] for k in self.keys_held if k in self.engine.key_map]
            self.engine.update_buffer(held_mapped)
            
            self.process_state_machine()
            self.render_canvas()
            
        self.after(1, self.tick)

    def process_state_machine(self):
        if self.state in ["COUNTDOWN", "PRACTICING"]:
            self.combo_timer += 1

        if self.state == "COUNTDOWN":
            if self.combo_timer < -110: 
                self.overlay_text = "3"
            elif self.combo_timer < -70: 
                self.overlay_text = "2"
            elif self.combo_timer < -30: 
                self.overlay_text = "1"
            elif self.combo_timer < 0: 
                self.overlay_text = "ROCK!"
                self.lbl_status.config(text="RECORDING", fg=ACCENT_COLOR)
            else:
                self.state = "PRACTICING"
                self.overlay_text = ""
                # Hard sync logic frame to visual frame 0
                self.engine.last_input_frame = self.current_frame 
                
        elif self.state == "RESULT":
            self.result_timer += 1
            if self.result_timer > 90:
                self.canvas_bg = "#050508"
                self.state = "IDLE"
                self.lbl_status.config(text="PRESS RESET KEY", fg="#555")

    # --- RENDERING ---
    def render_canvas(self):
        self.canvas.delete("all")
        self.canvas.config(bg=self.canvas_bg)
        
        self.draw_rhythm_track()
        
        if self.engine.prefs.get("visualizer") == "keyboard":
            self.draw_full_keyboard()
        else:
            self.draw_hitbox_visualizer()

        # Countdown Overlay
        if getattr(self, "overlay_text", "") and self.state == "COUNTDOWN":
            scale_mod = math.sin(self.combo_timer * 0.1) * 10
            font_size = int(50 + scale_mod)
            color = ACCENT_COLOR if self.overlay_text == "ROCK!" else "#fff"
            self.canvas.create_text(400, 60, text=self.overlay_text, font=("Impact", font_size, "italic"), fill=color)

    def draw_rhythm_track(self):
        # Draw track background
        self.canvas.create_rectangle(0, TRACK_Y - 30, 800, TRACK_Y + 30, fill="#111", outline="#333")
        
        # Draw blocks
        if self.state in ["COUNTDOWN", "PRACTICING", "RESULT"]:
            for block in self.target_timeline:
                if block["hit"]: continue 
                
                # Identify actual button to assign color
                combat_btn_re = re.compile(r"[P|K|S|H|D|RESET]")
                match = combat_btn_re.search(block["full_text"])
                target_combat_btn = match.group(0) if match else block["btn"]
                is_dir = target_combat_btn not in ['P', 'K', 'S', 'H', 'D', 'RESET']

                # Position slides left as combo_timer increases
                x_pos = PLAYHEAD_X + (block["abs_frame"] - self.combo_timer) * PIXELS_PER_FRAME
                
                if -50 < x_pos < 850:
                    r_color = BTN_COLORS.get(target_combat_btn, "#fff") if not is_dir else "#333"
                    width_mod = 2 if not is_dir else 1
                    
                    self.canvas.create_rectangle(x_pos - 15, TRACK_Y - 20, x_pos + 15, TRACK_Y + 20, fill=r_color, outline="#fff", width=width_mod)
                    self.canvas.create_text(x_pos, TRACK_Y, text=block["full_text"], font=("Arial", 10, "bold"), fill="#000" if not is_dir else "#fff")

        # Draw Playhead
        self.canvas.create_line(PLAYHEAD_X, TRACK_Y - 40, PLAYHEAD_X, TRACK_Y + 40, fill="#00ffcc", width=3)
        self.canvas.create_polygon(PLAYHEAD_X - 8, TRACK_Y - 40, PLAYHEAD_X + 8, TRACK_Y - 40, PLAYHEAD_X, TRACK_Y - 25, fill="#00ffcc")
        self.canvas.create_polygon(PLAYHEAD_X - 8, TRACK_Y + 40, PLAYHEAD_X + 8, TRACK_Y + 40, PLAYHEAD_X, TRACK_Y + 25, fill="#00ffcc")

    def _create_round_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1,
                  x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius,
                  x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2,
                  x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return self.canvas.create_polygon(points, **kwargs, smooth=True)

    def draw_hitbox_visualizer(self):
        base_y = 170
        held_mapped = [self.engine.key_map[k] for k in self.keys_held if k in self.engine.key_map]

        buttons = [
            ('left', 200, base_y + 10, 18), ('down', 245, base_y + 20, 18),
            ('right', 290, base_y + 10, 18), ('up', 245, base_y + 60, 22), 
            ('P', 400, base_y + 5, 20), ('S', 450, base_y - 10, 20),
            ('D', 500, base_y - 10, 20), ('K', 400, base_y + 50, 20),
            ('H', 450, base_y + 35, 20), ('RESET', 350, base_y + 70, 15)
        ]

        self.canvas.create_round_rect(160, 120, 540, 245, radius=15, fill="#151520", outline="#333", width=2)
        self.canvas.create_text(350, 140, text="VIRTUAL HITBOX CONTROLLER", font=("Consolas", 10, "bold"), fill="#555")

        for action, x, y, r in buttons:
            is_active = action in held_mapped
            
            if action in ['up', 'down', 'left', 'right']:
                base_color = "#222"
                glow_color = "#fff" if is_active else "#111"
                color = glow_color if is_active else base_color
            elif action == 'RESET':
                 base_color = "#222"
                 glow_color = ACCENT_COLOR if is_active else "#111" 
                 color = glow_color if is_active else base_color
            else:
                base_color = "#222" 
                glow_color = BTN_COLORS.get(action, "#fff") if is_active else "#111" 
                color = glow_color if is_active else base_color

            if is_active and action not in ['up', 'down', 'left', 'right', 'RESET']:
                 glow_r = r + 8
                 self.canvas.create_oval(x - glow_r, y - glow_r, x + glow_r, y + glow_r, fill="", outline=glow_color, width=2)

            self.canvas.create_oval(x - r - 2, y - r - 2, x + r + 2, y + r + 2, fill="#333", outline="")
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=glow_color if is_active else "#000", width=2)
            
            label = action.upper() if action in ['P', 'K', 'S', 'H', 'D'] else ""
            if label:
                text_color = "#000" if is_active else "#777"
                self.canvas.create_text(x, y, text=label, font=("Arial", 12, "bold"), fill=text_color)

    def draw_full_keyboard(self):
        base_y = 120
        keys_rows = [
            ['Q','W','E','R','T','Y','U','I','O','P','['],
            ['A','S','D','F','G','H','J','K','L',';','\''],
            ['Z','X','C','V','B','N','M',',','.','/'],
            ['Ctrl', 'Alt', 'Space', 'Alt', 'Ctrl']
        ]
        arrow_keys = [('←', 'left'), ('↑', 'up'), ('↓', 'down'), ('→', 'right')]

        self.canvas.create_round_rect(160, 110, 560, 255, radius=15, fill="#151520", outline="#333", width=2)
        self.canvas.create_text(360, 125, text="MECHANICAL KEYBOARD VISUALIZER", font=("Consolas", 10, "bold"), fill="#555")

        held_mapped = [self.engine.key_map[k] for k in self.keys_held if k in self.engine.key_map]

        x_start = 170
        y_start = 140
        key_w = 22
        key_h = 22
        key_gap_x = 6
        key_gap_y = 6
        row_offsets = [0, 8, 16, 0] 

        for row_idx, row in enumerate(keys_rows):
            x = x_start + row_offsets[row_idx]
            y = y_start + (key_h + key_gap_y)*row_idx
            
            if row_idx == 3: 
                 key_widths = [22, 22, 120, 22, 22]
                 x += 40 
                 for idx, key_w_val in enumerate(key_widths):
                      key_text = row[idx]
                      mapped_action = 'RESET' if key_text == "Space" else self.engine.key_map.get(key_text.lower())
                      
                      is_active = mapped_action in held_mapped
                      is_mapped = mapped_action in ['P','K','S','H','D','RESET','up','down','left','right']
                      
                      base_color = "#222"
                      unpressed_outline = "#fff" if mapped_action in ['up','down','left','right','RESET'] else BTN_COLORS.get(mapped_action, "#333")
                      pressed_color = BTN_COLORS.get(mapped_action, "#fff") if mapped_action not in ['up','down','left','right'] else "#fff"

                      color = pressed_color if is_active else base_color
                      outline_color = pressed_color if is_active else (unpressed_outline if is_mapped else "#333")
                      glow_color = pressed_color if is_active else "#111"
                      width_mod = 2 if is_mapped else 1 
                      
                      self.canvas.create_rectangle(x, y, x + key_w_val, y + key_h, fill=color, outline=outline_color, width=width_mod)
                      
                      label = key_text.upper() if key_w_val > 22 else ""
                      if label:
                           self.canvas.create_text(x + key_w_val/2, y + key_h/2, text=label, font=("Arial", 8, "bold"), fill="#000" if is_active else "#777")
                      
                      if is_active and is_mapped and mapped_action not in ['up','down','left','right','RESET']:
                           self.canvas.create_rectangle(x-5, y-5, x + key_w_val+5, y + key_h+5, fill="", outline=glow_color, width=2)
                           
                      x += key_w_val + key_gap_x
            else:
                 for key_text in row:
                      if key_text in ['U','I','O','J','K']:
                           combat_btn_re = re.compile(r"[P|K|S|H|D|RESET]")
                           match = combat_btn_re.search(self.engine.key_map.get(key_text.lower(), "X"))
                           mapped_action = match.group(0) if match else 'DIR' 
                      elif key_text in ['W','A','S','D']:
                           mapped_action = self.engine.key_map.get(key_text.lower()) 
                      else: 
                           mapped_action = self.engine.key_map.get(key_text.lower(), 'X') 
                           
                      is_active = mapped_action in held_mapped
                      is_mapped = mapped_action in ['P','K','S','H','D','RESET','up','down','left','right'] 
                      
                      base_color = "#222"
                      unpressed_outline = "#fff" if mapped_action in ['up','down','left','right','RESET'] else BTN_COLORS.get(mapped_action, "#333")
                      pressed_color = BTN_COLORS.get(mapped_action, "#fff") if mapped_action not in ['up','down','left','right','RESET'] else "#fff"

                      color = pressed_color if is_active else base_color
                      outline_color = pressed_color if is_active else (unpressed_outline if is_mapped else "#333")
                      glow_color = pressed_color if is_active else "#111"
                      width_mod = 2 if is_mapped else 1 
                      
                      self.canvas.create_rectangle(x, y, x + key_w, y + key_h, fill=color, outline=outline_color, width=width_mod)
                      self.canvas.create_text(x + key_w/2, y + key_h/2, text=key_text, font=("Arial", 9, "bold"), fill="#000" if is_active else "#777")
                      
                      if is_active and is_mapped and mapped_action not in ['up','down','left','right','RESET']:
                           self.canvas.create_rectangle(x-4, y-4, x + key_w+4, y + key_h+4, fill="", outline=glow_color, width=2)
                           
                      x += key_w + key_gap_x

        y_arrow = y_start + (key_h + key_gap_y)*1
        x_arrow = x_start + (key_w + key_gap_x)*11 + row_offsets[1] + 15
        
        for arrow, action in arrow_keys:
             is_active = action in held_mapped
             
             color = "#fff" if is_active else "#222"
             outline_color = "#fff" if is_active else "#777"
             
             if arrow == '↑': x_a, y_a = x_arrow, y_arrow - (key_h + key_gap_y)
             elif arrow == '↓': x_a, y_a = x_arrow, y_arrow
             elif arrow == '←': x_a, y_a = x_arrow - (key_w + key_gap_x), y_arrow
             elif arrow == '→': x_a, y_a = x_arrow + (key_w + key_gap_x), y_arrow
             
             self.canvas.create_rectangle(x_a, y_a, x_a + key_w, y_a + key_h, fill=color, outline=outline_color, width=2)
             self.canvas.create_text(x_a + key_w/2, y_a + key_h/2, text=arrow, font=("Arial", 12, "bold"), fill="#000" if is_active else "#777")
             
             if is_active:
                  self.canvas.create_rectangle(x_a-4, y_a-4, x_a + key_w+4, y_a + key_h+4, fill="", outline="#fff", width=2)

if __name__ == "__main__":
    app = TrainerApp()
    app.mainloop()