"""Real-time audio I/O using pyaudio."""
import ctypes
import struct
import wave
import array
import threading

SAMPLE_RATE = 48000
BLOCK_SIZE = 256
CHANNELS_OUT = 2


class AudioIO:
    def __init__(self, engine, wav_path=None):
        self.engine = engine
        self.stream = None
        self._pa = None
        self._wav_samples = None
        self._wav_pos = 0
        self._lock = threading.Lock()
        self._bypass = False

        # Pre-allocate ctypes buffers
        self._in_buf = (ctypes.c_float * BLOCK_SIZE)()
        self._out_l = (ctypes.c_float * BLOCK_SIZE)()
        self._out_r = (ctypes.c_float * BLOCK_SIZE)()

        if wav_path:
            self._load_wav(wav_path)

    def _load_wav(self, path):
        with wave.open(path, "r") as w:
            nch = w.getnchannels()
            raw = w.readframes(w.getnframes())
        samples = array.array("h")
        samples.frombytes(raw)
        if nch == 2:
            mono = samples[::2]
        else:
            mono = samples
        self._wav_samples = [v / 32768.0 for v in mono]

    @property
    def bypass(self):
        return self._bypass

    @bypass.setter
    def bypass(self, val):
        self._bypass = val

    def _callback(self, in_data, frame_count, time_info, status):
        import pyaudio
        for i in range(frame_count):
            if self._wav_samples:
                idx = self._wav_pos % len(self._wav_samples)
                self._in_buf[i] = self._wav_samples[idx]
                self._wav_pos += 1
            else:
                self._in_buf[i] = 0.0

        if self._bypass:
            # Pass-through (mono to both channels)
            out = bytearray(frame_count * 2 * 4)
            for i in range(frame_count):
                struct.pack_into("ff", out, i * 8,
                                 self._in_buf[i], self._in_buf[i])
            return (bytes(out), pyaudio.paContinue)

        self.engine.compute(self._in_buf, self._out_l, self._out_r)

        out = bytearray(frame_count * 2 * 4)
        for i in range(frame_count):
            struct.pack_into("ff", out, i * 8,
                             self._out_l[i], self._out_r[i])
        return (bytes(out), pyaudio.paContinue)

    def start(self):
        try:
            import pyaudio
        except ImportError:
            print("[AudioIO] pyaudio not available — no audio output")
            return False

        try:
            self._pa = pyaudio.PyAudio()
            self.stream = self._pa.open(
                format=pyaudio.paFloat32,
                channels=CHANNELS_OUT,
                rate=SAMPLE_RATE,
                output=True,
                frames_per_buffer=BLOCK_SIZE,
                stream_callback=self._callback,
            )
            self.stream.start_stream()
            return True
        except Exception as e:
            print(f"[AudioIO] Failed to start audio: {e}")
            self._cleanup_pa()
            return False

    def stop(self):
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        self._cleanup_pa()

    def _cleanup_pa(self):
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None

    @property
    def is_playing(self):
        return self.stream is not None and self.stream.is_active()
