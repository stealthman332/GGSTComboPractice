import tkinter as tk
from tkinter import ttk
import time
from input_engine import InputEngine

class TrainerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GGST Combo Trainer V1.2")
        self.geometry("700x550")
        
        self.engine = InputEngine()
        
        self.fps = 60
        self.frame_duration = 1.0 / self.fps
        self.current_frame = 0
        self.last_tick_time = time.perf_counter()
        
        self.keys_held = set()
        
        self.create_widgets()
        self.populate_ui()
        
        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<KeyRelease>", self.on_key_release)
        
        self.tick()

    def create_widgets(self):
        menu_frame = ttk.Frame(self, padding=10)
        menu_frame.pack(fill=tk.X)

        self.char_var = tk.StringVar()
        self.char_cb = ttk.Combobox(menu_frame, textvariable=self.char_var, state="readonly", width=15)
        self.char_cb.pack(side=tk.LEFT, padx=5)
        self.char_cb.bind("<<ComboboxSelected>>", self.on_char_select)

        self.combo_var = tk.StringVar()
        self.combo_cb = ttk.Combobox(menu_frame, textvariable=self.combo_var, state="readonly", width=30)
        self.combo_cb.pack(side=tk.LEFT, padx=5)
        self.combo_cb.bind("<<ComboboxSelected>>", self.on_combo_select)

        self.btn_settings = ttk.Button(menu_frame, text="⚙️ Keybinds", command=self.open_settings)
        self.btn_settings.pack(side=tk.RIGHT, padx=5)

        self.lbl_target = ttk.Label(self, text="Load a combo...", font=("Arial", 24, "bold"))
        self.lbl_target.pack(pady=20)

        self.lbl_buffer = ttk.Label(self, text="Buffer: ", font=("Consolas", 12), foreground="gray")
        self.lbl_buffer.pack()

        self.log = tk.Text(self, height=12, state=tk.DISABLED, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
        self.log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def log_message(self, msg):
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
            self.log_message(f"Loaded: {self.combo_var.get()}")
            self.update_target_display()

    def update_target_display(self):
        if self.engine.current_combo:
            target = self.engine.current_combo["sequence"][self.engine.combo_step]
            self.lbl_target.config(text=f"Target: {target['expected']} ({target['move']})")

    # --- KEYBINDING MENU ---
    def open_settings(self):
        win = tk.Toplevel(self)
        win.title("Custom Keybindings")
        win.geometry("300x450")
        win.transient(self)
        win.grab_set() 
        
        ttk.Label(win, text="Click a button, then press a key to bind.", padding=10).pack()
        
        self.temp_binds = self.engine.key_map.copy()
        action_to_key = {v: k for k, v in self.temp_binds.items()}
        actions = ['up', 'down', 'left', 'right', 'P', 'K', 'S', 'H', 'D']
        
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        self.binding_buttons = {}
        for idx, action in enumerate(actions):
            ttk.Label(frame, text=f"{action.upper()}:").grid(row=idx, column=0, pady=5, sticky=tk.E)
            current_key = action_to_key.get(action, "UNBOUND")
            
            btn = ttk.Button(frame, text=current_key)
            btn.config(command=lambda a=action, b=btn: self.listen_for_bind(a, b, win))
            btn.grid(row=idx, column=1, padx=10, pady=5)
            self.binding_buttons[action] = btn

        save_btn = ttk.Button(win, text="Save & Close", command=lambda: self.save_settings(win))
        save_btn.pack(pady=10)

    def listen_for_bind(self, action, btn, window):
        btn.config(text="Press any key...")
        bind_id = window.bind("<KeyPress>", lambda e: self.register_bind(e, action, btn, window))
        window.bind_id = bind_id

    def register_bind(self, event, action, btn, window):
        new_key = event.keysym.lower()
        
        # Remove old mappings for this action
        keys_to_remove = [k for k, v in self.temp_binds.items() if v == action]
        for k in keys_to_remove: del self.temp_binds[k]
            
        # Unbind if key was already in use
        if new_key in self.temp_binds:
            old_action = self.temp_binds[new_key]
            if old_action in self.binding_buttons:
                self.binding_buttons[old_action].config(text="UNBOUND")
                
        self.temp_binds[new_key] = action
        btn.config(text=new_key)
        window.unbind("<KeyPress>", window.bind_id)

    def save_settings(self, window):
        self.engine.save_config(self.temp_binds)
        self.keys_held.clear() # Reset physical keys to prevent getting stuck
        window.destroy()

    # --- INPUT LOOP ---
    def on_key_press(self, event):
        key = event.keysym.lower()
        if key not in self.keys_held:
            self.keys_held.add(key)
            mapped_action = self.engine.key_map.get(key)
            
            if mapped_action in ['P', 'K', 'S', 'H', 'D']:
                success, message = self.engine.check_input(mapped_action, self.current_frame)
                
                if success:
                    self.log_message(f"SUCCESS -> {message}")
                    if self.engine.combo_step == 0:
                        self.log_message("--- COMBO COMPLETE! ---")
                else:
                    self.log_message(f"DROP    -> {message}")
                
                self.update_target_display()

    def on_key_release(self, event):
        key = event.keysym.lower()
        if key in self.keys_held:
            self.keys_held.remove(key)

    def tick(self):
        now = time.perf_counter()
        elapsed = now - self.last_tick_time
        
        if elapsed >= self.frame_duration:
            self.current_frame += 1
            self.last_tick_time = now
            
            held_mapped = [self.engine.key_map[k] for k in self.keys_held if k in self.engine.key_map]
            self.engine.update_buffer(held_mapped)
            
            buffer_str = "".join(self.engine.frame_buffer[-20:])
            self.lbl_buffer.config(text=f"Raw Buffer: {buffer_str}")
            
        self.after(1, self.tick)

if __name__ == "__main__":
    app = TrainerApp()
    app.mainloop()