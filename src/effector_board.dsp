// ============================================================
// EffectorBoard — Guitar Effect Chain
// Target : Daisy Seed (48kHz, mono in / stereo out)
//
// エフェクターを並べるだけでチェーンになります。
// 使うエフェクターを下のリストから選んでパスを変えてください。
// ============================================================
import("stdfaust.lib");

// ── Delay 系 (mono → mono) ─────────────────────────────────
//   effectors/delay/delay.dsp         クリアなデジタルディレイ
//   effectors/delay/analog_delay.dsp  テープ/アナログ風（LPF + 歪み）
//   effectors/delay/echo_delay.dsp    2タップ・エコー

delay = component("effectors/delay/delay.dsp");

// ── Reverb 系 (mono → stereo) ──────────────────────────────
//   effectors/reverb/hall_reverb.dsp  ホールリバーブ（長い残響）
//   effectors/reverb/room_reverb.dsp  ルームリバーブ（短い残響）
//   effectors/reverb/shimmer.dsp      シマーリバーブ（倍音+残響）

reverb = component("effectors/reverb/hall_reverb.dsp");

// ── ボード: 直列に接続 ─────────────────────────────────────
//   mono in → [delay] → [reverb] → stereo out
process = _ : delay : reverb;
