// ============================================================
// Guitar Effect: Delay + Hall Reverb + Shimmer
// Target: Daisy Seed (48kHz, mono in / stereo out)
// ============================================================

import("stdfaust.lib");

// ============================================================
// Parameters
// ============================================================
delay_time     = hslider("v:Delay/[01]Time [unit:ms]", 300, 10, 1000, 1)    : si.smoo;
delay_feedback = hslider("v:Delay/[02]Feedback",        0.5, 0.0, 0.95, 0.01) : si.smoo;
delay_mix      = hslider("v:Delay/[03]Mix",             0.4, 0.0, 1.0,  0.01) : si.smoo;

rev_room    = hslider("v:Reverb/[01]Room",    0.7, 0.0, 1.0, 0.01) : si.smoo;
rev_damp    = hslider("v:Reverb/[02]Damping", 0.5, 0.0, 1.0, 0.01) : si.smoo;
rev_mix     = hslider("v:Reverb/[03]Mix",     0.3, 0.0, 1.0, 0.01) : si.smoo;
shimmer_amt = hslider("v:Reverb/[04]Shimmer", 0.0, 0.0, 0.9, 0.01) : si.smoo;

// ============================================================
// Delay Effect
// ============================================================
delay_n    = int(delay_time * float(ma.SR) / 1000.0);
echo       = +~(de.delay(ma.SR, delay_n) * delay_feedback);

// mono wet/dry blend → mono out
delay_proc = _ <: (echo, _)
               : (_ * delay_mix, _ * (1.0 - delay_mix))
               :> _;

// ============================================================
// Hall Reverb + Shimmer  (Zita Rev1 — stereo, 2 in / 2 out)
// ============================================================
t60dc   = 1.0 + rev_room * 7.0;
t60m    = 0.5 + rev_room * 5.5;
damp_hz = 7000.0 - rev_damp * 5500.0;

zita  = re.zita_rev1_stereo(20.0, 200.0, damp_hz, t60dc, t60m, 48000.0);
zita2 = _ <: (_, _) : zita;  // mono->stereo wrapper

// Shimmer: octave-up pitch shifted signal mixed into reverb input.
// pitch_up(x) uses ef.transpose (+12 semitones = +1 octave) then scales by shimmer_amt.
// shimmer_in adds the shimmer harmonic to the dry signal before entering zita.
pitch_up(x) = ef.transpose(4096, 256, 12.0, x) * shimmer_amt;
shimmer_in  = _ <: (_, pitch_up) : (_ + _);
shimmer_wet = _ : shimmer_in : zita2;  // 1 in → 2 out (wet stereo)

// mono in → stereo out with wet/dry
//
// Signal flow:
//   x ──<:──┬── shimmer_wet ──┬── wet_L ─┐
//            │                └── wet_R ─┤  route  ┌── wet_L * rv + dry * (1-rv)
//            ├── dry_L ─────────────────┤ ──────► │
//            └── dry_R ─────────────────┘         └── wet_R * rv + dry * (1-rv)

rev_proc = _ <: (shimmer_wet , _ , _)
             : route(4, 4, 1,1, 3,2, 2,3, 4,4)
             : par(i, 2, _ * rev_mix + _ * (1.0 - rev_mix));

// ============================================================
// Main: mono in → delay → hall reverb (+shimmer) → stereo out
// ============================================================
process = _ : delay_proc : rev_proc;
