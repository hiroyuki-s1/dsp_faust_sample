"""Serial bridge for hybrid mode — sends knob/switch state to Daisy via USB CDC."""

import struct
import threading
import time
from typing import Optional, Callable, Tuple

# Frame formats (little-endian, matching ARM Cortex-M7 / x86)
PC_SYNC = b'\xAA\x55'
DAISY_SYNC = b'\x55\xAA'

# struct PcToDaisy: sync(2) + knobs(7*4=28) + switches(2) = 32 bytes
PC_TO_DAISY_FMT = '<2s7f2B'
PC_TO_DAISY_SIZE = struct.calcsize(PC_TO_DAISY_FMT)  # 32

# struct DaisyToPc: sync(2) + params(7*4=28) + status(1) = 31 bytes
DAISY_TO_PC_FMT = '<2s7fB'
DAISY_TO_PC_SIZE = struct.calcsize(DAISY_TO_PC_FMT)  # 31

SEND_HZ = 30
SEND_INTERVAL = 1.0 / SEND_HZ


class SerialBridge:
    """Bidirectional serial communication with Daisy Seed in hybrid mode."""

    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self._ser = None
        self._running = False
        self._tx_thread: Optional[threading.Thread] = None
        self._rx_thread: Optional[threading.Thread] = None

        self._knobs = [0.0] * 7
        self._switches = [0, 0]
        self._lock = threading.Lock()

        # Callback: on_status(params: tuple[float*7], status: int)
        self.on_status: Optional[Callable[[Tuple, int], None]] = None

        self.connected = False
        self.last_rx_time = 0.0

    def open(self) -> bool:
        """Open serial port. Returns True on success."""
        try:
            import serial
            self._ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=0.1,
                write_timeout=0.1,
            )
            self.connected = True
            return True
        except Exception as e:
            print(f"[SerialBridge] Failed to open {self.port}: {e}")
            return False

    def start(self):
        """Start tx/rx threads."""
        if not self._ser or not self._ser.is_open:
            return
        self._running = True
        self._tx_thread = threading.Thread(target=self._tx_loop, daemon=True)
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._tx_thread.start()
        self._rx_thread.start()

    def stop(self):
        """Stop threads and close port."""
        self._running = False
        if self._tx_thread:
            self._tx_thread.join(timeout=1.0)
        if self._rx_thread:
            self._rx_thread.join(timeout=1.0)
        if self._ser and self._ser.is_open:
            self._ser.close()
        self.connected = False

    def set_knob(self, index: int, value: float):
        """Set normalized knob value (0.0-1.0)."""
        if 0 <= index < 7:
            with self._lock:
                self._knobs[index] = max(0.0, min(1.0, value))

    def set_switch(self, index: int, state: int):
        """Set switch state (0 or 1)."""
        if 0 <= index < 2:
            with self._lock:
                self._switches[index] = int(bool(state))

    def _tx_loop(self):
        """Send knob/switch frames at SEND_HZ."""
        while self._running:
            t0 = time.monotonic()
            try:
                with self._lock:
                    knobs = list(self._knobs)
                    sw = list(self._switches)

                frame = struct.pack(PC_TO_DAISY_FMT, PC_SYNC, *knobs, *sw)
                self._ser.write(frame)
            except Exception as e:
                print(f"[SerialBridge TX] {e}")
                self.connected = False
                break

            elapsed = time.monotonic() - t0
            remaining = SEND_INTERVAL - elapsed
            if remaining > 0:
                time.sleep(remaining)

    def _rx_loop(self):
        """Read status frames from Daisy."""
        buf = bytearray()
        while self._running:
            try:
                data = self._ser.read(64)
                if not data:
                    continue
                buf.extend(data)

                while len(buf) >= DAISY_TO_PC_SIZE:
                    idx = buf.find(DAISY_SYNC)
                    if idx < 0:
                        buf.clear()
                        break
                    if idx > 0:
                        del buf[:idx]
                    if len(buf) < DAISY_TO_PC_SIZE:
                        break

                    frame = bytes(buf[:DAISY_TO_PC_SIZE])
                    del buf[:DAISY_TO_PC_SIZE]

                    parsed = struct.unpack(DAISY_TO_PC_FMT, frame)
                    params = parsed[1:8]
                    status = parsed[8]

                    self.last_rx_time = time.monotonic()
                    self.connected = True

                    if self.on_status:
                        self.on_status(params, status)

            except Exception as e:
                if self._running:
                    print(f"[SerialBridge RX] {e}")
                break
