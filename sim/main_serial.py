"""Hybrid mode GUI — real Daisy Seed DSP + simulated knobs/OLED/switches via USB serial."""

import argparse
import json
import os
import tkinter as tk

from sim.oled_renderer import OledRenderer
from sim.widgets.oled_widget import OledWidget
from sim.widgets.knob_widget import KnobWidget
from sim.widgets.switch_widget import ToggleSwitch, MomentaryButton
from sim.serial_bridge import SerialBridge
from sim._oled_font import FONT5X7

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_BUF_SIZE = OLED_WIDTH * OLED_HEIGHT // 8


class LocalOledEngine:
    """Lightweight engine substitute for OLED rendering in hybrid mode.

    Provides the same API surface as FaustEngine that OledRenderer uses:
    get_param, oled_clear, oled_set_pixel, oled_draw_text, oled_get_framebuf.
    """

    def __init__(self):
        self._params = {}
        self._oled_buf = bytearray(OLED_BUF_SIZE)

    def set_param(self, path, value):
        self._params[path] = float(value)

    def get_param(self, path):
        return self._params.get(path, 0.0)

    def oled_clear(self):
        for i in range(OLED_BUF_SIZE):
            self._oled_buf[i] = 0

    def oled_set_pixel(self, x, y, on=1):
        if x < 0 or x >= OLED_WIDTH or y < 0 or y >= OLED_HEIGHT:
            return
        page = y // 8
        bit = y % 8
        idx = page * OLED_WIDTH + x
        if on:
            self._oled_buf[idx] |= (1 << bit)
        else:
            self._oled_buf[idx] &= ~(1 << bit)

    def oled_draw_text(self, x, y, text, font_size=0):
        scale = 2 if font_size > 0 else 1
        cx = x
        for ch in text:
            code = ord(ch) - 0x20
            if code < 0 or code > 94:
                code = 0
            glyph = FONT5X7[code]
            for col in range(5):
                bits = glyph[col]
                for row in range(7):
                    if bits & (1 << row):
                        for sy in range(scale):
                            for sx in range(scale):
                                self.oled_set_pixel(
                                    cx + col * scale + sx,
                                    y + row * scale + sy, 1)
            cx += (5 + 1) * scale

    def oled_get_framebuf(self):
        return bytes(self._oled_buf)


class HybridSimulator:
    def __init__(self, serial_port):
        self.root = tk.Tk()
        self.root.title(f"Daisy Hybrid \u2014 {serial_port}")
        self.root.configure(bg="#111111")
        self.root.resizable(False, False)

        # Load param config
        cfg_path = os.path.join(BASE_DIR, "params", "default.json")
        with open(cfg_path) as f:
            self.config = json.load(f)

        # Local engine for OLED rendering (no Faust DSP)
        self.engine = LocalOledEngine()

        # Build param list
        self.param_list = []
        for key, p in self.config["parameters"].items():
            entry = dict(p)
            entry["json_key"] = key
            self.param_list.append(entry)

        # Set defaults
        for p in self.param_list:
            self.engine.set_param(p["path"], p["default"])

        # OLED renderer (reuses sim/oled_renderer.py unchanged)
        self.oled_renderer = OledRenderer(self.engine, self.param_list)

        # Serial bridge
        self.bridge = SerialBridge(serial_port)
        self.bridge.on_status = self._on_daisy_status

        self._build_gui()
        self._update_oled()
        self._check_connection()

        # Connect
        if self.bridge.open():
            self.bridge.start()
            self._set_status(True)
            # Send initial knob defaults
            for i, p in enumerate(self.param_list):
                rng = p["max"] - p["min"]
                norm = (p["default"] - p["min"]) / rng if rng > 0 else 0.0
                self.bridge.set_knob(i, norm)
        else:
            self._set_status(False)

    def _build_gui(self):
        # -- Status bar --
        status_frame = tk.Frame(self.root, bg="#111111", padx=10, pady=2)
        status_frame.pack(fill=tk.X)
        self.status_label = tk.Label(
            status_frame, text="Connecting...",
            fg="#888888", bg="#111111", font=("Helvetica", 8))
        self.status_label.pack(side=tk.RIGHT)
        mode_label = tk.Label(
            status_frame, text="HYBRID MODE",
            fg="#e8a735", bg="#111111", font=("Helvetica", 8, "bold"))
        mode_label.pack(side=tk.LEFT)

        # -- OLED --
        oled_frame = tk.Frame(self.root, bg="#111111", padx=10, pady=8)
        oled_frame.pack()
        self.oled = OledWidget(oled_frame)
        self.oled.pack()

        # -- Knobs --
        knob_frame = tk.Frame(self.root, bg="#1a1a1a", padx=4, pady=4)
        knob_frame.pack(fill=tk.X)

        knob_colors = [
            "#e8a735", "#e8a735", "#e8a735",  # delay
            "#35a8e8", "#35a8e8", "#35a8e8",  # reverb
            "#b065e8",                          # shimmer
        ]

        self.knobs = {}
        for i, p in enumerate(self.param_list):
            color = knob_colors[i] if i < len(knob_colors) else "#c8a96e"

            def make_cb(idx, path, pmin, pmax):
                def cb(val):
                    rng = pmax - pmin
                    norm = (val - pmin) / rng if rng > 0 else 0.0
                    self.bridge.set_knob(idx, norm)
                    self.engine.set_param(path, val)
                return cb

            knob = KnobWidget(
                knob_frame,
                label=p["label"],
                min_val=p["min"],
                max_val=p["max"],
                default=p["default"],
                unit=p.get("unit", ""),
                color=color,
                on_change=make_cb(i, p["path"], p["min"], p["max"]),
            )
            knob.grid(row=0, column=i, padx=3, pady=2)
            self.knobs[p["json_key"]] = knob

        # -- Controls --
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

    def _on_bypass(self, state):
        self.bridge.set_switch(0, 1 if state else 0)

    def _on_page(self):
        self.oled_renderer.next_page()

    def _update_oled(self):
        self.oled_renderer.render()
        buf = self.engine.oled_get_framebuf()
        self.oled.update_from_framebuf(buf)
        self.root.after(66, self._update_oled)  # ~15 FPS

    def _check_connection(self):
        """Periodic check: mark disconnected if no heartbeat for 3 seconds."""
        import time
        if self.bridge.last_rx_time > 0:
            elapsed = time.monotonic() - self.bridge.last_rx_time
            if elapsed > 3.0:
                self._set_status(False)
        self.root.after(2000, self._check_connection)

    def _on_daisy_status(self, params, status):
        self.root.after(0, lambda: self._set_status(True))

    def _set_status(self, connected):
        if connected:
            self.status_label.config(text="Daisy: Connected", fg="#00ff44")
        else:
            self.status_label.config(text="Daisy: Disconnected", fg="#ff4444")

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self.bridge.stop()


def main():
    parser = argparse.ArgumentParser(description="Daisy Hybrid Simulator")
    parser.add_argument("--port", "-p", default="/dev/ttyACM0",
                        help="Serial port (default: /dev/ttyACM0)")
    args = parser.parse_args()

    app = HybridSimulator(args.port)
    app.run()


if __name__ == "__main__":
    main()
