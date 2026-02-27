#!/usr/bin/env python3
"""
Guitar effect: Delay + Hall Reverb
Pure Python — no external dependencies required.

Usage:
  python3 scripts/apply_effect.py [input.wav] [output.wav]
"""

import wave
import struct
import array
import time
import sys
import os

# ──────────────────────────────────────────────────────────────
# WAV I/O
# ──────────────────────────────────────────────────────────────
def read_wav_mono(path):
    """Return (samples_float_list, sample_rate)."""
    with wave.open(path, 'r') as w:
        nch = w.getnchannels()
        sr  = w.getframerate()
        sw  = w.getsampwidth()
        nf  = w.getnframes()
        raw = w.readframes(nf)

    if sw == 2:
        buf = array.array('h')
        buf.frombytes(raw)
        if nch == 2:
            # take left channel
            mono = buf[::2]
        else:
            mono = buf
    elif sw == 3:
        # 24-bit — convert manually
        vals = []
        for i in range(0, len(raw), 3 * nch):
            b = raw[i:i+3]
            v = struct.unpack('<i', b + (b'\xff' if b[2] & 0x80 else b'\x00'))[0]
            vals.append(v >> 8)  # scale to 16-bit range
        mono = vals
    else:
        raise ValueError(f"Unsupported sample width: {sw} bytes")

    scale = 1.0 / 32768.0
    return [v * scale for v in mono], sr


def write_wav_stereo(path, left, right, sr):
    """Write stereo 16-bit WAV from two float lists."""
    n = len(left)
    out = array.array('h', [0] * (n * 2))
    for i in range(n):
        l = left[i]
        r = right[i]
        out[i*2]   = max(-32767, min(32767, int(l * 32767)))
        out[i*2+1] = max(-32767, min(32767, int(r * 32767)))
    with wave.open(path, 'w') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(out.tobytes())


# ──────────────────────────────────────────────────────────────
# DSP helpers — keep all in flat local-variable style for speed
# ──────────────────────────────────────────────────────────────
def make_comb(size):
    return [0.0] * size, 0, 0.0   # buf, pos, filterstore

def process_comb(x, buf, pos, size, feedback, damp):
    out = buf[pos]
    # lowpass-feedback
    fs  = out * (1.0 - damp)
    buf[pos] = x + fs * feedback
    return out, (pos + 1) % size, fs   # caller caches filterstore if needed

def make_allpass(size, feedback=0.5):
    return [0.0] * size, 0, feedback

def process_allpass(x, buf, pos, size, fb):
    bval = buf[pos]
    out  = -x + bval
    buf[pos] = x + bval * fb
    return out, (pos + 1) % size


# ──────────────────────────────────────────────────────────────
# Main processor
# ──────────────────────────────────────────────────────────────
def process(samples, sr,
            delay_time_ms  = 320,
            delay_feedback = 0.55,
            delay_mix      = 0.35,
            rev_room       = 0.75,
            rev_damp       = 0.40,
            rev_mix        = 0.38):

    n = len(samples)

    # ── Delay ──────────────────────────────────────
    delay_n    = int(delay_time_ms * sr / 1000.0)
    max_dl     = sr + 1                       # 1-second max
    delay_buf  = [0.0] * max_dl
    dpos       = 0

    # ── Freeverb-style Hall Reverb ─────────────────
    # 8 comb filters (original delays at 44100 Hz, scaled)
    sc = sr / 44100.0
    comb_delays = [int(d * sc) for d in [1557, 1617, 1491, 1422,
                                          1277, 1356, 1188, 1116]]
    SPREAD = 23
    fb_c   = 0.70 + rev_room * 0.28          # 0.70 – 0.98
    dmp    = rev_damp * 0.40

    # Left / right comb buffers
    cbufs_l  = [[0.0] * d for d in comb_delays]
    cbufs_r  = [[0.0] * (d + SPREAD) for d in comb_delays]
    cpos_l   = [0] * 8
    cpos_r   = [0] * 8
    cfs_l    = [0.0] * 8     # filterstore
    cfs_r    = [0.0] * 8
    csizes_l = comb_delays
    csizes_r = [d + SPREAD for d in comb_delays]

    # 4 all-pass filters (shared L+R)
    ap_delays = [int(d * sc) for d in [225, 556, 441, 341]]
    apbufs    = [[0.0] * d for d in ap_delays]
    apbufs2   = [[0.0] * d for d in ap_delays]  # right channel
    appos     = [0] * 4
    appos2    = [0] * 4
    ap_fb     = 0.5

    # output buffers
    out_l = [0.0] * n
    out_r = [0.0] * n

    inp_scale   = 0.015        # input gain into reverb
    d1m         = 1.0 - dmp   # precompute (1 - damp)

    print(f"  Processing {n} samples ({n/sr:.1f}s) …")
    t0 = time.time()
    report_interval = n // 20   # report every 5%

    for i in range(n):
        # ── progress ──────────────────────────────
        if i % report_interval == 0:
            pct = i * 100 // n
            print(f"    {pct:3d}%  ({time.time()-t0:.1f}s)", flush=True)

        x = samples[i]

        # ── Feedback delay ────────────────────────
        rp       = (dpos - delay_n) % max_dl
        delayed  = delay_buf[rp]
        delay_buf[dpos] = x + delayed * delay_feedback
        dpos     = (dpos + 1) % max_dl
        xd       = x * (1.0 - delay_mix) + delayed * delay_mix

        # ── Reverb: 8 parallel comb filters ───────
        inp  = xd * inp_scale
        suml = 0.0
        sumr = 0.0

        for k in range(8):
            # left
            bl   = cbufs_l[k]
            pl   = cpos_l[k]
            ol   = bl[pl]
            fs   = ol * d1m + cfs_l[k] * dmp
            bl[pl]   = inp + fs * fb_c
            cpos_l[k] = (pl + 1) % csizes_l[k]
            cfs_l[k] = fs
            suml += ol

            # right
            br   = cbufs_r[k]
            pr   = cpos_r[k]
            orr  = br[pr]
            fs2  = orr * d1m + cfs_r[k] * dmp
            br[pr]   = inp + fs2 * fb_c
            cpos_r[k] = (pr + 1) % csizes_r[k]
            cfs_r[k] = fs2
            sumr += orr

        # ── 4 series all-pass ─────────────────────
        for k in range(4):
            ab  = apbufs[k]
            ap  = appos[k]
            bv  = ab[ap]
            suml_new = -suml + bv
            ab[ap]  = suml + bv * ap_fb
            appos[k] = (ap + 1) % ap_delays[k]
            suml    = suml_new

            ab2 = apbufs2[k]
            ap2 = appos2[k]
            bv2 = ab2[ap2]
            sumr_new = -sumr + bv2
            ab2[ap2] = sumr + bv2 * ap_fb
            appos2[k] = (ap2 + 1) % ap_delays[k]
            sumr     = sumr_new

        dry = 1.0 - rev_mix
        out_l[i] = xd * dry + suml * rev_mix
        out_r[i] = xd * dry + sumr * rev_mix

    elapsed = time.time() - t0
    print(f"    100%  ({elapsed:.1f}s total)")
    return out_l, out_r


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inp  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base, 'gen', 'guitar_clean.wav')
    out  = sys.argv[2] if len(sys.argv) > 2 else os.path.join(base, 'gen', 'guitar_effected.wav')

    print(f"Input  : {inp}")
    print(f"Output : {out}")

    samples, sr = read_wav_mono(inp)
    print(f"  {len(samples)} samples @ {sr} Hz  ({len(samples)/sr:.1f}s)")

    left, right = process(samples, sr)

    print(f"Writing: {out}")
    write_wav_stereo(out, left, right, sr)
    size_mb = os.path.getsize(out) / 1e6
    print(f"Done — {size_mb:.1f} MB")
