#ifndef HAL_SIM_H
#define HAL_SIM_H

/**
 * HAL implementation for desktop simulator.
 * Knob/switch values are set externally (from Python via C API).
 * OLED buffer is read by Python for rendering.
 */

#include "hal.h"
#include <cstring>

class HalSim : public Hal {
    int sample_rate_;
    int block_size_;
    float   knobs_[8];
    bool    switches_[4];
    uint8_t oled_buf_[HAL_OLED_WIDTH * HAL_OLED_HEIGHT / 8];

public:
    HalSim(int sr = 48000, int bs = 256)
        : sample_rate_(sr), block_size_(bs) {
        std::memset(knobs_, 0, sizeof(knobs_));
        std::memset(switches_, 0, sizeof(switches_));
        std::memset(oled_buf_, 0, sizeof(oled_buf_));
    }

    int  getSampleRate() const override { return sample_rate_; }
    int  getBlockSize()  const override { return block_size_; }
    float getKnob(int i) const override {
        return (i >= 0 && i < 8) ? knobs_[i] : 0.0f;
    }
    int  getNumKnobs()    const override { return 7; }
    bool getSwitch(int i) const override {
        return (i >= 0 && i < 4) ? switches_[i] : false;
    }
    int  getNumSwitches() const override { return 1; }

    // Setters (called from Python side via C API)
    void setKnob(int i, float v)   { if (i >= 0 && i < 8) knobs_[i] = v; }
    void setSwitch(int i, bool v)  { if (i >= 0 && i < 4) switches_[i] = v; }

    uint8_t* getOledBuffer() override { return oled_buf_; }

    void oledClear() override {
        std::memset(oled_buf_, 0, sizeof(oled_buf_));
    }

    void oledSetPixel(int x, int y, bool on) override {
        if (x < 0 || x >= HAL_OLED_WIDTH ||
            y < 0 || y >= HAL_OLED_HEIGHT) return;
        int page = y / 8, bit = y % 8;
        int idx  = page * HAL_OLED_WIDTH + x;
        if (on) oled_buf_[idx] |=  (1 << bit);
        else    oled_buf_[idx] &= ~(1 << bit);
    }

    void oledDrawText(int x, int y, const char* text, int size) override {
        /* Text rendering handled by Python side */
        (void)x; (void)y; (void)text; (void)size;
    }

    void oledUpdate() override { /* No-op — Python reads buffer directly */ }
};

#endif /* HAL_SIM_H */
