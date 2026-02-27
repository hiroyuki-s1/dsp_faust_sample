"""Daisy Seed Simulator — Main GUI."""
import tkinter as tk
import json
import os
import sys

from sim.faust_engine import FaustEngine
from sim.audio_io import AudioIO, SAMPLE_RATE
from sim.oled_renderer import OledRenderer
from sim.widgets.oled_widget import OledWidget
from sim.widgets.knob_widget import KnobWidget
from sim.widgets.switch_widget import ToggleSwitch, MomentaryButton

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _match_param_path(json_path, faust_paths):
    """Match a JSON config path to an actual Faust param path.

    JSON paths may use old names (e.g. /delay_reverb/...) while Faust
    generates paths based on the current DSP file (e.g. /effector_board/...).
    We match by suffix: Delay/Time, Hall_Reverb/Room, etc.
    """
    # Normalize: replace spaces with underscores for comparison
    suffix = "/".join(json_path.strip("/").split("/")[1:])  # e.g. "Delay/Time"
    suffix_norm = suffix.replace(" ", "_")

    for fp in faust_paths:
        fp_suffix = "/".join(fp.strip("/").split("/")[1:])
        fp_norm = fp_suffix.replace(" ", "_")
        if fp_norm == suffix_norm:
            return fp

    # Fallback: try matching just the last component
    last = json_path.split("/")[-1].replace(" ", "_")
    for fp in faust_paths:
        fp_last = fp.split("/")[-1].replace(" ", "_")
        if fp_last == last:
            return fp

    return None


class DaisySimulator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Daisy Seed Simulator")
        self.root.configure(bg="#111111")
        self.root.resizable(False, False)

        # Load param config
        cfg_path = os.path.join(BASE_DIR, "params", "default.json")
        with open(cfg_path) as f:
            self.config = json.load(f)

        # Init Faust engine
        self.engine = FaustEngine()
        self.engine.init(SAMPLE_RATE)

        # Map JSON params to actual Faust paths
        self.param_list = []  # list of {json_key, path, label, ...}
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

        # OLED renderer
        self.oled_renderer = OledRenderer(self.engine, self.param_list)

        # Audio
        wav = os.path.join(BASE_DIR, "gen", "guitar_clean.wav")
        self.audio = AudioIO(self.engine, wav if os.path.exists(wav) else None)

        self._build_gui()
        self._update_oled()

    def _build_gui(self):
        # ── OLED ──
        oled_frame = tk.Frame(self.root, bg="#111111", padx=10, pady=8)
        oled_frame.pack()
        self.oled = OledWidget(oled_frame)
        self.oled.pack()

        # ── Knobs ──
        knob_frame = tk.Frame(self.root, bg="#1a1a1a", padx=4, pady=4)
        knob_frame.pack(fill=tk.X)

        knob_colors = ["#e8a735", "#e8a735", "#e8a735",
                        "#35a8e8", "#35a8e8", "#35a8e8",
                        "#b065e8"]

        self.knobs = {}
        for i, p in enumerate(self.param_list):
            color = knob_colors[i] if i < len(knob_colors) else "#c8a96e"

            def make_cb(path):
                return lambda val: self.engine.set_param(path, val)

            knob = KnobWidget(
                knob_frame,
                label=p["label"],
                min_val=p["min"],
                max_val=p["max"],
                default=p["default"],
                unit=p.get("unit", ""),
                color=color,
                on_change=make_cb(p["path"]),
            )
            knob.grid(row=0, column=i, padx=3, pady=2)
            self.knobs[p["json_key"]] = knob

        # ── Controls ──
        ctrl_frame = tk.Frame(self.root, bg="#111111", padx=10, pady=8)
        ctrl_frame.pack(fill=tk.X)

        self.bypass_sw = ToggleSwitch(
            ctrl_frame, label="BYPASS", initial=False,
            on_change=self._on_bypass)
        self.bypass_sw.pack(side=tk.LEFT, padx=8)

        self.page_btn = MomentaryButton(
            ctrl_frame, label="PAGE",
            on_press=self._on_page)
        self.page_btn.pack(side=tk.LEFT, padx=8)

        # Play / Stop
        btn_frame = tk.Frame(ctrl_frame, bg="#111111")
        btn_frame.pack(side=tk.RIGHT, padx=8)

        self.play_btn = tk.Button(
            btn_frame, text="PLAY", bg="#238636", fg="white",
            font=("Helvetica", 9, "bold"), width=6,
            command=self._play)
        self.play_btn.pack(side=tk.LEFT, padx=4)

        self.stop_btn = tk.Button(
            btn_frame, text="STOP", bg="#da3633", fg="white",
            font=("Helvetica", 9, "bold"), width=6,
            command=self._stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=4)

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
