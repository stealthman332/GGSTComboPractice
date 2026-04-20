import tkinter as tk
from tkinter import ttk
import time
import math
from input_engine import InputEngine

# Visual Configuration
PIXELS_PER_FRAME = 8
PLAYHEAD_X = 550
TRACK_BUTTON_Y = 30
TRACK_DIR_Y = 80

# Neon Cyberpunk Palette
BG_COLOR = "#0f0f15"
PANEL_COLOR = "#1a1a24"
TEXT_COLOR = "#00ffcc"
ACCENT_COLOR = "#ff007f"

BTN_COLORS = {
    'P': '#ff00bb', # Neon Pink
    'K': '#00d4ff', # Cyan
    'S': '#00ff88', # Neon Green
    'H': '#ff2a00', # Electric Red
    'D': '#ffaa00'  # Orange
}

ARROW_MAP = {
    '1': '↙', '2': '↓', '3': '↘',
    '4': '←', '5': '•', '6': '→',
    '7': '↖', '8': '↑', '9': '↗'
}

class TrainerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GGST Combo Trainer V1.4 - Training Environment")
        self.geometry("750x700")
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
        self.canvas_bg = "#050508"
        
        # Input State
        self.keys_held = set()
        self.active_buttons = {} 
        self.past_buttons = []   
        
        self.create_widgets()
        self.populate_ui()
        
        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<KeyRelease>", self.on_key_release)
        
        self.tick()

    def create_widgets(self):
        # --- Custom Styling ---
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background=PANEL_COLOR)
        style.configure('TLabel', background=PANEL_COLOR, foreground="white")
        style.configure('TButton', background="#333", foreground="white", borderwidth=0, padding=5)
        style.map('TButton', background=[('active', ACCENT_COLOR)])
        
        # --- Top Menu ---
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

        self.btn_settings = ttk.Button(menu_frame, text="⚙️ Controls", command=self.open_settings)
        self.btn_settings.pack(side=tk.RIGHT, padx=5)

        # --- Dynamic Target Display ---
        target_frame = tk.Frame(self, bg=BG_COLOR)
        target_frame.pack(fill=tk.X, pady=10)
        
        self.lbl_status = tk.Label(target_frame, text="STANDBY", font=("Impact", 14), bg=BG_COLOR, fg="#555")
        self.lbl_status.pack()

        self.lbl_target = tk.Label(target_frame, text="Select a route", font=("Arial Black", 28), bg=BG_COLOR, fg="white")
        self.lbl_target.pack()

        # --- SCROLLING TIMELINE CANVAS ---
        canvas_container = tk.Frame(self, bg=BG_COLOR, padx=15)
        canvas_container.pack(fill=tk.X)
        
        self.canvas = tk.Canvas(canvas_container, height=140, bg=self.canvas_bg, highlightthickness=2, highlightbackground="#333")
        self.canvas.pack(fill=tk.X, pady=5)

        # --- Event Log ---
        self.log = tk.Text(self, height=10, state=tk.DISABLED, bg=PANEL_COLOR, fg=TEXT_COLOR, font=("Consolas", 11), bd=0, padx=10, pady=10)
        self.log.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

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
        if self.engine.current_combo:
            target = self.engine.current_combo["sequence"][self.engine.combo_step]
            self.lbl_target.config(text=f"{target['expected']} ({target['move']})", fg="white")

    # --- TRAINING ENVIRONMENT STATE MACHINE ---
    def trigger_reset(self):
        self.state = "COUNTDOWN"
        self.state_timer = time.time()
        self.engine.combo_step = 0
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
            self.canvas_bg = "#002211" # Flash green
        else:
            self.lbl_status.config(text="DROPPED", fg="#ff2a00")
            self.lbl_target.config(text=message, fg="#ff2a00")
            self.canvas_bg = "#330000" # Flash red

    # --- INPUT HANDLING ---
    def on_key_press(self, event):
        key = event.keysym.lower()
        if key not in self.keys_held:
            self.keys_held.add(key)
            mapped_action = self.engine.key_map.get(key)
            
            # Global Environment Controls
            if mapped_action == 'RESET':
                self.trigger_reset()
                return

            # Attack Inputs (Only process if actively practicing)
            if mapped_action in ['P', 'K', 'S', 'H', 'D']:
                self.active_buttons[mapped_action] = self.current_frame
                
                if self.state == "PRACTICING":
                    success, message = self.engine.check_input(mapped_action, self.current_frame)
                    
                    if success:
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
            mapped_action = self.engine.key_map.get(key)
            
            if mapped_action in self.active_buttons:
                start_frame = self.active_buttons.pop(mapped_action)
                self.past_buttons.append({
                    "btn": mapped_action, 
                    "start": start_frame, 
                    "end": self.current_frame
                })

    # --- SETTINGS MENU ---
    def open_settings(self):
        win = tk.Toplevel(self)
        win.title("Map Hardware Controls")
        win.geometry("320x500")
        win.configure(bg=BG_COLOR)
        win.transient(self)
        win.grab_set() 
        
        tk.Label(win, text="Click an action, press a physical key.", bg=BG_COLOR, fg="white", pady=10).pack()
        
        self.temp_binds = self.engine.key_map.copy()
        action_to_key = {v: k for k, v in self.temp_binds.items()}
        actions = ['up', 'down', 'left', 'right', 'P', 'K', 'S', 'H', 'D', 'RESET']
        
        frame = tk.Frame(win, bg=BG_COLOR)
        frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        self.binding_buttons = {}
        for idx, action in enumerate(actions):
            tk.Label(frame, text=f"{action.upper()}:", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")).grid(row=idx, column=0, pady=6, sticky=tk.E)
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
        self.engine.save_config(self.temp_binds)
        self.keys_held.clear() 
        window.destroy()

    # --- RENDER LOOP ---
    def tick(self):
        now = time.perf_counter()
        elapsed = now - self.last_tick_time
        
        if elapsed >= self.frame_duration:
            self.current_frame += 1
            self.last_tick_time = now
            
            # Background logic
            held_mapped = [self.engine.key_map[k] for k in self.keys_held if k in self.engine.key_map]
            self.engine.update_buffer(held_mapped)
            
            # State Machine Logic
            self.process_state_machine()
            
            # Rendering
            self.render_timeline()
            
        self.after(1, self.tick)

    def process_state_machine(self):
        now = time.time()
        elapsed = now - self.state_timer
        
        if self.state == "COUNTDOWN":
            if elapsed < 0.6:
                self.overlay_text = "3"
            elif elapsed < 1.2:
                self.overlay_text = "2"
            elif elapsed < 1.8:
                self.overlay_text = "1"
            elif elapsed < 2.5:
                self.overlay_text = "ROCK!"
                self.lbl_status.config(text="RECORDING", fg=ACCENT_COLOR)
            else:
                self.state = "PRACTICING"
                self.overlay_text = ""
                # Re-sync frame counter so strict timing starts from exactly "ROCK!"
                self.engine.last_input_frame = self.current_frame
                
        elif self.state == "RESULT":
            # Fade background back to normal over 1 second
            if elapsed > 1.0:
                self.canvas_bg = "#050508"
                self.state = "IDLE"
                self.lbl_status.config(text="PRESS RESET KEY", fg="#555")

    def render_timeline(self):
        self.canvas.delete("all")
        self.canvas.config(bg=self.canvas_bg)
        
        # Grid
        for i in range(0, 100):
            frame_offset = self.current_frame % 10
            x = PLAYHEAD_X - (i * 10 * PIXELS_PER_FRAME) + (frame_offset * PIXELS_PER_FRAME)
            if x > 0:
                self.canvas.create_line(x, 0, x, 140, fill="#1a1a24")

        # Past Holds
        cleanup_threshold = self.current_frame - int(PLAYHEAD_X / PIXELS_PER_FRAME) - 20
        self.past_buttons = [b for b in self.past_buttons if b["end"] > cleanup_threshold]
        for btn_data in self.past_buttons:
            self.draw_button_block(btn_data["btn"], btn_data["start"], btn_data["end"])

        # Active Holds
        for btn, start_frame in self.active_buttons.items():
            self.draw_button_block(btn, start_frame, self.current_frame)

        # Directional Buffer
        buf_len = len(self.engine.frame_buffer)
        for i, dir_str in enumerate(self.engine.frame_buffer):
            frames_ago = (buf_len - 1) - i 
            x = PLAYHEAD_X - (frames_ago * PIXELS_PER_FRAME)
            arrow = ARROW_MAP.get(dir_str, "")
            color = "#fff" if dir_str != "5" else "#333" 
            if arrow:
                self.canvas.create_text(x, TRACK_DIR_Y, text=arrow, fill=color, font=("Arial", 14))

        # Playhead
        self.canvas.create_line(PLAYHEAD_X, 0, PLAYHEAD_X, 140, fill="#00ffcc", width=2)
        
        # State Overlays
        if getattr(self, "overlay_text", "") and self.state == "COUNTDOWN":
            # Bounce scale effect based on sin wave
            scale_mod = math.sin((time.time() * 10) % math.pi) * 10
            font_size = int(60 + scale_mod)
            color = ACCENT_COLOR if self.overlay_text == "ROCK!" else "#fff"
            self.canvas.create_text(PLAYHEAD_X / 2, 70, text=self.overlay_text, font=("Impact", font_size, "italic"), fill=color)

    def draw_button_block(self, btn, start_frame, end_frame):
        start_x = PLAYHEAD_X - ((self.current_frame - start_frame) * PIXELS_PER_FRAME)
        end_x = PLAYHEAD_X - ((self.current_frame - end_frame) * PIXELS_PER_FRAME)
        if end_x - start_x < PIXELS_PER_FRAME:
            end_x = start_x + PIXELS_PER_FRAME
            
        color = BTN_COLORS.get(btn, "#fff")
        self.canvas.create_rectangle(start_x, TRACK_BUTTON_Y - 18, end_x, TRACK_BUTTON_Y + 18, fill=color, outline="#000", width=2)
        self.canvas.create_text(start_x + 8, TRACK_BUTTON_Y, text=btn, fill="#000", font=("Arial", 12, "bold"), anchor=tk.W)

if __name__ == "__main__":
    app = TrainerApp()
    app.mainloop()