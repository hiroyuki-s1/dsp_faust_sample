# ============================================================
# Daisy Seed build Makefile
# Requires: libdaisy + DaisySP installed
# See: https://github.com/electro-smith/DaisyToolchain
# ============================================================

# Path to libdaisy (adjust to your installation)
LIBDAISY_DIR ?= $(HOME)/daisy/libdaisy
DAISYSP_DIR  ?= $(HOME)/daisy/DaisySP

# Target binary name
TARGET ?= effector_board

# Source files (main.cpp only — Faust output is header-only, included by main.cpp)
# Override with CPP_SOURCES=main_serial.cpp for hybrid mode
CPP_SOURCES ?= main.cpp

# -------- Include paths --------
# ../gen also contains faust/ runtime headers (copied by gen-daisy)
C_INCLUDES = \
    -I$(LIBDAISY_DIR)/src \
    -I$(DAISYSP_DIR)/Source \
    -I../gen

# -------- Daisy Makefile boilerplate --------
SYSTEM_FILES_DIR = $(LIBDAISY_DIR)/core
include $(LIBDAISY_DIR)/core/Makefile

# -------- Generate Faust C++ for Daisy --------
.PHONY: gen clean-gen

gen: ../gen/effector_board.h

../gen/effector_board.h:
	$(MAKE) -C .. gen-daisy

clean-gen:
	rm -f ../gen/effector_board.h
