#ifndef HAL_DAISY_H
#define HAL_DAISY_H

/**
 * HAL implementation for real Daisy Seed hardware.
 * Uses DaisySeed API for ADC, GPIO, SPI/I2C OLED.
 */

#include "hal.h"
#include "daisy_seed.h"
#include <cstring>

class HalDaisy : public Hal {
    daisy::DaisySeed& hw_;
    uint8_t oled_buf_[HAL_OLED_WIDTH * HAL_OLED_HEIGHT / 8];

public:
    explicit HalDaisy(daisy::DaisySeed& hw) : hw_(hw) {
        std::memset(oled_buf_, 0, sizeof(oled_buf_));
    }

    int  getSampleRate() const override { return hw_.AudioSampleRate(); }
    int  getBlockSize()  const override { return hw_.AudioBlockSize(); }
    float getKnob(int i) const override { return hw_.adc.GetFloat(i); }
    int   getNumKnobs()  const override { return 7; }
    bool  getSwitch(int i) const override { (void)i; return false; }
    int   getNumSwitches() const override { return 1; }

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
        /* TODO: SSD1306 font rendering */
        (void)x; (void)y; (void)text; (void)size;
    }

    void oledUpdate() override {
        /* TODO: SPI/I2C transfer to SSD1306 */
    }
};

#endif /* HAL_DAISY_H */
