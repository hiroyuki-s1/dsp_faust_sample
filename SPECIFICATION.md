# dsp_faust_sample 仕様書

## 1. プロジェクト概要

### 1.1 目的
ギターエフェクト（ディレイ + リバーブ + シマー）を Faust 言語でプロトタイピングし、
Daisy Seed マイコンボード上で動作する組み込みオーディオエフェクターを実現するプロジェクト。

### 1.2 システム全体像

```
┌────────────────────────────────────────────────────────────────────┐
│  DSP定義層 (Faust)                                                  │
│  src/effector_board.dsp → エフェクターチェーン定義                      │
│  src/effectors/delay/*.dsp → ディレイ系エフェクター (3種)               │
│  src/effectors/reverb/*.dsp → リバーブ系エフェクター (3種)              │
└──────┬─────────────┬────────────────────┬──────────────────────────┘
       │             │                    │
       ▼             ▼                    ▼
┌──────────┐  ┌──────────────┐  ┌─────────────────────────┐
│ Daisy実機  │  │ デスクトップ    │  │ ブラウザプレビュー         │
│ (ARM C++)  │  │ シミュレータ    │  │ (Web Audio API)          │
│ daisy/     │  │ sim/ + sim_src/│  │ scripts/realtime_effect  │
└──────────┘  └──────────────┘  └─────────────────────────┘
```

### 1.3 動作モード

| モード | 入出力 | 用途 |
|--------|--------|------|
| Daisy Seed 実機 | モノラル入力 → ステレオ出力 (48kHz) | 本番デプロイ |
| デスクトップシミュレータ | WAVファイル → pyaudio 出力 | 開発・デバッグ (tkinter GUI) |
| ブラウザプレビュー | WAVファイル → Web Audio API | WSL2環境でのリアルタイム試聴 |
| オフライン処理 | WAVファイル → WAVファイル | バッチ処理 (純Python) |

---

## 2. 信号処理アーキテクチャ

### 2.1 信号フロー

```
Guitar (mono) ──→ [Delay] ──→ [Reverb] ──→ Stereo Out (L/R)
                  (1→1)        (1→2)
```

- **入力**: モノラル 48kHz
- **出力**: ステレオ 48kHz
- **ブロックサイズ**: 48サンプル (Daisy)、256サンプル (シミュレータ)

### 2.2 EffectorBoard モジュールシステム

エフェクターはコンポーネント単位でモジュール化されている。

**エフェクターボード定義** (`src/effector_board.dsp`):
```faust
delay  = component("effectors/delay/delay.dsp");
reverb = component("effectors/reverb/hall_reverb.dsp");
process = _ : delay : reverb;
```

- `component()` で各エフェクターを独立 DSP ファイルからインポート
- パスはインポート元ファイルからの相対パス
- チェーン変更は `effector_board.dsp` の編集のみで完結
- エフェクターの差し替え・追加・削除・並び替えが容易

---

## 3. エフェクター仕様

### 3.1 Delay 系 (mono → mono)

#### 3.1.1 Digital Delay (`src/effectors/delay/delay.dsp`)

クリアで明瞭なデジタルディレイ。

| パラメータ | パス | デフォルト | 範囲 | 単位 |
|-----------|------|-----------|------|------|
| Time | `v:Delay/[01]Time` | 300 | 10 – 1000 | ms |
| Feedback | `v:Delay/[02]Feedback` | 0.5 | 0.0 – 0.95 | — |
| Mix | `v:Delay/[03]Mix` | 0.4 | 0.0 – 1.0 | — |

**アルゴリズム**:
- ディレイバッファ長: `delay_time * SR / 1000` サンプル (最大1秒 = SR サンプル)
- フィードバックループ: `echo = +~(de.delay(SR, delay_n) * feedback)`
- Wet/Dry ブレンド: `echo * mix + dry * (1 - mix)` をモノラル加算

#### 3.1.2 Analog Delay (`src/effectors/delay/analog_delay.dsp`)

テープ/アナログ回路をシミュレートしたウォームなディレイ。

| パラメータ | パス | デフォルト | 範囲 | 単位 |
|-----------|------|-----------|------|------|
| Time | `v:Analog Delay/[01]Time` | 350 | 10 – 1000 | ms |
| Feedback | `v:Analog Delay/[02]Feedback` | 0.5 | 0.0 – 0.95 | — |
| Mix | `v:Analog Delay/[03]Mix` | 0.4 | 0.0 – 1.0 | — |
| Tone | `v:Analog Delay/[04]Tone` | 0.5 | 0.0 – 1.0 | — |

**アルゴリズム**:
- **LPF (テープヘッド特性)**: 1次ローパスフィルタ。カットオフ = `500 + Tone * 6000` Hz (500Hz ~ 6500Hz)
- **ソフトクリップ (飽和歪み)**: `tanh(x * 1.8) / 1.8` — フィードバック蓄積時に自然な歪みを付加
- フィードバック経路: `delay → LPF → ソフトクリップ → * feedback`

#### 3.1.3 Echo Delay (`src/effectors/delay/echo_delay.dsp`)

付点音符風の2タップ・エコー。

| パラメータ | パス | デフォルト | 範囲 | 単位 |
|-----------|------|-----------|------|------|
| Time | `v:Echo/[01]Time` | 220 | 10 – 800 | ms |
| Decay | `v:Echo/[02]Decay` | 0.6 | 0.0 – 0.95 | — |
| Mix | `v:Echo/[03]Mix` | 0.4 | 0.0 – 1.0 | — |

**アルゴリズム**:
- **Tap 1**: `delay_time` ms — フィードバックループ付き（主エコー）
- **Tap 2**: `delay_time × 1.5` ms — 減衰レベル `decay * 0.6`（ドット付き音符風のリズム感）
- 3信号をミックス: `tap1 * mix + tap2 * mix * 0.7 + dry * (1 - mix)`

### 3.2 Reverb 系 (mono → stereo)

#### 3.2.1 Hall Reverb (`src/effectors/reverb/hall_reverb.dsp`)

Zita Rev1 ベースの大きなホールリバーブ。長い残響と広がりのある空間感。

| パラメータ | パス | デフォルト | 範囲 | 単位 |
|-----------|------|-----------|------|------|
| Room | `v:Hall Reverb/[01]Room` | 0.7 | 0.0 – 1.0 | — |
| Damping | `v:Hall Reverb/[02]Damping` | 0.5 | 0.0 – 1.0 | — |
| Mix | `v:Hall Reverb/[03]Mix` | 0.3 | 0.0 – 1.0 | — |

**アルゴリズム**:
- **Zita Rev1 Stereo** (`re.zita_rev1_stereo`): アルゴリズミック・リバーブ
  - 初期遅延 (rdel): 20 ms
  - 低域クロスオーバー (f1): 200 Hz
  - 高域減衰 (damp_hz): `7000 - Damping * 5500` Hz (1500Hz ~ 7000Hz)
  - 低域残響時間 (t60dc): `1.0 + Room * 7.0` 秒 (1.0s ~ 8.0s)
  - 中域残響時間 (t60m): `0.5 + Room * 5.5` 秒 (0.5s ~ 6.0s)
  - 基準サンプルレート: 48000 Hz
- **mono→stereo 変換**: `zita2 = _ <: (_, _) : zita` (分岐してステレオリバーブへ)
- **Wet/Dry ミックス**: `route(4,4,...)` でステレオ Wet と Dry を整列し、各チャンネルでブレンド

#### 3.2.2 Room Reverb (`src/effectors/reverb/room_reverb.dsp`)

Zita Rev1 ベースの小部屋リバーブ。短い残響と自然な空間感。

| パラメータ | パス | デフォルト | 範囲 | 単位 |
|-----------|------|-----------|------|------|
| Room | `v:Room Reverb/[01]Room` | 0.4 | 0.0 – 1.0 | — |
| Damping | `v:Room Reverb/[02]Damping` | 0.6 | 0.0 – 1.0 | — |
| Mix | `v:Room Reverb/[03]Mix` | 0.25 | 0.0 – 1.0 | — |

**アルゴリズム**:
- Hall Reverb と同じ Zita Rev1 ベースだが、パラメータレンジが異なる:
  - 初期遅延: **5 ms** (ホールの20msより短い初期反射)
  - t60dc: `0.5 + Room * 1.5` 秒 (0.5s ~ 2.0s) — ホールの1/4以下
  - t60m: `0.3 + Room * 1.2` 秒 (0.3s ~ 1.5s)
  - damp_hz: `5000 - Damping * 3000` Hz (2000Hz ~ 5000Hz)

#### 3.2.3 Shimmer Reverb (`src/effectors/reverb/shimmer.dsp`)

ホールリバーブ + オクターブ上の倍音によるシマーエフェクト。

| パラメータ | パス | デフォルト | 範囲 | 単位 |
|-----------|------|-----------|------|------|
| Room | `v:Shimmer/[01]Room` | 0.9 | 0.0 – 1.0 | — |
| Damping | `v:Shimmer/[02]Damping` | 0.3 | 0.0 – 1.0 | — |
| Mix | `v:Shimmer/[03]Mix` | 0.5 | 0.0 – 1.0 | — |
| Amount | `v:Shimmer/[04]Amount` | 0.6 | 0.0 – 0.9 | — |

**アルゴリズム**:
- **ピッチシフト**: `ef.transpose(4096, 256, 12.0, x)` — OLA方式で+12半音(1オクターブ上)
  - ウィンドウサイズ: 4096 サンプル
  - ホップサイズ: 256 サンプル
  - シフト量: 12.0 半音
- **信号フロー**: `入力 → (dry + pitch_up * shimmer_amt) → Zita Rev1 → stereo`
- ピッチシフト成分をドライ信号に加算してからリバーブに送ることで、キラキラとした幻想的な持続音を生成

---

## 4. パラメータ設定

### 4.1 パラメータ定義 (`params/default.json`)

| # | JSON キー | ラベル | デフォルト | 範囲 | 単位 | Daisy ハードウェア |
|---|-----------|--------|-----------|------|------|--------------------|
| 1 | delay_time | Delay Time | 300 | 10 – 1000 | ms | knob1 (ADC0/pin15) |
| 2 | delay_feedback | Delay Feedback | 0.5 | 0.0 – 0.95 | — | knob2 (ADC1/pin16) |
| 3 | delay_mix | Delay Mix | 0.4 | 0.0 – 1.0 | — | knob3 (ADC2/pin17) |
| 4 | reverb_room | Reverb Room | 0.7 | 0.0 – 1.0 | — | knob4 (ADC3/pin18) |
| 5 | reverb_damp | Reverb Damping | 0.5 | 0.0 – 1.0 | — | knob5 (ADC4/pin19) |
| 6 | reverb_mix | Reverb Mix | 0.3 | 0.0 – 1.0 | — | knob6 (ADC5/pin20) |
| 7 | shimmer | Shimmer | 0.0 | 0.0 – 0.9 | — | knob7 |

### 4.2 パラメータパスマッチング

JSON 設定のパス (例: `/delay_reverb/Delay/Time`) と Faust 生成パス (例: `/effector_board/Delay/Time`) は
DSP ファイル名によって接頭辞が異なるため、**サフィックスマッチング** (`Delay/Time` 部分) で自動対応する。

```python
# sim/main.py: _match_param_path()
suffix = "/".join(json_path.strip("/").split("/")[1:])  # "Delay/Time"
```

フォールバック: 末尾コンポーネント (`Time`) のみの一致も試行。

### 4.3 オーディオ設定

| 項目 | 値 |
|------|-----|
| サンプルレート | 48000 Hz |
| ブロックサイズ (Daisy) | 48 サンプル |
| ブロックサイズ (シミュレータ) | 256 サンプル |
| 入力チャンネル数 | 1 (モノラル) |
| 出力チャンネル数 | 2 (ステレオ) |

---

## 5. Daisy Seed 実機ビルド

### 5.1 ハードウェア構成

- **マイコン**: Daisy Seed (STM32H750, ARM Cortex-M7)
- **メモリ**: FLASH 128KB / SRAM 512KB / **SDRAM 64MB** (外付け)
- **ADC**: 6チャンネル (ADC0-5 → pin 15-20) — ポテンショメータ接続
- **オーディオコーデック**: 内蔵 (48kHz, 24-bit)

### 5.2 メモリ配置

```cpp
static mydsp DSY_SDRAM_BSS dsp;  // SDRAM に配置 (必須)
```

ディレイバッファ(最大1秒 = 192KB) + リバーブバッファ が 512KB SRAM を超過するため、
SDRAM 上に mydsp インスタンスを配置する。

- 実測メモリ使用量: FLASH 118KB/128KB, SRAM 15KB/512KB, **SDRAM 1.8MB/64MB**

### 5.3 ソフトウェア構成 (`daisy/main.cpp`)

```
main()
  ├─ hw.Configure() / Init()
  ├─ hw.SetAudioBlockSize(48)
  ├─ ADC 初期化 (6ch, pin 15-20)
  ├─ dsp.init(sampleRate)
  ├─ dsp.buildUserInterface(&ui)  // MapUI でパラメータマップ構築
  └─ hw.StartAudio(AudioCallback)

AudioCallback(in, out, size)
  ├─ knobs[0..5] = hw.adc.GetFloat(k)  // ADC → 0.0-1.0
  ├─ ui.setParamValue(path, scaledValue)  // MapUI でパラメータ設定
  └─ dsp.compute(size, inputs, outputs)   // Faust DSP 処理
```

### 5.4 ノブ→パラメータ変換 (ADC スケーリング)

| ノブ | ADC 値 (0-1) | パラメータ変換式 |
|------|------------|-----------------|
| Knob1 | knobs[0] | Delay Time = `10 + knobs[0] * 990` ms |
| Knob2 | knobs[1] | Delay Feedback = `knobs[1] * 0.95` |
| Knob3 | knobs[2] | Delay Mix = `knobs[2]` (そのまま) |
| Knob4 | knobs[3] | Room = `knobs[3]` (そのまま) |
| Knob5 | knobs[4] | Damping = `knobs[4]` (そのまま) |
| Knob6 | knobs[5] | Mix = `knobs[5]` (そのまま) |

### 5.5 ビルドチェーン

```
make daisy
  ├─ make gen-daisy (Faust → C++ ヘッダ生成)
  │    ├─ faust -lang cpp → gen/effector_board.h
  │    └─ Faust ランタイムヘッダ → gen/faust/ にコピー
  └─ make -C daisy all (ARM クロスコンパイル)
       ├─ gcc-arm-none-eabi (13.2.1)
       ├─ libdaisy (~/daisy/libdaisy)
       └─ DaisySP (~/daisy/DaisySP)
```

### 5.6 フラッシュ書き込み

```bash
cd daisy && make program-dfu   # USB DFU モードで書き込み
```

---

## 6. デスクトップシミュレータ

### 6.1 アーキテクチャ

```
┌──────────────────────────────────────────────────────────┐
│  Python (tkinter GUI)                                      │
│  sim/main.py → DaisySimulator クラス                       │
│    ├─ OledWidget  (128x64 OLED 4倍表示)                    │
│    ├─ KnobWidget × 7  (ドラッグ/スクロール操作)              │
│    ├─ ToggleSwitch (BYPASS)                                │
│    └─ MomentaryButton (PAGE)                               │
└──────────┬───────────────────────────────────────────────┘
           │ ctypes
           ▼
┌──────────────────────────────────────────────────────────┐
│  C++ 共有ライブラリ (gen/sim_engine.so)                     │
│  sim_src/faust_api.cpp                                     │
│    ├─ mydsp (Faust 生成 DSP エンジン)                       │
│    ├─ MapUI (パラメータマップ)                               │
│    └─ OLED フレームバッファ (1024 bytes)                     │
└──────────────────────────────────────────────────────────┘
```

### 6.2 C API (`sim_src/faust_api.h`)

```c
// ライフサイクル
faust_handle_t faust_create(void);
void           faust_destroy(faust_handle_t h);
void           faust_init(faust_handle_t h, int sample_rate);

// DSP 情報
int  faust_get_num_inputs(faust_handle_t h);   // → 1
int  faust_get_num_outputs(faust_handle_t h);  // → 2

// パラメータアクセス
int         faust_get_params_count(faust_handle_t h);
const char* faust_get_param_address(faust_handle_t h, int index);
void        faust_set_param(faust_handle_t h, const char* path, float value);
float       faust_get_param(faust_handle_t h, const char* path);

// オーディオ処理
void faust_compute(faust_handle_t h, int count, float** inputs, float** outputs);

// OLED (SSD1306 互換: 128x64, 1bpp, 8ページ × 128列)
const unsigned char* faust_oled_get_framebuf(faust_handle_t h);
void faust_oled_clear(faust_handle_t h);
void faust_oled_set_pixel(faust_handle_t h, int x, int y, int on);
void faust_oled_draw_text(faust_handle_t h, int x, int y, const char* text, int font_size);
void faust_oled_update(faust_handle_t h);
```

### 6.3 OLED 表示仕様

- **解像度**: 128 × 64 ピクセル (1bpp モノクロ)
- **バッファフォーマット**: SSD1306 互換 — 8ページ × 128列 = 1024 bytes
  - ページ = y / 8, ビット = y % 8, インデックス = page * 128 + x
- **フォント**: 5×7 ビットマップフォント (`sim_src/oled_font5x7.h`)
  - font_size=0: 1倍 (5×7px), font_size=1: 2倍 (10×14px)
- **表示更新**: 15 FPS (66ms 間隔)

#### OLED 画面レイアウト (2ページ構成)

**Page 1: DELAY**
```
┌────────────────────────────────────┐
│ DELAY              (大文字 2倍)     │
│ ──────────────────────────────────  │
│ TIME:  300ms        ████████░░░░  │
│ FDBK:  0.50         ██████░░░░░░  │
│ MIX:   0.40         █████░░░░░░░  │
│                      ●  ○         │
└────────────────────────────────────┘
```

**Page 2: REVERB**
```
┌────────────────────────────────────┐
│ REVERB             (大文字 2倍)     │
│ ──────────────────────────────────  │
│ ROOM:  0.70         █████████░░░  │
│ DAMP:  0.50         ██████░░░░░░  │
│ MIX:   0.30         ████░░░░░░░░  │
│ SHIMM: 0.00         ░░░░░░░░░░░░  │
│                      ○  ●         │
└────────────────────────────────────┘
```

- パラメータ名 + 値 (テキスト) + ミニバーグラフ (x=80 ~ x=124, 幅44px)
- ページインジケータ (●=現在 / ○=他ページ) を最下部中央に表示

### 6.4 GUI ウィジェット仕様

#### KnobWidget (`sim/widgets/knob_widget.py`)
- **サイズ**: 70×70 px
- **操作**: 上ドラッグ=増加 / 下ドラッグ=減少 / ダブルクリック=デフォルトリセット / マウスホイール=微調整
- **感度**: ドラッグ 150px で全範囲
- **表示**: 225° ~ -45° (270° の弧)、ポインターライン、値テキスト
- **カラー**: Delay 系=`#e8a735` (金), Reverb 系=`#35a8e8` (青), Shimmer=`#b065e8` (紫)

#### OledWidget (`sim/widgets/oled_widget.py`)
- **サイズ**: 512 × 256 px (128×64 の 4倍スケール)
- **色**: ON=`#00FF88` (緑), OFF=`#080808` (黒に近い灰)
- **更新方式**: PhotoImage.put() による一括描画

#### ToggleSwitch (`sim/widgets/switch_widget.py`)
- **用途**: BYPASS スイッチ (クリックでトグル)
- **表示**: LED インジケータ (ON=`#00ff44`, OFF=`#330000`)

#### MomentaryButton (`sim/widgets/switch_widget.py`)
- **用途**: PAGE ボタン (OLED 表示ページ切り替え)
- **動作**: 押下時にイベント発火、離すと元に戻る

### 6.5 オーディオ I/O (`sim/audio_io.py`)

- **ライブラリ**: pyaudio
- **フォーマット**: Float32, 48kHz, 2ch 出力
- **ブロックサイズ**: 256 サンプル
- **入力ソース**: WAV ファイルをループ再生 (`gen/guitar_clean.wav`)
- **バイパスモード**: DSP 処理をスキップし入力をそのまま出力

---

## 7. HAL (Hardware Abstraction Layer)

### 7.1 インターフェース (`hal/hal.h`)

実機とシミュレータで共通のインターフェースを提供する抽象基底クラス。

```cpp
class Hal {
public:
    // Audio
    virtual int   getSampleRate() const = 0;
    virtual int   getBlockSize()  const = 0;

    // Knobs (ADC, 0.0–1.0)
    virtual float getKnob(int index)    const = 0;
    virtual int   getNumKnobs()         const = 0;   // → 7

    // Switches
    virtual bool  getSwitch(int index)  const = 0;
    virtual int   getNumSwitches()      const = 0;   // → 1

    // OLED (SSD1306: 128x64)
    virtual uint8_t* getOledBuffer()                                    = 0;
    virtual void oledClear()                                            = 0;
    virtual void oledSetPixel(int x, int y, bool on)                    = 0;
    virtual void oledDrawText(int x, int y, const char* text, int size) = 0;
    virtual void oledUpdate()                                           = 0;
};
```

### 7.2 実装

| クラス | ファイル | 用途 |
|--------|---------|------|
| `HalDaisy` | `hal/hal_daisy.h` | Daisy Seed 実機。`daisy::DaisySeed` をラップ |
| `HalSim` | `hal/hal_sim.h` | シミュレータ。knob/switch 値を外部から設定可能 |

**HalSim の特徴**:
- `setKnob(i, v)` / `setSwitch(i, v)` で Python 側から値を注入
- OLED バッファは Python 側から直接読み取り (update は no-op)
- knobs 配列サイズ: 8, switches 配列サイズ: 4

---

## 8. ブラウザプレビュー

### 8.1 概要 (`scripts/realtime_effect.py`)

WSL2 環境では ALSA が利用できないため、ブラウザの Web Audio API でリアルタイム処理を実現。

```
Python HTTP サーバー (localhost:8765)
  ├─ GET /        → HTML (シングルページアプリ)
  ├─ GET /audio   → WAV ファイル配信
  └─ POST /stop   → サーバー停止
```

### 8.2 UI 構成

ペダルボードを模した視覚的な UI:
- **ヘッダー**: PLAY / STOP ボタン、SPLIT ボタン (並列チェーン)、CLEAR ボタン
- **ボード**: IN → [エフェクター群] → OUT のチェーン表示
- **パレット**: 6種のエフェクターをクリック/ドラッグして配置
- **並列モード**: SPLIT で2系統の並列チェーン + MIX コントロール

### 8.3 エフェクター実装 (JavaScript)

ブラウザ側でPython/Faustとは独立に DSP を JavaScript で再実装:

| エフェクター | キー | 実装概要 |
|-------------|------|---------|
| Digital Delay | `digital_delay` | フィードバックディレイバッファ |
| Analog Delay | `analog_delay` | LPF (1次RC) + `tanh` サチュレーション |
| Echo Delay | `echo_delay` | 2タップ (×1.0 + ×1.5) ディレイ |
| Hall Reverb | `hall_reverb` | Freeverb (8 コムフィルタ + 4 オールパス) |
| Room Reverb | `room_reverb` | Freeverb (短いディレイ時間) |
| Shimmer | `shimmer` | OLA ピッチシフター + Freeverb |

### 8.4 Freeverb 実装詳細

```javascript
// 8つのコムフィルタ (44100Hz 基準のディレイ長、SRでスケーリング)
comb_delays = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617]
// L/R にステレオスプレッド (SPREAD=23 サンプル)
// 4つの直列オールパスフィルタ
allpass_delays = [225, 556, 441, 341]  // フィードバック = 0.5
```

- 入力ゲイン: 0.015
- フィードバック係数: `0.70 + room * 0.28` (Hall) / `0.60 + room * 0.28` (Room)
- ダンピング係数: `damp * 0.40`

### 8.5 OLA ピッチシフター実装

```javascript
function makePitcher(SR) {
  // 2つのグレイン (位相オフセット 0 / 0.5)
  // グレインサイズ: 2048 サンプル
  // バッファサイズ: 2048 * 8 サンプル (リングバッファ)
  // ハニングウィンドウによるクロスフェード
}
```

### 8.6 ドラッグ＆ドロップ

- パレットからペダルをボードにドラッグして配置
- ボード上のペダルをドラッグして並び替え
- ゴーストプレビュー表示
- タッチイベント対応 (モバイルブラウザ)
- ESC キーでキャンセル

---

## 9. オフライン処理

### 9.1 Faust コンパイル済みバイナリ

```bash
faust2sndfile src/effector_board.dsp   # → src/effector_board バイナリ
./src/effector_board input.wav output.wav
```

### 9.2 純Python 処理 (`scripts/apply_effect.py`)

外部依存なし (標準ライブラリのみ) のオフライン処理スクリプト。

```bash
python3 scripts/apply_effect.py [input.wav] [output.wav]
```

- **入力**: WAV (16-bit/24-bit, モノラル/ステレオ → モノラル抽出)
- **出力**: WAV (16-bit ステレオ)
- **エフェクト**: Delay + Freeverb (Faust 版と同等のアルゴリズム)

**Freeverb 実装 (Python)**:
- 8 並列コムフィルタ (L/R 各8、ステレオスプレッド SPREAD=23)
- 4 直列オールパスフィルタ (L/R 独立)
- 進捗表示: 5% 刻み

---

## 10. ビルドシステム

### 10.1 Makefile ターゲット一覧

| ターゲット | 説明 | コマンド例 |
|-----------|------|-----------|
| `check` | effector_board.dsp 構文チェック | `make check` |
| `check-all` | 全エフェクター + ボード 一括チェック | `make check-all` |
| `gen` | Daisy Seed 向け C++ 生成 (minimal arch) | `make gen` |
| `gen-daisy` | bare C++ ヘッダ + ランタイムヘッダ生成 | `make gen-daisy` |
| `header` | 自己完結型 C++ ヘッダ生成 | `make header` |
| `diagram` | SVG ブロック図生成 | `make diagram` |
| `params` | パラメータ一覧表示 | `make params` |
| `sim` | シミュレータ起動 (.so ビルド + GUI) | `make sim` |
| `sim-lib` | 共有ライブラリのみビルド | `make sim-lib` |
| `sim-gen` | Faust bare C++ 生成 (シミュレータ用) | `make sim-gen` |
| `daisy` | Daisy Seed 実機ビルド | `make daisy` |
| `clean` | gen/ ディレクトリ削除 | `make clean` |
| `archs` | 利用可能アーキテクチャ一覧 | `make archs` |

### 10.2 個別エフェクターチェック

```bash
make TARGET=effectors/delay/delay check
make TARGET=effectors/delay/analog_delay check
make TARGET=effectors/reverb/room_reverb check
```

### 10.3 シミュレータビルドフロー

```
make sim
  ├─ sim-lib ─┬─ sim-gen: faust -lang cpp → gen/effector_board_bare.cpp
  │            └─ g++ -shared -fPIC -O2 -std=c++17
  │                 sim_src/faust_api.cpp → gen/sim_engine.so
  └─ python3 -m sim.main (tkinter GUI 起動)
```

### 10.4 Daisy ビルドフロー

```
make daisy
  ├─ gen-daisy: faust → gen/effector_board.h
  │             cp faust/runtime headers → gen/faust/
  └─ make -C daisy all
       └─ libdaisy Makefile (ARM cross-compile)
```

---

## 11. ファイル構成

```
dsp_faust_sample/
├── src/
│   ├── effector_board.dsp          ★ エフェクターチェーン定義 (メインDSP)
│   └── effectors/
│       ├── delay/
│       │   ├── delay.dsp           デジタルディレイ (mono→mono)
│       │   ├── analog_delay.dsp    アナログディレイ (mono→mono)
│       │   └── echo_delay.dsp      2タップ・エコー (mono→mono)
│       └── reverb/
│           ├── hall_reverb.dsp     ホールリバーブ (mono→stereo)
│           ├── room_reverb.dsp     ルームリバーブ (mono→stereo)
│           └── shimmer.dsp         シマーリバーブ (mono→stereo)
├── params/
│   └── default.json                パラメータ定義 + Daisy マッピング
├── daisy/
│   ├── main.cpp                    Daisy Seed オーディオコールバック
│   └── Makefile                    ARM クロスコンパイル
├── sim/                            デスクトップシミュレータ (Python)
│   ├── __init__.py
│   ├── main.py                     DaisySimulator メインクラス
│   ├── faust_engine.py             ctypes ラッパー (sim_engine.so)
│   ├── audio_io.py                 pyaudio I/O
│   ├── oled_renderer.py            OLED 画面描画ロジック
│   └── widgets/
│       ├── __init__.py
│       ├── knob_widget.py          回転ノブ UI
│       ├── oled_widget.py          OLED ディスプレイ UI
│       └── switch_widget.py        トグル/モーメンタリスイッチ UI
├── sim_src/                        シミュレータ C++ ソース
│   ├── faust_api.h                 C API ヘッダ
│   ├── faust_api.cpp               C API 実装 (DSP + OLED)
│   └── oled_font5x7.h             5×7 ビットマップフォント
├── hal/                            ハードウェア抽象化層
│   ├── hal.h                       抽象基底クラス
│   ├── hal_daisy.h                 Daisy Seed 実機実装
│   └── hal_sim.h                   シミュレータ実装
├── scripts/
│   ├── apply_effect.py             オフライン WAV 処理 (純Python)
│   ├── realtime_effect.py          ブラウザリアルタイムプレビュー
│   ├── gen_daisy.sh                faust2daisy ラッパー
│   └── print_params.py             パラメータ一覧表示
├── archive/                        旧来の参照用ファイル
│   ├── delay_reverb.dsp            一体型 (Delay+Reverb+Shimmer)
│   ├── delay_only.dsp              ディレイ単体テスト用
│   └── reverb_only.dsp             リバーブ単体テスト用
├── gen/                            生成ファイル (gitignore 済み)
│   ├── effector_board.h            Faust 生成 C++ ヘッダ
│   ├── effector_board.cpp          Faust 生成 C++ (arch付き)
│   ├── effector_board_bare.cpp     Faust 生成 C++ (bare)
│   ├── sim_engine.so               シミュレータ共有ライブラリ
│   ├── guitar_clean.wav            入力テスト音源 (48kHz mono)
│   └── faust/                      Faust ランタイムヘッダ (コピー)
├── .vscode/
│   ├── settings.json               Faust 関連 VSCode 設定
│   ├── extensions.json             推奨拡張機能
│   └── tasks.json                  ビルドタスク (6タスク)
├── Makefile                        トップレベル Makefile
├── setup.sh                        環境セットアップスクリプト
├── README.md                       開発環境まとめ
└── .gitignore
```

---

## 12. 開発環境

### 12.1 必須ソフトウェア

| ソフトウェア | バージョン | 用途 |
|-------------|-----------|------|
| Faust | 2.70.3 | DSP コンパイラ |
| GCC (x86) | — | sim_engine.so ビルド |
| Python 3 | — | シミュレータ / スクリプト |
| pyaudio | — | シミュレータ音声出力 |

### 12.2 Daisy Seed ビルド追加

| ソフトウェア | バージョン | 用途 |
|-------------|-----------|------|
| gcc-arm-none-eabi | 13.2.1 | ARM クロスコンパイラ |
| dfu-util | 0.11 | USB DFU 書き込み |
| libdaisy | — | Daisy SDK |
| DaisySP | — | Daisy DSP ライブラリ |

### 12.3 セットアップ

```bash
bash setup.sh   # Faust + VSCode 拡張インストール
```

---

## 13. 既知の制約・注意事項

### 13.1 Faust v2.70.3 バグ

`(_ , _) : zita` が `<:` 式の内部で型推論に失敗する。

```faust
// NG: <: コンテキスト内での直接使用
zita2 = _ <: ((_ , _) : zita , ...);

// OK: 事前にラッパーを定義
zita2 = _ <: (_, _) : zita;
```

### 13.2 Shimmer パラメータ上限

Shimmer Amount の最大値は **0.9** に制限。1.0 にするとフィードバック発散のリスクがあるため。

### 13.3 WSL2 制約

- ALSA 未サポート → pyaudio はホスト側の PulseAudio 転送が必要
- ブラウザプレビュー (`realtime_effect.py`) で代替可能

### 13.4 Daisy Seed SDRAM 必須

mydsp インスタンスは `DSY_SDRAM_BSS` 属性で SDRAM に配置が必須。
内蔵 SRAM (512KB) ではディレイ/リバーブバッファが収まらない。

---

## 14. VSCode タスク

| タスク | キーバインド | 説明 |
|--------|------------|------|
| Faust: Check Syntax | — | 現在のファイルの構文チェック |
| Faust: Generate C++ | — | 現在のファイルから C++ 生成 |
| Faust: Generate C++ for Daisy Seed | — | Daisy Seed 向け C++ 生成 |
| Faust: Generate Diagram | — | SVG ブロック図生成 |
| Faust: Check + Generate C++ | Ctrl+Shift+B (デフォルト) | チェック→生成の連続実行 |
| Show Parameters | — | パラメータ一覧表示 |
