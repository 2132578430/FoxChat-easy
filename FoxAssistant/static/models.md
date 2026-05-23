# 语音模型下载说明

运行前需下载以下模型文件到 `static/` 目录。

## 1. VAD 模型（语音活动检测）

**文件**: `silero_vad.onnx` (~1.8MB)

**下载地址**:
- https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx
- 或从 sherpa-onnx releases: https://github.com/k2-fsa/sherpa-onnx/releases

## 2. SenseVoice 识别模型（命令识别）

**文件**: `model.int8.onnx` (~227MB) + `tokens.txt`

**下载地址**:
- https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sensevoice-zh-en-ja-ko-yue-2024-07-17.tar.bz2
- 解压后取 `model.int8.onnx` 和 `tokens.txt` 放到 `static/` 目录

## 3. KWS 唤醒词模型（"你好狐狸"）

**目录**: `sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20/` (~39MB)

**下载地址**:
- https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20.tar.bz2
- 解压后整个目录放到 `static/` 下
- 包含文件: encoder-epoch-13-avg-2-chunk-16-left-64.int8.onnx, decoder-epoch-13-avg-2-chunk-16-left-64.onnx, joiner-epoch-13-avg-2-chunk-16-left-64.int8.onnx, tokens.txt, keywords.txt

---

## 快速下载脚本（Windows PowerShell）

```powershell
# 进入 static 目录
cd FoxAssistant/static

# 下载 VAD
Invoke-WebRequest -Uri "https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx" -OutFile "silero_vad.onnx"

# 下载 SenseVoice
Invoke-WebRequest -Uri "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sensevoice-zh-en-ja-ko-yue-2024-07-17.tar.bz2" -OutFile "sensevoice.tar.bz2"
tar -xjf sensevoice.tar.bz2
move sherpa-onnx-sensevoice-zh-en-ja-ko-yue-2024-07-17/model.int8.onnx .
move sherpa-onnx-sensevoice-zh-en-ja-ko-yue-2024-07-17/tokens.txt .
rm sensevoice.tar.bz2
rm -r sherpa-onnx-sensevoice-zh-en-ja-ko-yue-2024-07-17

# 下载 KWS
Invoke-WebRequest -Uri "https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20.tar.bz2" -OutFile "kws.tar.bz2"
tar -xjf kws.tar.bz2
rm kws.tar.bz2
```