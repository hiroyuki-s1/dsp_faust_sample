"""Rotary knob widget — drag vertically to change value."""
import tkinter as tk
import math

KNOB_SIZE = 60
ARC_START = 225   # degrees (7 o'clock position, tkinter convention)
ARC_SWEEP = -270  # clockwise 270 degrees


class KnobWidget(tk.Canvas):
    def __init__(self, parent, label="Knob", min_val=0.0, max_val=1.0,
                 default=0.5, unit="", color="#c8a96e",
                 on_change=None, bg_color=None, **kwargs):
        bg = bg_color or "#1a1a1a"
        super().__init__(parent, width=KNOB_SIZE + 16,
                         height=KNOB_SIZE + 40,
                         bg=bg, highlightthickness=0, **kwargs)
        self.min_val = min_val
        self.max_val = max_val
        self.value = default
        self._default = default
        self.unit = unit
        self.color = color
        self.label = label
        self.on_change = on_change

        self._drag_y = None
        self._drag_val = None

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Double-Button-1>", self._on_reset)
        self.bind("<MouseWheel>", self._on_scroll)
        self.bind("<Button-4>", lambda e: self._scroll_delta(1))
        self.bind("<Button-5>", lambda e: self._scroll_delta(-1))

        self._draw()

    def _on_press(self, event):
        self._drag_y = event.y
        self._drag_val = self.value

    def _on_drag(self, event):
        if self._drag_y is None:
            return
        dy = self._drag_y - event.y
        rng = self.max_val - self.min_val
        new_val = self._drag_val + dy * rng / 150.0
        self.set_value(max(self.min_val, min(self.max_val, new_val)))

    def _on_release(self, event):
        self._drag_y = None

    def _on_reset(self, event):
        self.set_value(self._default)

    def _on_scroll(self, event):
        self._scroll_delta(1 if event.delta > 0 else -1)

    def _scroll_delta(self, direction):
        rng = self.max_val - self.min_val
        step = rng / 50.0
        self.set_value(max(self.min_val,
                           min(self.max_val, self.value + direction * step)))

    def set_value(self, val):
        self.value = val
        self._draw()
        if self.on_change:
            self.on_change(self.value)

    def _draw(self):
        self.delete("all")
        w = KNOB_SIZE + 16
        cx = w // 2
        cy = 8 + KNOB_SIZE // 2
        r = KNOB_SIZE // 2 - 2

        # Outer ring
        self.create_oval(cx - r, cy - r, cx + r, cy + r,
                         fill="#2a2a2a", outline="#444", width=1)

        # Background arc
        ri = r - 6
        self.create_arc(cx - ri, cy - ri, cx + ri, cy + ri,
                        start=ARC_START, extent=ARC_SWEEP,
                        style="arc", outline="#333", width=3)

        # Value arc
        frac = ((self.value - self.min_val) /
                (self.max_val - self.min_val))
        val_extent = ARC_SWEEP * frac
        self.create_arc(cx - ri, cy - ri, cx + ri, cy + ri,
                        start=ARC_START, extent=val_extent,
                        style="arc", outline=self.color, width=3)

        # Pointer line
        angle_deg = ARC_START + val_extent
        angle_rad = math.radians(angle_deg)
        px = cx + math.cos(angle_rad) * (ri - 4)
        py = cy - math.sin(angle_rad) * (ri - 4)
        self.create_line(cx, cy, px, py, fill="white", width=2)

        # Center dot
        self.create_oval(cx - 3, cy - 3, cx + 3, cy + 3,
                         fill="#555", outline="")

        # Label
        self.create_text(cx, cy + r + 8, text=self.label,
                         fill="#999", font=("Helvetica", 7))
        # Value
        if self.unit:
            vt = f"{self.value:.0f}{self.unit}"
        else:
            vt = f"{self.value:.2f}"
        self.create_text(cx, cy + r + 20, text=vt,
                         fill="#ccc", font=("Helvetica", 7))
