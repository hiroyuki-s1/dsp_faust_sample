// ============================================================
// Digital Delay
// クリアな明るいデジタルディレイ。
// I/O : mono → mono
// ============================================================
import("stdfaust.lib");

delay_time     = hslider("v:Delay/[01]Time [unit:ms]", 300, 10, 1000, 1)     : si.smoo;
delay_feedback = hslider("v:Delay/[02]Feedback",        0.5, 0.0, 0.95, 0.01) : si.smoo;
delay_mix      = hslider("v:Delay/[03]Mix",             0.4, 0.0, 1.0,  0.01) : si.smoo;

delay_n = int(delay_time * float(ma.SR) / 1000.0);
echo    = +~(de.delay(ma.SR, delay_n) * delay_feedback);

process = _ <: (echo, _)
            : (_ * delay_mix, _ * (1.0 - delay_mix))
            :> _;
