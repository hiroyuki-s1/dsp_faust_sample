/**
 * effector_board — Daisy Seed hybrid mode (USB serial peripherals)
 *
 * Audio DSP runs on real Daisy Seed hardware.
 * Knob/switch values received from PC via USB CDC serial.
 * No physical ADC knobs needed.
 *
 * Build: make daisy-sim  (from project root)
 * Flash: cd daisy && make TARGET=effector_board_serial program-dfu
 */

#include "daisy_seed.h"
#include "daisysp.h"

// Faust runtime
#include "faust/dsp/dsp.h"
#include "faust/gui/UI.h"
#include "faust/gui/meta.h"
#include "faust/gui/MapUI.h"

// Generated Faust DSP
#include "effector_board.h"

using namespace daisy;

// ----------------------------------------------------------------
// Protocol (must match sim/serial_bridge.py)
// ----------------------------------------------------------------
#pragma pack(push, 1)
struct PcToDaisy {
    uint8_t sync[2];       // {0xAA, 0x55}
    float   knobs[7];      // normalized 0.0-1.0
    uint8_t switches[2];   // [0]=bypass, [1]=page
};

struct DaisyToPc {
    uint8_t sync[2];       // {0x55, 0xAA}
    float   params[7];     // echo back current knob values
    uint8_t status;        // 0=OK
};
#pragma pack(pop)

static constexpr size_t PC_FRAME_SIZE = sizeof(PcToDaisy);    // 32
static constexpr size_t DAISY_FRAME_SIZE = sizeof(DaisyToPc); // 31

// ----------------------------------------------------------------
// Hardware & DSP
// ----------------------------------------------------------------
static DaisySeed hw;
static mydsp DSY_SDRAM_BSS dsp;
static MapUI ui;

// Double-buffered knob values (main loop writes staging, audio reads active)
static volatile float knob_staging[7] = {};
static float          knob_active[7]  = {};
static volatile bool  bypass_staging  = false;
static volatile bool  new_frame_flag  = false;

// ----------------------------------------------------------------
// Ring buffer for USB CDC receive
// ----------------------------------------------------------------
static constexpr size_t RX_BUF_SIZE = 256;
static uint8_t          rx_buf[RX_BUF_SIZE];
static volatile size_t  rx_head = 0;
static volatile size_t  rx_tail = 0;

static void UsbRxCallback(uint8_t* buf, uint32_t* len)
{
    for (uint32_t i = 0; i < *len; i++)
    {
        size_t next = (rx_head + 1) % RX_BUF_SIZE;
        if (next != rx_tail)
        {
            rx_buf[rx_head] = buf[i];
            rx_head = next;
        }
    }
}

static inline size_t rx_available()
{
    return (rx_head - rx_tail + RX_BUF_SIZE) % RX_BUF_SIZE;
}

static inline uint8_t rx_peek(size_t offset)
{
    return rx_buf[(rx_tail + offset) % RX_BUF_SIZE];
}

static inline void rx_consume(size_t n)
{
    rx_tail = (rx_tail + n) % RX_BUF_SIZE;
}

// ----------------------------------------------------------------
// Parse serial frames from ring buffer
// ----------------------------------------------------------------
static void ParseSerialFrames()
{
    while (rx_available() >= PC_FRAME_SIZE)
    {
        // Scan for sync marker 0xAA 0x55
        if (rx_peek(0) != 0xAA || rx_peek(1) != 0x55)
        {
            rx_consume(1);
            continue;
        }

        // Read frame into local buffer
        uint8_t frame[PC_FRAME_SIZE];
        for (size_t i = 0; i < PC_FRAME_SIZE; i++)
        {
            frame[i] = rx_peek(i);
        }
        rx_consume(PC_FRAME_SIZE);

        PcToDaisy* pkt = reinterpret_cast<PcToDaisy*>(frame);

        // Validate knob values (NaN / range guard)
        bool valid = true;
        for (int k = 0; k < 7; k++)
        {
            float v = pkt->knobs[k];
            if (v != v || v < 0.0f || v > 1.0f)
            {
                valid = false;
                break;
            }
        }
        if (!valid)
            continue;

        // Copy to staging buffer
        for (int k = 0; k < 7; k++)
            knob_staging[k] = pkt->knobs[k];
        bypass_staging  = pkt->switches[0] != 0;
        new_frame_flag  = true;
    }
}

// ----------------------------------------------------------------
// Audio callback
// ----------------------------------------------------------------
void AudioCallback(AudioHandle::InputBuffer  in,
                   AudioHandle::OutputBuffer out,
                   size_t                    size)
{
    // Copy staging → active on new frame
    if (new_frame_flag)
    {
        for (int k = 0; k < 7; k++)
            knob_active[k] = knob_staging[k];
        new_frame_flag = false;
    }

    // Bypass mode
    if (bypass_staging)
    {
        for (size_t i = 0; i < size; i++)
        {
            out[0][i] = in[0][i];
            out[1][i] = in[0][i];
        }
        return;
    }

    // Map normalized 0-1 knobs to Faust parameter ranges
    ui.setParamValue("/effector_board/Delay/Time",
                     10.0f + knob_active[0] * 990.0f);
    ui.setParamValue("/effector_board/Delay/Feedback",
                     knob_active[1] * 0.95f);
    ui.setParamValue("/effector_board/Delay/Mix",
                     knob_active[2]);
    ui.setParamValue("/effector_board/Hall_Reverb/Room",
                     knob_active[3]);
    ui.setParamValue("/effector_board/Hall_Reverb/Damping",
                     knob_active[4]);
    ui.setParamValue("/effector_board/Hall_Reverb/Mix",
                     knob_active[5]);
    // Shimmer (knob 7) — path may not exist; setParamValue is no-op if missing
    ui.setParamValue("/effector_board/Hall_Reverb/Shimmer",
                     knob_active[6] * 0.9f);

    // Faust DSP compute
    FAUSTFLOAT* inputs[1]  = { (FAUSTFLOAT*)in[0] };
    FAUSTFLOAT* outputs[2] = { out[0], out[1] };
    dsp.compute(static_cast<int>(size), inputs, outputs);
}

// ----------------------------------------------------------------
// main
// ----------------------------------------------------------------
int main()
{
    hw.Configure();
    hw.Init();
    hw.SetAudioBlockSize(48);

    // No ADC init — knobs come from USB serial

    // USB CDC init
    hw.usb_handle.Init(UsbHandle::FS_INTERNAL);
    System::Delay(500);  // Wait for USB enumeration
    hw.usb_handle.SetReceiveCallback(UsbRxCallback,
                                     UsbHandle::FS_INTERNAL);

    // Faust DSP init
    dsp.init(static_cast<int>(hw.AudioSampleRate()));
    dsp.buildUserInterface(&ui);

    // Start audio
    hw.StartAudio(AudioCallback);

    // LED blink + heartbeat
    uint32_t last_tx     = 0;
    uint32_t led_counter = 0;

    while (true)
    {
        // Parse pending USB data
        ParseSerialFrames();

        // Send heartbeat at ~5 Hz
        uint32_t now = System::GetNow();
        if (now - last_tx > 200)
        {
            last_tx = now;

            DaisyToPc resp;
            resp.sync[0] = 0x55;
            resp.sync[1] = 0xAA;
            for (int k = 0; k < 7; k++)
                resp.params[k] = knob_active[k];
            resp.status = 0;
            hw.usb_handle.TransmitInternal(
                reinterpret_cast<uint8_t*>(&resp), sizeof(resp));

            // Blink LED to indicate hybrid mode (~2.5 Hz)
            hw.SetLed((led_counter++ & 1) != 0);
        }

        System::Delay(1);
    }
}
