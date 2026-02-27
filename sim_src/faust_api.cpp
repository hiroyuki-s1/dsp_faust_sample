#include "faust_api.h"
#include <cstring>
#include <vector>
#include <string>

// Faust runtime headers
#include "faust/dsp/dsp.h"
#include "faust/gui/UI.h"
#include "faust/gui/meta.h"
#include "faust/gui/MapUI.h"

// Faust-generated DSP (bare output, defines class mydsp : public dsp)
#include "effector_board_bare.cpp"

// Bitmap font for OLED text
#include "oled_font5x7.h"

// ── Engine state ──────────────────────────────────────────────
struct FaustEngine {
    mydsp  dsp;
    MapUI  ui;
    unsigned char oled_buf[OLED_BUF_SIZE];
    std::vector<std::string> param_addresses;  // stable storage for c_str()
};

// ── Lifecycle ─────────────────────────────────────────────────
faust_handle_t faust_create(void) {
    auto* e = new FaustEngine();
    std::memset(e->oled_buf, 0, OLED_BUF_SIZE);
    return static_cast<faust_handle_t>(e);
}

void faust_destroy(faust_handle_t h) {
    delete static_cast<FaustEngine*>(h);
}

void faust_init(faust_handle_t h, int sample_rate) {
    auto* e = static_cast<FaustEngine*>(h);
    e->dsp.init(sample_rate);
    e->dsp.buildUserInterface(&e->ui);
    // Cache param addresses for stable c_str() pointers
    int n = e->ui.getParamsCount();
    e->param_addresses.resize(n);
    for (int i = 0; i < n; i++)
        e->param_addresses[i] = e->ui.getParamAddress(i);
}

// ── DSP info ──────────────────────────────────────────────────
int faust_get_num_inputs(faust_handle_t h) {
    return static_cast<FaustEngine*>(h)->dsp.getNumInputs();
}

int faust_get_num_outputs(faust_handle_t h) {
    return static_cast<FaustEngine*>(h)->dsp.getNumOutputs();
}

// ── Parameters ────────────────────────────────────────────────
int faust_get_params_count(faust_handle_t h) {
    return static_cast<FaustEngine*>(h)->ui.getParamsCount();
}

const char* faust_get_param_address(faust_handle_t h, int index) {
    auto* e = static_cast<FaustEngine*>(h);
    if (index < 0 || index >= (int)e->param_addresses.size()) return "";
    return e->param_addresses[index].c_str();
}

void faust_set_param(faust_handle_t h, const char* path, float value) {
    static_cast<FaustEngine*>(h)->ui.setParamValue(path, (FAUSTFLOAT)value);
}

float faust_get_param(faust_handle_t h, const char* path) {
    return static_cast<FaustEngine*>(h)->ui.getParamValue(path);
}

// ── Audio ─────────────────────────────────────────────────────
void faust_compute(faust_handle_t h, int count,
                   float** inputs, float** outputs) {
    static_cast<FaustEngine*>(h)->dsp.compute(count, inputs, outputs);
}

// ── OLED frame buffer ─────────────────────────────────────────
const unsigned char* faust_oled_get_framebuf(faust_handle_t h) {
    return static_cast<FaustEngine*>(h)->oled_buf;
}

void faust_oled_clear(faust_handle_t h) {
    std::memset(static_cast<FaustEngine*>(h)->oled_buf, 0, OLED_BUF_SIZE);
}

void faust_oled_set_pixel(faust_handle_t h, int x, int y, int on) {
    if (x < 0 || x >= OLED_WIDTH || y < 0 || y >= OLED_HEIGHT) return;
    auto* buf = static_cast<FaustEngine*>(h)->oled_buf;
    int page = y / 8;
    int bit  = y % 8;
    int idx  = page * OLED_WIDTH + x;
    if (on) buf[idx] |=  (1 << bit);
    else    buf[idx] &= ~(1 << bit);
}

void faust_oled_draw_text(faust_handle_t h, int x, int y,
                          const char* text, int font_size) {
    int scale = (font_size > 0) ? 2 : 1;
    int cx = x;
    for (const char* p = text; *p; ++p) {
        int ch = (*p < 0x20 || *p > 0x7E) ? 0 : (*p - 0x20);
        for (int col = 0; col < 5; col++) {
            unsigned char bits = font5x7[ch][col];
            for (int row = 0; row < 7; row++) {
                if (bits & (1 << row)) {
                    for (int sy = 0; sy < scale; sy++)
                        for (int sx = 0; sx < scale; sx++)
                            faust_oled_set_pixel(h,
                                cx + col * scale + sx,
                                y  + row * scale + sy, 1);
                }
            }
        }
        cx += (5 + 1) * scale;
    }
}

void faust_oled_update(faust_handle_t h) {
    /* No-op in simulator — Python reads framebuf directly */
    (void)h;
}
