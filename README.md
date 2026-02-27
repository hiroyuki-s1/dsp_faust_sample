# Guitar Effects — Faust + Daisy Seed

ギター用エフェクター（Delay + Hall Reverb）のプロトタイプ環境。
FAUST でDSPを記述し、Daisy Seed 向け C++ にエクスポートする。

## エフェクト構成

```
ギター (mono) → [Delay] → [Hall Reverb] → ステレオ出力
```

| エフェクト | アルゴリズム | I/O |
|---|---|---|
| Delay | フィードバック遅延線 (`de.delay`) | mono → mono |
| Hall Reverb | Zita Rev1 (`re.zita_rev1_stereo`) | mono → stereo |

## パラメータ (7個)

| # | 名前 | デフォルト | 範囲 | Daisy Seed |
|---|---|---|---|---|
| 1 | Delay Time | 300 ms | 10〜1000 ms | knob1 (ADC15) |
| 2 | Delay Feedback | 0.50 | 0.0〜0.95 | knob2 (ADC16) |
| 3 | Delay Mix | 0.40 | 0.0〜1.0 | knob3 (ADC17) |
| 4 | Reverb Room | 0.70 | 0.0〜1.0 | knob4 (ADC18) |
| 5 | Reverb Damping | 0.50 | 0.0〜1.0 | knob5 (ADC19) |
| 6 | Reverb Mix | 0.30 | 0.0〜1.0 | knob6 (ADC20) |
| 7 | Shimmer | 0.00 | 0.0〜0.9 | knob7 |

---

## EffectorBoard — モジュール構成

エフェクターを独立した `.dsp` ファイルに分割。`effector_board.dsp` が直列チェーンを定義。

```
dsp/
  effector_board.dsp    ★ ボード（エフェクターの並び定義）
  effectors/
    delay.dsp           ディレイ (mono→mono)
    reverb.dsp          ホールリバーブ+シマー (mono→stereo)
  delay_reverb.dsp      旧来の一体型（参照用）
  delay_only.dsp        ディレイ単体テスト用
  reverb_only.dsp       リバーブ単体テスト用

params/
  default.json          パラメータ定義 + Daisy ハードウェアマッピング

daisy/
  main.cpp              Daisy Seed オーディオコールバック
  Makefile              ARM クロスコンパイル用

scripts/
  apply_effect.py       オフライン処理（純Python、依存なし）
  realtime_effect.py    リアルタイムプレビュー（ブラウザ Web Audio API）
  gen_daisy.sh          faust2daisy ラッパー
  print_params.py       パラメータ一覧表示

gen/                    生成ファイル（gitignore 済み）
  guitar_clean.wav      テスト用ギター音源 (CC0, 48kHz mono, 26s)
  guitar_delay_reverb.wav  Faust生成 エフェクト済み (stereo)
```

---

## 開発環境

| ツール | バージョン | 用途 |
|---|---|---|
| FAUST | 2.70.3 | DSPコンパイラ |
| faust2sndfile | 同上 | WAVファイル処理バイナリ生成 |
| Python | 3.12 | オフライン処理・リアルタイムUI |
| WSL2 / Ubuntu | 22.04 | 実行環境 |
| VSCode | — | エディタ |

**インストール済みパッケージ:**
```bash
sudo apt install faust faust-common libsndfile1-dev libmp3lame-dev python3-tk pulseaudio-utils
```

**VSCode 拡張:**
- `glen-anderson.vscode-faust` — 構文ハイライト・エラーチェック
- `sukumo28.wav-preview` — WAVファイルプレビュー
- `ms-vscode.cpptools` — C++ サポート
- `ms-vscode.makefile-tools` — Makefile サポート

---

## 使い方

### 1. DSP 構文チェック

```bash
faust dsp/delay_reverb.dsp -o /dev/null
```

### 2. オーディオファイル処理（Faust バイナリ）

```bash
# バイナリをビルド
faust2sndfile dsp/delay_reverb.dsp      # → dsp/delay_reverb

# 処理実行
./dsp/delay_reverb gen/guitar_clean.wav gen/guitar_effected.wav
```

### 3. オフライン処理（Python）

```bash
python3 scripts/apply_effect.py [input.wav] [output.wav]
# デフォルト: gen/guitar_clean.wav → gen/guitar_effected.wav
```

### 4. リアルタイムプレビュー（ブラウザ）

```bash
python3 scripts/realtime_effect.py
# → http://localhost:8765 をブラウザで開く
# スライダーでパラメータをリアルタイム調整
```

> WSL2 は ALSA が使えないため、オーディオはブラウザの Web Audio API で処理する。

### 5. Daisy Seed 向け C++ 生成

```bash
make gen
# または
bash scripts/gen_daisy.sh dsp/delay_reverb.dsp
```

---

## Faust DSP 設計メモ

### シグナルフロー

```
_ : delay_proc : rev_proc
```

**delay_proc** (mono → mono):
```
input ─<:─┬─ echo ─ * delay_mix ──:>─ output
           └─ dry  ─ * (1-mix)  ─┘
```

**rev_proc** (mono → stereo):
```
input ─<:─┬─ zita2 ─┬─ wet_L ─┐
           │         └─ wet_R ─┤  route  ┌─ wet_L * mix + dry * (1-mix) → L
           ├─ dry ─────────────┤ ──────► │
           └─ dry ─────────────┘         └─ wet_R * mix + dry * (1-mix) → R
```

### 既知の Faust バグ（v2.70.3）

`<:` 演算子のコンテキスト内で `(_ , _) : zita` と書くと型推論エラーになる。
**回避策**: 別名で mono→stereo ラッパーを定義してから使う。

```faust
// NG: _ <: ((_ , _) : zita , _ , _)  ← エラー

// OK:
zita2 = _ <: (_, _) : zita;
rev_proc = _ <: (zita2 , _ , _) : route(...) : par(...);
```

---

## Daisy Seed フラッシュ手順

```bash
# 前提: DaisyToolchain インストール済み
cd daisy
make        # ARM クロスコンパイル
make program-dfu  # USB DFU でフラッシュ
```

ノブのピン割り当ては `daisy/main.cpp` を参照。
