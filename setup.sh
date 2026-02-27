#!/usr/bin/env bash
# setup.sh — One-time environment setup
# Run: bash setup.sh
set -euo pipefail

echo "=== dsp_faust_sample setup ==="

# ────────────────────────────────────────────
# 1. Install Faust
# ────────────────────────────────────────────
echo ""
echo "[1] Installing Faust..."
sudo apt-get update -qq
sudo apt-get install -y faust faust-common

echo "    Faust version: $(faust --version 2>&1 | head -1)"
echo "    Architecture files: $(ls /usr/share/faust/*.cpp 2>/dev/null | wc -l) files"

# ────────────────────────────────────────────
# 2. Check available architectures
# ────────────────────────────────────────────
echo ""
echo "[2] Available Faust architecture files:"
ls /usr/share/faust/*.cpp 2>/dev/null | sed 's|.*/||' | sed 's/\.cpp//' | sort | column

if [ -f /usr/share/faust/daisy.cpp ]; then
    echo "    daisy.cpp: FOUND — Daisy Seed architecture available"
else
    echo "    daisy.cpp: NOT FOUND — will use minimal.cpp + manual adaptation"
    echo "    (daisy.cpp is available in DaisyExamples repo)"
fi

# ────────────────────────────────────────────
# 3. Install VSCode Faust extension (optional)
# ────────────────────────────────────────────
echo ""
echo "[3] Installing VSCode Faust extension..."
if command -v code &>/dev/null; then
    code --install-extension nuchi.faust-vscode || \
    echo "    Note: install manually from VSCode: Extensions → search 'Faust'"
else
    echo "    code command not found — install extension manually:"
    echo "    VSCode Extensions → search 'Faust' → install 'nuchi.faust-vscode'"
fi

# ────────────────────────────────────────────
# 4. Quick syntax test
# ────────────────────────────────────────────
echo ""
echo "[4] Testing Faust compilation..."
if faust -wall dsp/delay_reverb.dsp -o /dev/null 2>&1; then
    echo "    delay_reverb.dsp: OK"
else
    echo "    delay_reverb.dsp: FAILED — check output above"
fi

# ────────────────────────────────────────────
# 5. Optional: Daisy Seed toolchain
# ────────────────────────────────────────────
echo ""
echo "[5] Daisy Seed toolchain (optional):"
echo "    To build for Daisy Seed hardware, install DaisyToolchain:"
echo "    https://github.com/electro-smith/DaisyToolchain"
echo ""
echo "    Quick install (ARM cross-compiler):"
echo "    sudo apt-get install -y gcc-arm-none-eabi binutils-arm-none-eabi"
echo ""
echo "    Then clone libdaisy and DaisySP:"
echo "    mkdir -p ~/daisy"
echo "    git clone https://github.com/electro-smith/libDaisy ~/daisy/libdaisy"
echo "    git clone https://github.com/electro-smith/DaisySP ~/daisy/DaisySP"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  make check    — verify DSP syntax"
echo "  make gen      — generate C++ from DSP"
echo "  make diagram  — generate SVG block diagram"
