// ============================================================
// Echo Delay
// 2タップ・エコー。
//   - tap1 = delay_time           (フィードバックループ付き)
//   - tap2 = delay_time × 1.5    (ドット付き音符感、減衰あり)
// I/O : mono → mono
// ============================================================
import("stdfaust.lib");

delay_time = hslider("v:Echo/[01]Time [unit:ms]", 220, 10, 800, 1)     : si.smoo;
decay      = hslider("v:Echo/[02]Decay",           0.6, 0.0, 0.95, 0.01) : si.smoo;
echo_mix   = hslider("v:Echo/[03]Mix",             0.4, 0.0, 1.0,  0.01) : si.smoo;

delay_n1 = int(delay_time           * float(ma.SR) / 1000.0);
delay_n2 = int(delay_time * 1.5     * float(ma.SR) / 1000.0);

// タップ1: フィードバックループ
tap1 = +~(de.delay(ma.SR, delay_n1) * decay);

// タップ2: 遅延のみ、tap1より小さく
tap2(x) = de.delay(ma.SR, delay_n2, x) * (decay * 0.6);

process = _ <: (tap1, tap2, _)
            : (_ * echo_mix, _ * echo_mix * 0.7, _ * (1.0 - echo_mix))
            :> _;
