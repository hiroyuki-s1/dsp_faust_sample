// Hall Reverb + Shimmer — for isolated testing
import("stdfaust.lib");

rev_room    = hslider("Room",    0.7, 0.0, 1.0, 0.01) : si.smoo;
rev_damp    = hslider("Damping", 0.5, 0.0, 1.0, 0.01) : si.smoo;
rev_mix     = hslider("Mix",     0.3, 0.0, 1.0, 0.01) : si.smoo;
shimmer_amt = hslider("Shimmer", 0.0, 0.0, 0.9, 0.01) : si.smoo;

t60dc   = 1.0 + rev_room * 7.0;
t60m    = 0.5 + rev_room * 5.5;
damp_hz = 7000.0 - rev_damp * 5500.0;

zita  = re.zita_rev1_stereo(20.0, 200.0, damp_hz, t60dc, t60m, 48000.0);
zita2 = _ <: (_, _) : zita;

pitch_up(x) = ef.transpose(4096, 256, 12.0, x) * shimmer_amt;
shimmer_in  = _ <: (_, pitch_up) : (_ + _);
shimmer_wet = _ : shimmer_in : zita2;

rev_proc = _ <: (shimmer_wet , _ , _)
             : route(4, 4, 1,1, 3,2, 2,3, 4,4)
             : par(i, 2, _ * rev_mix + _ * (1.0 - rev_mix));

process = _ : rev_proc;
