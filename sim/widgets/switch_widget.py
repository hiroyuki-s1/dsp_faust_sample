"""Toggle and momentary switch widgets."""
import tkinter as tk


class ToggleSwitch(tk.Canvas):
    """Stomp-style bypass switch. Click to toggle."""

    def __init__(self, parent, label="BYPASS", initial=True,
                 on_change=None, bg_color=None, **kwargs):
        bg = bg_color or "#1a1a1a"
        super().__init__(parent, width=56, height=76,
                         bg=bg, highlightthickness=0, **kwargs)
        self.state = initial
        self.label = label
        self.on_change = on_change
        self.bind("<Button-1>", self._toggle)
        self._draw()

    def _toggle(self, event=None):
        self.state = not self.state
        self._draw()
        if self.on_change:
            self.on_change(self.state)

    def _draw(self):
        self.delete("all")
        # LED
        led = "#00ff44" if self.state else "#330000"
        self.create_oval(20, 4, 36, 20, fill=led, outline="#555")
        # Button body
        fill = "#444" if self.state else "#222"
        self.create_oval(8, 24, 48, 64, fill=fill, outline="#666", width=2)
        txt = "ON" if self.state else "OFF"
        self.create_text(28, 44, text=txt,
                         fill="#aaa", font=("Helvetica", 8, "bold"))
        # Label
        self.create_text(28, 70, text=self.label,
                         fill="#888", font=("Helvetica", 7))


class MomentaryButton(tk.Canvas):
    """Press-and-release button (e.g., page navigation)."""

    def __init__(self, parent, label="PAGE", on_press=None,
                 bg_color=None, **kwargs):
        bg = bg_color or "#1a1a1a"
        super().__init__(parent, width=56, height=76,
                         bg=bg, highlightthickness=0, **kwargs)
        self.label = label
        self.on_press = on_press
        self.pressed = False
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self._draw()

    def _press(self, event):
        self.pressed = True
        self._draw()
        if self.on_press:
            self.on_press()

    def _release(self, event):
        self.pressed = False
        self._draw()

    def _draw(self):
        self.delete("all")
        fill = "#555" if self.pressed else "#333"
        self.create_rectangle(8, 24, 48, 56, fill=fill,
                              outline="#777", width=2)
        self.create_text(28, 40, text=self.label,
                         fill="#ddd", font=("Helvetica", 8, "bold"))
