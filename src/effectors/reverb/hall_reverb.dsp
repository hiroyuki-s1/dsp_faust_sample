// ============================================================
// Hall Reverb
// Zita Rev1 ベースの大きなホールリバーブ。
// 残響時間が長く、広がりのある空間感。
// I/O : mono → stereo
// ============================================================
import("stdfaust.lib");

rev_room = hslider("v:Hall Reverb/[01]Room",    0.7, 0.0, 1.0, 0.01) : si.smoo;
rev_damp = hslider("v:Hall Reverb/[02]Damping", 0.5, 0.0, 1.0, 0.01) : si.smoo;
rev_mix  = hslider("v:Hall Reverb/[03]Mix",     0.3, 0.0, 1.0, 0.01) : si.smoo;

// Room が大きいほど残響が長い (t60dc: 1.0s ~ 8.0s)
t60dc   = 1.0 + rev_room * 7.0;
t60m    = 0.5 + rev_room * 5.5;
// Damping が大きいほど高域が吸収される
damp_hz = 7000.0 - rev_damp * 5500.0;

zita  = re.zita_rev1_stereo(20.0, 200.0, damp_hz, t60dc, t60m, 48000.0);
zita2 = _ <: (_, _) : zita;

process = _ <: (zita2, _, _)
             : route(4, 4, 1,1, 3,2, 2,3, 4,4)
             : par(i, 2, _ * rev_mix + _ * (1.0 - rev_mix));
