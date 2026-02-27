// ============================================================
// Room Reverb
// Zita Rev1 ベースの小部屋リバーブ。
// 残響時間が短く、身近で自然な空間感。
// I/O : mono → stereo
// ============================================================
import("stdfaust.lib");

rev_room = hslider("v:Room Reverb/[01]Room",    0.4, 0.0, 1.0, 0.01) : si.smoo;
rev_damp = hslider("v:Room Reverb/[02]Damping", 0.6, 0.0, 1.0, 0.01) : si.smoo;
rev_mix  = hslider("v:Room Reverb/[03]Mix",     0.25, 0.0, 1.0, 0.01) : si.smoo;

// 小部屋: 残響時間がホールより大幅に短い (t60dc: 0.5s ~ 2.0s)
t60dc   = 0.5 + rev_room * 1.5;
t60m    = 0.3 + rev_room * 1.2;
// 早めの高域吸収 (部屋の壁の特性)
damp_hz = 5000.0 - rev_damp * 3000.0;

// rdel=5ms (ホール 20ms より早い初期反射), f1=200Hz 低域クロスオーバー
zita  = re.zita_rev1_stereo(5.0, 200.0, damp_hz, t60dc, t60m, 48000.0);
zita2 = _ <: (_, _) : zita;

process = _ <: (zita2, _, _)
             : route(4, 4, 1,1, 3,2, 2,3, 4,4)
             : par(i, 2, _ * rev_mix + _ * (1.0 - rev_mix));
