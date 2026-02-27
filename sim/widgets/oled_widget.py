"""OLED display widget — 128x64 monochrome at 4x scale."""
import tkinter as tk

OLED_W, OLED_H = 128, 64
SCALE = 3
CANVAS_W = OLED_W * SCALE
CANVAS_H = OLED_H * SCALE
COLOR_ON = "#00FF88"
COLOR_OFF = "#080808"
COLOR_BG = "#000000"


class OledWidget(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, width=CANVAS_W, height=CANVAS_H,
                         bg=COLOR_BG, highlightthickness=2,
                         highlightbackground="#333333", **kwargs)
        self._img = tk.PhotoImage(width=CANVAS_W, height=CANVAS_H)
        self.create_image(0, 0, anchor=tk.NW, image=self._img)
        self._prev_buf = None

    def update_from_framebuf(self, buf):
        """Render SSD1306-format 1024-byte buffer (8 pages x 128 cols)."""
        if buf == self._prev_buf:
            return
        self._prev_buf = buf

        # Build row data for PhotoImage.put()
        # Each row is a string of space-separated colors
        rows = []
        for y in range(OLED_H):
            page = y // 8
            bit = y % 8
            colors = []
            for x in range(OLED_W):
                byte_val = buf[page * OLED_W + x]
                on = bool(byte_val & (1 << bit))
                c = COLOR_ON if on else COLOR_OFF
                # Repeat each pixel SCALE times horizontally
                colors.extend([c] * SCALE)
            row_str = " ".join(colors)
            # Repeat each row SCALE times vertically
            for _ in range(SCALE):
                rows.append("{" + row_str + "}")

        # Single put() call with all rows
        self._img.put(" ".join(rows))
