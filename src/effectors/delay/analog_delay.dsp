// ============================================================
// Analog Delay
// テープ/アナログ回路をシミュレート。
//   - フィードバックループにLPF（テープヘッドの高域減衰）
//   - ソフトクリップでフィードバックが歪む
// I/O : mono → mono
// ============================================================
import("stdfaust.lib");

delay_time     = hslider("v:Analog Delay/[01]Time [unit:ms]", 350, 10, 1000, 1)     : si.smoo;
delay_feedback = hslider("v:Analog Delay/[02]Feedback",        0.5, 0.0, 0.95, 0.01) : si.smoo;
delay_mix      = hslider("v:Analog Delay/[03]Mix",             0.4, 0.0, 1.0,  0.01) : si.smoo;
tone           = hslider("v:Analog Delay/[04]Tone",            0.5, 0.0, 1.0,  0.01) : si.smoo;

// テープヘッドの周波数特性: Tone で高域上限を調整 (500Hz ~ 6500Hz)
cutoff = 500.0 + tone * 6000.0;
lp(x)  = fi.lowpass(1, cutoff, x);

// ソフトクリップ: フィードバックが積み重なるほど歪む
sat(x) = ma.tanh(x * 1.8) / 1.8;

delay_n = int(delay_time * float(ma.SR) / 1000.0);
echo    = +~(de.delay(ma.SR, delay_n) : lp : sat : *(delay_feedback));

process = _ <: (echo, _)
            : (_ * delay_mix, _ * (1.0 - delay_mix))
            :> _;
