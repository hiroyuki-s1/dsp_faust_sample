// Delay only — for isolated testing
import("stdfaust.lib");

delay_time     = hslider("Time [unit:ms]", 300, 10, 1000, 1)   : si.smoo;
delay_feedback = hslider("Feedback",       0.5, 0.0, 0.95, 0.01) : si.smoo;
delay_mix      = hslider("Mix",            0.4, 0.0, 1.0,  0.01) : si.smoo;

max_delay_n = int(ma.SR);
delay_n     = int(delay_time * float(ma.SR) / 1000.0);
echo        = +~(de.delay(max_delay_n, delay_n) * delay_feedback);

process = _ <: (echo, _) : (_ * delay_mix, _ * (1.0 - delay_mix)) :> _;
