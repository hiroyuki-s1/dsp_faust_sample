#ifndef HAL_H
#define HAL_H

/**
 * Hardware Abstraction Layer — common interface for Daisy Seed and simulator.
 *
 * main.cpp のアプリケーションロジックはこのインターフェースのみ使用する。
 * ビルドターゲットに応じて hal_daisy.h または hal_sim.h をインクルード。
 */

#include <cstdint>

#define HAL_OLED_WIDTH  128
#define HAL_OLED_HEIGHT 64

class Hal {
public:
    virtual ~Hal() {}

    // ── Audio ──
    virtual int  getSampleRate() const = 0;
    virtual int  getBlockSize()  const = 0;

    // ── Knobs (ADC, 0.0–1.0) ──
    virtual float getKnob(int index) const = 0;
    virtual int   getNumKnobs()      const = 0;

    // ── Switches ──
    virtual bool getSwitch(int index) const = 0;
    virtual int  getNumSwitches()     const = 0;

    // ── OLED ──
    virtual uint8_t* getOledBuffer()                                    = 0;
    virtual void oledClear()                                            = 0;
    virtual void oledSetPixel(int x, int y, bool on)                    = 0;
    virtual void oledDrawText(int x, int y, const char* text, int size) = 0;
    virtual void oledUpdate()                                           = 0;
};

#endif /* HAL_H */
