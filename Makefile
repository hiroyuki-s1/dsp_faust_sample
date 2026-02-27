# ============================================================
# dsp_faust_sample — top-level Makefile
# ============================================================

FAUST       ?= faust
SRC_DIR     = src
GEN_DIR     = gen
PARAMS_FILE = params/default.json

# Default DSP file (override: make TARGET=effectors/delay/analog_delay)
TARGET ?= effector_board

DSP_FILE  = $(SRC_DIR)/$(TARGET).dsp
CPP_FILE  = $(GEN_DIR)/$(TARGET).cpp
HDR_FILE  = $(GEN_DIR)/$(TARGET).h
SVG_DIR   = $(GEN_DIR)/$(TARGET)-svg
WAV_OUT   = $(GEN_DIR)/$(TARGET).wav

.PHONY: all gen gen-daisy diagram check check-all clean help sim sim-lib sim-gen daisy daisy-sim sim-serial

all: check gen diagram

# ── Syntax check (fast) ──────────────────────────────────────
check:
	@echo "[FAUST] Checking $(DSP_FILE)..."
	$(FAUST) -wall $(DSP_FILE) -o /dev/null 2>&1
	@echo "  OK"

# ── Check all effectors + the board ──────────────────────────
check-all:
	@echo "[FAUST] Checking all effectors..."
	@for f in \
	  src/effectors/delay/*.dsp \
	  src/effectors/reverb/*.dsp \
	  src/effector_board.dsp; do \
	  printf "  %-54s" "$$f"; \
	  $(FAUST) $$f -o /dev/null 2>&1 && echo "OK" || echo "FAIL"; \
	done

# ── Generate C++ for Daisy Seed ──────────────────────────────
gen: $(CPP_FILE)

$(CPP_FILE): $(DSP_FILE) | $(GEN_DIR)
	@echo "[FAUST] Generating C++ (minimal arch) -> $(CPP_FILE)"
	$(FAUST) \
		-lang cpp \
		-a $(FAUST_ARCH) \
		-vec \
		-vs 32 \
		-ftz 2 \
		-o $(CPP_FILE) \
		$(DSP_FILE)
	@echo "  Done: $(CPP_FILE)"

# Architecture file: try daisy first, fall back to minimal
FAUST_ARCH_DAISY  = /usr/share/faust/daisy.cpp
FAUST_ARCH_MINIMAL = /usr/share/faust/minimal.cpp
FAUST_ARCH = $(shell [ -f $(FAUST_ARCH_DAISY) ] && echo $(FAUST_ARCH_DAISY) || echo $(FAUST_ARCH_MINIMAL))

# ── Generate C++ header-only (for embedding in Daisy project) ─
header: | $(GEN_DIR)
	@echo "[FAUST] Generating self-contained header -> $(HDR_FILE)"
	$(FAUST) \
		-lang cpp \
		-inj /usr/share/faust/minimalUI.h \
		-o $(HDR_FILE) \
		$(DSP_FILE) || \
	$(FAUST) \
		-lang cpp \
		-o $(HDR_FILE) \
		$(DSP_FILE)

# ── Generate bare C++ header for Daisy Seed ───────────────────
DAISY_HDR = $(GEN_DIR)/effector_board.h

gen-daisy: $(DAISY_HDR)

$(DAISY_HDR): $(SRC_DIR)/effector_board.dsp
	@mkdir -p $(GEN_DIR)/faust/dsp $(GEN_DIR)/faust/gui
	@echo "[FAUST] Generating bare header -> $(DAISY_HDR)"
	$(FAUST) -lang cpp -o $(DAISY_HDR) $(SRC_DIR)/effector_board.dsp
	@echo "[FAUST] Copying runtime headers -> $(GEN_DIR)/faust/"
	@cp /usr/include/faust/dsp/dsp.h       $(GEN_DIR)/faust/dsp/
	@cp /usr/include/faust/gui/UI.h        $(GEN_DIR)/faust/gui/
	@cp /usr/include/faust/gui/meta.h      $(GEN_DIR)/faust/gui/
	@cp /usr/include/faust/gui/MapUI.h     $(GEN_DIR)/faust/gui/
	@cp /usr/include/faust/gui/PathBuilder.h $(GEN_DIR)/faust/gui/
	@cp /usr/include/faust/export.h        $(GEN_DIR)/faust/
	@echo "  Done: $(DAISY_HDR)"

# ── Generate block diagram SVG ────────────────────────────────
diagram: | $(GEN_DIR)
	@echo "[FAUST] Generating block diagram -> $(SVG_DIR)"
	$(FAUST) -svg -o $(SVG_DIR) $(DSP_FILE) 2>/dev/null || \
	$(FAUST) -svg $(DSP_FILE) -o $(SVG_DIR)/$(TARGET).svg 2>/dev/null || \
	$(FAUST) -svg $(DSP_FILE) 2>/dev/null
	@echo "  See: $(SVG_DIR)/"

# ── Print parameters (from params file) ──────────────────────
params:
	@python3 scripts/print_params.py $(PARAMS_FILE)

# ── List all Faust architecture files ────────────────────────
archs:
	@ls /usr/share/faust/*.cpp 2>/dev/null | sort

$(GEN_DIR):
	mkdir -p $(GEN_DIR)

# ── Simulator ────────────────────────────────────────────────
SIM_SO       = $(GEN_DIR)/sim_engine.so
SIM_BARE_CPP = $(GEN_DIR)/effector_board_bare.cpp
SIM_SRC      = sim_src/faust_api.cpp

# Generate bare Faust C++ (no architecture wrapper) for simulator
sim-gen: $(SIM_BARE_CPP)

$(SIM_BARE_CPP): $(SRC_DIR)/effector_board.dsp
	@mkdir -p $(GEN_DIR)
	@echo "[SIM] Generating bare C++ -> $(SIM_BARE_CPP)"
	$(FAUST) -lang cpp -o $(SIM_BARE_CPP) $(SRC_DIR)/effector_board.dsp

# Build shared library
sim-lib: $(SIM_BARE_CPP)
	@echo "[SIM] Building $(SIM_SO)..."
	g++ -shared -fPIC -O2 -std=c++17 \
		-I/usr/include -I$(GEN_DIR) -Isim_src \
		$(SIM_SRC) -o $(SIM_SO)
	@echo "  Done: $(SIM_SO)"

# Launch simulator GUI
sim: sim-lib
	@echo "[SIM] Starting Daisy Seed Simulator..."
	python3 -m sim.main

# Build for Daisy Seed hardware
daisy: gen-daisy
	$(MAKE) -C daisy all

# ── Hybrid mode (real Daisy DSP + USB serial peripherals) ─────
SERIAL_PORT ?= /dev/ttyACM0

# Build hybrid firmware for Daisy Seed (USB serial knobs, no ADC)
daisy-sim: gen-daisy
	$(MAKE) -C daisy TARGET=effector_board_serial CPP_SOURCES=main_serial.cpp all

# Launch hybrid GUI (connects to Daisy via USB serial)
sim-serial:
	@echo "[HYBRID] Starting hybrid simulator (port: $(SERIAL_PORT))..."
	python3 -m sim.main_serial --port $(SERIAL_PORT)

clean:
	rm -rf $(GEN_DIR)

help:
	@echo ""
	@echo "  make check           — effector_board の構文チェック"
	@echo "  make check-all       — 全エフェクター + ボードを一括チェック"
	@echo "  make gen             — Daisy Seed 向け C++ 生成"
	@echo "  make diagram         — SVG ブロック図生成"
	@echo "  make params          — パラメータ一覧表示"
	@echo "  make clean           — 生成ファイル削除"
	@echo ""
	@echo "  シミュレータ:"
	@echo "  make sim             — シミュレータ起動 (.so ビルド + GUI)"
	@echo "  make sim-lib         — 共有ライブラリのみビルド"
	@echo "  make daisy           — Daisy Seed 実機ビルド"
	@echo ""
	@echo "  ハイブリッドモード (実機Daisy + USBシリアル周辺機器):"
	@echo "  make daisy-sim       — ハイブリッド Daisy ファームウェアビルド"
	@echo "  make sim-serial      — ハイブリッド GUI 起動 (要 pyserial)"
	@echo "  make sim-serial SERIAL_PORT=/dev/ttyACM1  — ポート指定"
	@echo ""
	@echo "  個別チェック例:"
	@echo "  make TARGET=effectors/delay/delay check"
	@echo "  make TARGET=effectors/delay/analog_delay check"
	@echo "  make TARGET=effectors/reverb/room_reverb check"
	@echo ""
