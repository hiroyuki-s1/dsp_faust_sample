#!/usr/bin/env bash
# gen_daisy.sh — Generate Faust C++ for Daisy Seed using faust2daisy (if available)
# Usage: ./scripts/gen_daisy.sh [dsp_file]
set -euo pipefail

DSP="${1:-dsp/delay_reverb.dsp}"
GEN_DIR="gen"
mkdir -p "$GEN_DIR"
BASENAME=$(basename "$DSP" .dsp)

echo "[gen_daisy] DSP file: $DSP"

# ── Option 1: faust2daisy (from faust-tools or DaisyExamples) ──
if command -v faust2daisy &>/dev/null; then
    echo "[gen_daisy] Using faust2daisy..."
    faust2daisy -sr 48000 -bs 48 "$DSP"
    mv "${BASENAME}.cpp" "$GEN_DIR/" 2>/dev/null || true
    echo "[gen_daisy] Done: $GEN_DIR/${BASENAME}.cpp"
    exit 0
fi

# ── Option 2: faust with daisy.cpp architecture ──
DAISY_ARCH="/usr/share/faust/daisy.cpp"
if [ -f "$DAISY_ARCH" ]; then
    echo "[gen_daisy] Using architecture: $DAISY_ARCH"
    faust -lang cpp -a "$DAISY_ARCH" -vec -vs 32 -ftz 2 \
          -o "$GEN_DIR/${BASENAME}.cpp" "$DSP"
    echo "[gen_daisy] Done: $GEN_DIR/${BASENAME}.cpp"
    exit 0
fi

# ── Option 3: faust with minimal.cpp (basic C++ output) ──
MINIMAL_ARCH="/usr/share/faust/minimal.cpp"
if [ -f "$MINIMAL_ARCH" ]; then
    echo "[gen_daisy] WARNING: daisy.cpp not found, using minimal.cpp"
    echo "[gen_daisy] You will need to adapt the output for Daisy Seed manually."
    faust -lang cpp -a "$MINIMAL_ARCH" -vec -vs 32 -ftz 2 \
          -o "$GEN_DIR/${BASENAME}.cpp" "$DSP"
    echo "[gen_daisy] Done: $GEN_DIR/${BASENAME}.cpp"
    exit 0
fi

# ── Option 4: bare C++ (no architecture wrapper) ──
echo "[gen_daisy] WARNING: No architecture file found. Generating bare C++."
faust -lang cpp -o "$GEN_DIR/${BASENAME}.cpp" "$DSP"
echo "[gen_daisy] Done: $GEN_DIR/${BASENAME}.cpp"
