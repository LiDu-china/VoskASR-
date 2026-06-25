# Vosk 语音识别程序

离线实时中文语音转文字工具，支持多种音频格式识别。

## ✨ 功能特点

- 🎤 **实时语音识别** - 边说边显示文字
- 🎵 **多格式支持** - WAV、MP3、FLAC、OGG、M4A、AAC、WMA
- 📂 **文件批量识别** - 支持多文件同时识别
- 💾 **一键导出** - 识别结果保存为文本文件
- 🔌 **离线使用** - 无需网络，隐私安全
- 🎯 **高精度** - 使用 Vosk 中文模型

## 📦 安装方式

### 方式一：下载精简版安装包（推荐）

> 安装包仅 **186MB**，首次运行自动下载语音模型（约2GB）

**下载地址**：[GitHub Releases](https://github.com/LiDu-china/VoskASR-/releases)

**安装步骤：**

1. 下载 `VoskASR-Lite-Setup-1.0.exe`
2. 双击运行安装
3. 首次启动时，程序会自动下载语音模型
4. 下载完成后即可使用（模型会保存在安装目录）

### 方式二：源码运行（适合开发者）

```bash
# 1. 克隆代码
git clone https://github.com/LiDu-china/VoskASR-.git
cd VoskASR-

# 2. 安装 Python 依赖
pip install vosk pyaudio

# 3. 下载语音模型（约 2GB）
# 访问 https://alphacephei.com/vosk/models
# 下载 vosk-model-cn-0.22
# 解压到 model/ 目录

# 4. 运行程序
python "import tkinter as tk.py"
```

### 方式三：自行打包

```bash
# 安装打包工具
pip install pyinstaller

# 运行打包脚本
build.bat

# 安装 Inno Setup 后编译 setup.iss 生成安装包
```

## 🚀 使用方法

### 实时录音识别
1. 选择音频输入设备（麦克风）
2. 点击「开始录音识别」
3. 对着麦克风说话，文字会实时显示
4. 点击「停止识别」结束

### 文件识别
1. 点击「打开音频文件」
2. 选择一个或多个音频文件（按住 Ctrl 多选）
3. 等待识别完成

### 导出结果
1. 识别完成后，点击「导出文字」
2. 选择保存位置
3. 识别结果保存为 .txt 文件

## 🛠️ 开发环境搭建

如果需要修改源码或自行打包：

### 环境要求
- Python 3.10+
- Windows 10/11

### 安装依赖
```bash
pip install vosk pyaudio
```

### 运行程序
```bash
python "import tkinter as tk.py"
```

### 打包为 exe
```bash
pip install pyinstaller

pyinstaller --name VoskASR \
            --onedir \
            --hidden-import vosk \
            --hidden-import pyaudio \
            --collect-all vosk \
            "import tkinter as tk.py"
```

## 📁 项目结构

```
语音转文本/
├── import tkinter as tk.py  # 主程序
├── setup.iss                # Inno Setup 安装脚本
├── build.bat                # 打包脚本
├── .gitignore               # Git 忽略文件
└── README.md                # 项目说明
```

## 🔧 配置说明

程序会自动检测运行环境：
- **开发环境**：使用绝对路径加载模型
- **打包环境**：使用相对路径加载模型

模型和 FFmpeg 需要放在程序同级目录：
```
程序目录/
├── VoskASR.exe
├── bin/ffmpeg.exe
└── model/vosk-model-cn-0.22/
```

## 📝 依赖组件

| 组件 | 用途 | 大小 |
|------|------|------|
| Vosk | 语音识别引擎 | ~50MB |
| PyAudio | 麦克风录音 | ~1MB |
| FFmpeg | 音频格式转换 | ~100MB |
| Vosk 中文模型 | 识别模型 | ~2GB |

## 🐛 常见问题

### Q: 模型加载失败？
A: 确保 `model/vosk-model-cn-0.22` 目录存在且完整

### Q: 无法录音？
A: 检查麦克风权限是否开启

### Q: 识别不准确？
A: 尝试更清晰地说话，或使用更大的模型

## 📄 许可证

MIT License

## 🔗 相关链接

- [Vosk 官网](https://alphacephei.com/vosk/)
- [Vosk 模型下载](https://alphacephei.com/vosk/models)
- [FFmpeg 官网](https://ffmpeg.org/)
