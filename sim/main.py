"""Daisy Seed Simulator — Pedalboard-style GUI."""
import tkinter as tk
import json
import os

from sim.faust_engine import FaustEngine
from sim.audio_io import AudioIO, SAMPLE_RATE
from sim.oled_renderer import OledRenderer
from sim.widgets.oled_widget import OledWidget
from sim.widgets.knob_widget import KnobWidget
from sim.widgets.switch_widget import ToggleSwitch, MomentaryButton

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Color Palette ──────────────────────────────────────────
BOARD_BG = "#1c1410"       # dark wood board
HEADER_BG = "#0e0e14"      # dark header bar
HEADER_ACCENT = "#c8a96e"  # gold accent

DELAY_BG = "#2a1a00"       # warm brown pedal
DELAY_ACCENT = "#e8a735"   # gold knobs/text
REVERB_BG = "#0a1a2e"      # cool blue pedal
REVERB_ACCENT = "#35a8e8"  # blue knobs/text
DISPLAY_BG = "#141414"     # display panel


def _match_param_path(json_path, faust_paths):
    """Match a JSON config path to an actual Faust param path."""
    suffix = "/".join(json_path.strip("/").split("/")[1:])
    suffix_norm = suffix.replace(" ", "_")

    for fp in faust_paths:
        fp_suffix = "/".join(fp.strip("/").split("/")[1:])
        fp_norm = fp_suffix.replace(" ", "_")
        if fp_norm == suffix_norm:
            return fp

    last = json_path.split("/")[-1].replace(" ", "_")
    for fp in faust_paths:
        fp_last = fp.split("/")[-1].replace(" ", "_")
        if fp_last == last:
            return fp

    return None


class DaisySimulator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Daisy Hakoniwa")
        self.root.configure(bg=BOARD_BG)
        self.root.resizable(False, False)

        # Load param config
        cfg_path = os.path.join(BASE_DIR, "params", "default.json")
        with open(cfg_path) as f:
            self.config = json.load(f)

        # Init Faust engine
        self.engine = FaustEngine()
        self.engine.init(SAMPLE_RATE)

        # Map JSON params to actual Faust paths
        self.param_list = []
        for key, p in self.config["parameters"].items():
            actual_path = _match_param_path(
                p["path"], self.engine.param_paths)
            if actual_path:
                entry = dict(p)
                entry["path"] = actual_path
                entry["json_key"] = key
                self.param_list.append(entry)

        # Set defaults
        for p in self.param_list:
            self.engine.set_param(p["path"], p["default"])

        # Split params into delay / reverb groups
        self.delay_params = [p for p in self.param_list if "Delay" in p["path"]]
        self.reverb_params = [p for p in self.param_list if "Delay" not in p["path"]]

        # OLED renderer
        self.oled_renderer = OledRenderer(self.engine, self.param_list)

        # Audio
        wav = os.path.join(BASE_DIR, "gen", "guitar_clean.wav")
        self.audio = AudioIO(self.engine, wav if os.path.exists(wav) else None)

        self.knobs = {}
        self._build_gui()
        self._update_oled()

    # ── GUI Construction ──────────────────────────────────────

    def _build_gui(self):
        self._build_header()
        self._build_board()

    def _build_header(self):
        """Top bar: title + transport controls."""
        header = tk.Frame(self.root, bg=HEADER_BG, padx=12, pady=6)
        header.pack(fill=tk.X)

        # Title
        tk.Label(
            header, text="DAISY HAKONIWA",
            bg=HEADER_BG, fg=HEADER_ACCENT,
            font=("Helvetica", 11, "bold"),
        ).pack(side=tk.LEFT)

        # Separator dash
        tk.Label(
            header, text="  Effector Board Simulator",
            bg=HEADER_BG, fg="#666",
            font=("Helvetica", 8),
        ).pack(side=tk.LEFT)

        # Transport buttons
        btn_frame = tk.Frame(header, bg=HEADER_BG)
        btn_frame.pack(side=tk.RIGHT)

        self.stop_btn = tk.Button(
            btn_frame, text="STOP", bg="#da3633", fg="white",
            font=("Helvetica", 8, "bold"), width=5, relief=tk.FLAT,
            command=self._stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.RIGHT, padx=2)

        self.play_btn = tk.Button(
            btn_frame, text="PLAY", bg="#238636", fg="white",
            font=("Helvetica", 8, "bold"), width=5, relief=tk.FLAT,
            command=self._play)
        self.play_btn.pack(side=tk.RIGHT, padx=2)

    def _build_board(self):
        """Main board area with pedals and display."""
        # Board surface
        board = tk.Frame(self.root, bg=BOARD_BG, padx=16, pady=12)
        board.pack(fill=tk.BOTH, expand=True)

        # ── Top decorative line (cable rail) ──
        rail = tk.Canvas(board, height=4, bg=BOARD_BG, highlightthickness=0)
        rail.pack(fill=tk.X, pady=(0, 8))
        rail.bind("<Configure>", lambda e: rail.create_line(
            0, 2, e.width, 2, fill="#3a2a18", width=2, dash=(8, 4)))

        # ── Pedals row ──
        pedals_frame = tk.Frame(board, bg=BOARD_BG)
        pedals_frame.pack()

        # DELAY pedal
        self._build_pedal(
            pedals_frame, "DELAY", self.delay_params,
            DELAY_BG, DELAY_ACCENT, side=tk.LEFT)

        # Cable between pedals
        cable = tk.Canvas(pedals_frame, width=28, height=300,
                          bg=BOARD_BG, highlightthickness=0)
        cable.pack(side=tk.LEFT, padx=0)
        cable.create_line(14, 130, 14, 170, fill="#555", width=3)
        cable.create_oval(10, 122, 18, 130, fill="#444", outline="#666")
        cable.create_oval(10, 170, 18, 178, fill="#444", outline="#666")

        # REVERB pedal
        self._build_pedal(
            pedals_frame, "REVERB", self.reverb_params,
            REVERB_BG, REVERB_ACCENT, side=tk.LEFT)

        # Cable to display
        cable2 = tk.Canvas(pedals_frame, width=28, height=300,
                           bg=BOARD_BG, highlightthickness=0)
        cable2.pack(side=tk.LEFT, padx=0)
        cable2.create_line(14, 130, 14, 170, fill="#555", width=3)
        cable2.create_oval(10, 122, 18, 130, fill="#444", outline="#666")
        cable2.create_oval(10, 170, 18, 178, fill="#444", outline="#666")

        # Display panel
        self._build_display_panel(pedals_frame)

        # ── Bottom decorative line ──
        rail2 = tk.Canvas(board, height=4, bg=BOARD_BG, highlightthickness=0)
        rail2.pack(fill=tk.X, pady=(8, 0))
        rail2.bind("<Configure>", lambda e: rail2.create_line(
            0, 2, e.width, 2, fill="#3a2a18", width=2, dash=(8, 4)))

    def _build_pedal(self, parent, name, params, bg_color, accent, side):
        """Build a single pedal enclosure with knobs and footswitch."""
        # Outer frame (pedal body)
        pedal = tk.Frame(parent, bg=bg_color, padx=2, pady=2,
                         highlightbackground="#555", highlightthickness=2)
        pedal.pack(side=side, padx=6, pady=4)

        # Inner frame
        inner = tk.Frame(pedal, bg=bg_color, padx=8, pady=6)
        inner.pack()

        # ── Screw decorations (top) ──
        screw_top = tk.Frame(inner, bg=bg_color)
        screw_top.pack(fill=tk.X)
        for s in (tk.LEFT, tk.RIGHT):
            c = tk.Canvas(screw_top, width=12, height=12,
                          bg=bg_color, highlightthickness=0)
            c.pack(side=s)
            c.create_oval(2, 2, 10, 10, fill="#888", outline="#555")
            c.create_line(3, 6, 9, 6, fill="#444")
            c.create_line(6, 3, 6, 9, fill="#444")

        # ── Pedal name ──
        tk.Label(
            inner, text=name, bg=bg_color, fg=accent,
            font=("Helvetica", 10, "bold"),
        ).pack(pady=(2, 6))

        # ── Knobs ──
        knob_frame = tk.Frame(inner, bg=bg_color)
        knob_frame.pack()

        for i, p in enumerate(params):
            def make_cb(path):
                return lambda val: self.engine.set_param(path, val)

            knob = KnobWidget(
                knob_frame,
                label=p["label"].split()[-1],
                min_val=p["min"],
                max_val=p["max"],
                default=p["default"],
                unit=p.get("unit", ""),
                color=accent,
                bg_color=bg_color,
                on_change=make_cb(p["path"]),
            )
            # Layout: 2 columns for reverb (4 params), centered for delay (3)
            if len(params) <= 3:
                knob.grid(row=0, column=i, padx=3, pady=2)
            else:
                knob.grid(row=i // 2, column=i % 2, padx=3, pady=2)
            self.knobs[p["json_key"]] = knob

        # ── LED + Footswitch ──
        foot_frame = tk.Frame(inner, bg=bg_color)
        foot_frame.pack(pady=(6, 2))

        switch = ToggleSwitch(
            foot_frame, label="BYPASS", initial=False,
            on_change=self._on_bypass, bg_color=bg_color)
        switch.pack()

        # ── Screw decorations (bottom) ──
        screw_bot = tk.Frame(inner, bg=bg_color)
        screw_bot.pack(fill=tk.X)
        for s in (tk.LEFT, tk.RIGHT):
            c = tk.Canvas(screw_bot, width=12, height=12,
                          bg=bg_color, highlightthickness=0)
            c.pack(side=s)
            c.create_oval(2, 2, 10, 10, fill="#888", outline="#555")
            c.create_line(3, 6, 9, 6, fill="#444")
            c.create_line(6, 3, 6, 9, fill="#444")

    def _build_display_panel(self, parent):
        """Build the OLED display + PAGE button panel."""
        panel = tk.Frame(parent, bg=DISPLAY_BG, padx=2, pady=2,
                         highlightbackground="#444", highlightthickness=2)
        panel.pack(side=tk.LEFT, padx=6, pady=4)

        inner = tk.Frame(panel, bg=DISPLAY_BG, padx=10, pady=8)
        inner.pack()

        # Panel title
        tk.Label(
            inner, text="DISPLAY", bg=DISPLAY_BG, fg="#666",
            font=("Helvetica", 8, "bold"),
        ).pack(pady=(0, 4))

        # OLED
        self.oled = OledWidget(inner)
        self.oled.pack(pady=(0, 8))

        # PAGE button
        self.page_btn = MomentaryButton(
            inner, label="PAGE",
            on_press=self._on_page, bg_color=DISPLAY_BG)
        self.page_btn.pack()

    # ── Callbacks ─────────────────────────────────────────────

    def _on_bypass(self, state):
        self.audio.bypass = state

    def _on_page(self):
        self.oled_renderer.next_page()

    def _update_oled(self):
        self.oled_renderer.render()
        buf = self.engine.oled_get_framebuf()
        self.oled.update_from_framebuf(buf)
        self.root.after(66, self._update_oled)  # ~15 FPS

    def _play(self):
        ok = self.audio.start()
        if ok:
            self.play_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)

    def _stop(self):
        self.audio.stop()
        self.play_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self.audio.stop()
            self.engine.destroy()


def main():
    app = DaisySimulator()
    app.run()


if __name__ == "__main__":
    main()
