"""Default OLED display — shows parameter values on 2 pages."""


class OledRenderer:
    def __init__(self, engine, param_config):
        """
        engine: FaustEngine instance
        param_config: list of dicts from params/default.json["parameters"]
                      each with keys: path, label, min, max, unit, default
        """
        self.engine = engine
        self.page = 0

        # Group parameters into pages by path prefix
        delay_params = []
        reverb_params = []
        for p in param_config:
            if "Delay" in p["path"]:
                delay_params.append(p)
            else:
                reverb_params.append(p)

        self.pages = []
        if delay_params:
            self.pages.append(("DELAY", delay_params))
        if reverb_params:
            self.pages.append(("REVERB", reverb_params))
        if not self.pages:
            self.pages.append(("(no params)", []))

    def next_page(self):
        if self.pages:
            self.page = (self.page + 1) % len(self.pages)

    def render(self):
        """Draw current page to OLED frame buffer."""
        e = self.engine
        e.oled_clear()

        if not self.pages:
            return

        title, params = self.pages[self.page]

        # Title (large font)
        e.oled_draw_text(2, 0, title, font_size=1)

        # Separator line at y=16
        for x in range(128):
            e.oled_set_pixel(x, 16, 1)

        # Parameters (small font, up to 4 per page)
        y = 20
        for p in params[:4]:
            val = e.get_param(p["path"])
            name = p["label"].split()[-1][:6].upper()
            if p.get("unit"):
                vt = f"{val:.0f}{p['unit']}"
            else:
                vt = f"{val:.2f}"
            line = f"{name}: {vt}"
            e.oled_draw_text(4, y, line, font_size=0)

            # Mini bar graph (x=80 to x=124)
            frac = 0.0
            rng = p["max"] - p["min"]
            if rng > 0:
                frac = (val - p["min"]) / rng
            frac = max(0.0, min(1.0, frac))
            bar_x0 = 80
            bar_x1 = bar_x0 + int(44 * frac)
            for bx in range(bar_x0, bar_x1):
                for by in range(y + 1, y + 6):
                    e.oled_set_pixel(bx, by, 1)
            # Bar outline
            for bx in range(bar_x0, bar_x0 + 44):
                e.oled_set_pixel(bx, y, 1)
                e.oled_set_pixel(bx, y + 7, 1)
            for by in range(y, y + 8):
                e.oled_set_pixel(bar_x0, by, 1)
                e.oled_set_pixel(bar_x0 + 44, by, 1)

            y += 11

        # Page indicator dots at bottom
        total = len(self.pages)
        start_x = 64 - (total * 4)
        for i in range(total):
            cx = start_x + i * 8
            if i == self.page:
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        if dx * dx + dy * dy <= 4:
                            e.oled_set_pixel(cx + dx, 60 + dy, 1)
            else:
                e.oled_set_pixel(cx, 60, 1)
