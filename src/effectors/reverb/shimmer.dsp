// ============================================================
// Shimmer Reverb
// ホールリバーブ + オクターブ上の倍音。
// 入力にピッチシフト成分を混ぜてからリバーブに送ることで
// キラキラとした幻想的な持続音を生成する。
// I/O : mono → stereo
// ============================================================
import("stdfaust.lib");

rev_room    = hslider("v:Shimmer/[01]Room",    0.9, 0.0, 1.0, 0.01) : si.smoo;
rev_damp    = hslider("v:Shimmer/[02]Damping", 0.3, 0.0, 1.0, 0.01) : si.smoo;
rev_mix     = hslider("v:Shimmer/[03]Mix",     0.5, 0.0, 1.0, 0.01) : si.smoo;
shimmer_amt = hslider("v:Shimmer/[04]Amount",  0.6, 0.0, 0.9, 0.01) : si.smoo;

t60dc   = 1.0 + rev_room * 7.0;
t60m    = 0.5 + rev_room * 5.5;
damp_hz = 7000.0 - rev_damp * 5500.0;

zita  = re.zita_rev1_stereo(20.0, 200.0, damp_hz, t60dc, t60m, 48000.0);
zita2 = _ <: (_, _) : zita;

// オクターブ上にピッチシフト (ef.transpose: ウィンドウ4096, ホップ256, 半音12)
pitch_up(x) = ef.transpose(4096, 256, 12.0, x) * shimmer_amt;

// ドライにピッチシフト成分を足してからリバーブへ
shimmer_in  = _ <: (_, pitch_up) : (_ + _);
shimmer_wet = _ : shimmer_in : zita2;

process = _ <: (shimmer_wet, _, _)
             : route(4, 4, 1,1, 3,2, 2,3, 4,4)
             : par(i, 2, _ * rev_mix + _ * (1.0 - rev_mix));
