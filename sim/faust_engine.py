"""Thin ctypes wrapper around gen/sim_engine.so"""
import ctypes
import os

OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_BUF_SIZE = OLED_WIDTH * OLED_HEIGHT // 8  # 1024


class FaustEngine:
    def __init__(self, so_path=None):
        if so_path is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            so_path = os.path.join(base, "gen", "sim_engine.so")
        self._lib = ctypes.CDLL(so_path)
        self._setup_signatures()
        self._handle = self._lib.faust_create()
        self.param_paths = []

    def _setup_signatures(self):
        L = self._lib
        L.faust_create.restype = ctypes.c_void_p
        L.faust_destroy.argtypes = [ctypes.c_void_p]
        L.faust_init.argtypes = [ctypes.c_void_p, ctypes.c_int]
        L.faust_get_num_inputs.argtypes = [ctypes.c_void_p]
        L.faust_get_num_inputs.restype = ctypes.c_int
        L.faust_get_num_outputs.argtypes = [ctypes.c_void_p]
        L.faust_get_num_outputs.restype = ctypes.c_int
        L.faust_get_params_count.argtypes = [ctypes.c_void_p]
        L.faust_get_params_count.restype = ctypes.c_int
        L.faust_get_param_address.argtypes = [ctypes.c_void_p, ctypes.c_int]
        L.faust_get_param_address.restype = ctypes.c_char_p
        L.faust_set_param.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                      ctypes.c_float]
        L.faust_get_param.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        L.faust_get_param.restype = ctypes.c_float
        L.faust_compute.argtypes = [
            ctypes.c_void_p, ctypes.c_int,
            ctypes.POINTER(ctypes.POINTER(ctypes.c_float)),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_float)),
        ]
        # OLED
        L.faust_oled_get_framebuf.argtypes = [ctypes.c_void_p]
        L.faust_oled_get_framebuf.restype = ctypes.POINTER(ctypes.c_ubyte)
        L.faust_oled_clear.argtypes = [ctypes.c_void_p]
        L.faust_oled_set_pixel.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        L.faust_oled_draw_text.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
            ctypes.c_char_p, ctypes.c_int]
        L.faust_oled_update.argtypes = [ctypes.c_void_p]

    def init(self, sample_rate=48000):
        self._lib.faust_init(self._handle, sample_rate)
        n = self._lib.faust_get_params_count(self._handle)
        self.param_paths = []
        for i in range(n):
            raw = self._lib.faust_get_param_address(self._handle, i)
            self.param_paths.append(raw.decode("utf-8"))

    @property
    def num_inputs(self):
        return self._lib.faust_get_num_inputs(self._handle)

    @property
    def num_outputs(self):
        return self._lib.faust_get_num_outputs(self._handle)

    def set_param(self, path, value):
        self._lib.faust_set_param(self._handle, path.encode(), float(value))

    def get_param(self, path):
        return self._lib.faust_get_param(self._handle, path.encode())

    def compute(self, in_buf, out_l, out_r):
        """Process one block. Arguments are ctypes float arrays."""
        count = len(in_buf)
        inp = ctypes.cast(in_buf, ctypes.POINTER(ctypes.c_float))
        ol = ctypes.cast(out_l, ctypes.POINTER(ctypes.c_float))
        orr = ctypes.cast(out_r, ctypes.POINTER(ctypes.c_float))
        inputs = (ctypes.POINTER(ctypes.c_float) * 1)(inp)
        outputs = (ctypes.POINTER(ctypes.c_float) * 2)(ol, orr)
        self._lib.faust_compute(self._handle, count, inputs, outputs)

    # ── OLED ──────────────────────────────────────────────────
    def oled_clear(self):
        self._lib.faust_oled_clear(self._handle)

    def oled_set_pixel(self, x, y, on=1):
        self._lib.faust_oled_set_pixel(self._handle, x, y, on)

    def oled_draw_text(self, x, y, text, font_size=0):
        self._lib.faust_oled_draw_text(
            self._handle, x, y, text.encode(), font_size)

    def oled_get_framebuf(self):
        ptr = self._lib.faust_oled_get_framebuf(self._handle)
        return bytes(ptr[:OLED_BUF_SIZE])

    def destroy(self):
        if self._handle:
            self._lib.faust_destroy(self._handle)
            self._handle = None

    def __del__(self):
        self.destroy()
