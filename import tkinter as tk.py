import tkinter as tk
from tkinter import ttk, filedialog
import pyaudio
import json
import threading
import time
import subprocess
import tempfile
import os
import sys
import wave
import urllib.request
import zipfile
from vosk import Model, KaldiRecognizer


def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，从 exe 所在目录查找
        base_path = os.path.dirname(sys.executable)
        return os.path.join(base_path, relative_path)
    else:
        # 开发环境，使用原始绝对路径
        return None  # 由下面的开发环境路径处理


# ========== 配置路径 ==========
if getattr(sys, 'frozen', False):
    # 打包环境
    FFMPEG_PATH = get_resource_path("bin/ffmpeg.exe")
    MODEL_PATH = get_resource_path("model/vosk-model-cn-0.22")
else:
    # 开发环境 - 使用原始绝对路径
    FFMPEG_PATH = "D:/Prom/ffmpeg-8.1.1-essentials_build/bin/ffmpeg.exe"
    MODEL_PATH = "D:/Prom/vosk-model-cn-0.22"

# ========== 1. 定义全局变量（核心新增） ==========
# 用于存储语音识别结束后的完整文本结果
FINAL_RECOGNIZED_TEXT = ""

# 配置项
SAMPLERATE = 16000  # vosk模型要求的采样率
CHUNK = 4000        # 音频块大小（减小提高灵敏度，0.25秒/块）

class VoskRealTimeASR:
    def __init__(self, root):
        self.root = root
        self.root.title("Vosk 离线实时语音转中文文本")
        self.root.geometry("700x450")

        # 核心状态变量
        self.is_running = False
        self.recognizer = None
        self.audio_stream = None

        # ========== 关键修改：调整初始化顺序 ==========
        # 1. 先初始化音频设备（收集设备列表，供GUI使用）
        self.init_audio_device()
        # 2. 再创建GUI（定义status_label、设备下拉框等组件）
        self.create_gui()
        # 3. 最后加载模型（此时status_label已存在）
        self.init_vosk_model()

    def init_vosk_model(self):
        """初始化Vosk中文模型（支持自动下载）"""
        # 检查模型是否存在
        if not os.path.exists(MODEL_PATH):
            print(f"模型不存在，需要下载: {MODEL_PATH}")
            self.status_label.config(text="⏳ 首次运行，正在下载语音模型（约2GB）...", foreground="blue")
            self.root.update()
            # 启动下载线程
            self.download_thread = threading.Thread(target=self.download_model)
            self.download_thread.daemon = True
            self.download_thread.start()
            return

        try:
            print(f"加载模型: {MODEL_PATH}")
            self.model = Model(model_path=MODEL_PATH)
            self.recognizer = KaldiRecognizer(self.model, SAMPLERATE)
            self.recognizer.SetWords(True)
            self.status_label.config(text="✅ Vosk模型加载成功", foreground="green")
        except Exception as e:
            error_msg = f"❌ 模型加载失败：{str(e)}"
            self.status_label.config(text="❌ 模型加载失败", foreground="red")
            print(error_msg)

    def download_model(self):
        """下载 Vosk 中文模型"""
        model_url = "https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip"
        zip_path = os.path.join(os.path.dirname(MODEL_PATH), "vosk-model-cn-0.22.zip")

        try:
            # 创建 model 目录
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

            print(f"开始下载模型: {model_url}")
            print(f"保存到: {zip_path}")

            # 下载文件
            def progress_hook(block_num, block_size, total_size):
                downloaded = block_num * block_size
                if total_size > 0:
                    percent = min(100, downloaded * 100 // total_size)
                    self.root.after(0, lambda p=percent: self.status_label.config(
                        text=f"⏳ 正在下载模型... {p}%"))

            urllib.request.urlretrieve(model_url, zip_path, progress_hook)

            print("下载完成，正在解压...")
            self.root.after(0, lambda: self.status_label.config(text="⏳ 正在解压模型..."))
            self.root.update()

            # 解压
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.dirname(MODEL_PATH))

            # 删除 zip 文件
            os.remove(zip_path)

            print("模型准备完成！")
            self.root.after(0, lambda: self.status_label.config(text="✅ 模型下载完成，正在加载..."))
            self.root.update()

            # 重新加载模型
            self.init_vosk_model()

        except Exception as e:
            error_msg = f"❌ 模型下载失败：{str(e)}"
            print(error_msg)
            self.root.after(0, lambda: self.status_label.config(
                text="❌ 模型下载失败，请检查网络或手动下载", foreground="red"))

    def init_audio_device(self):
        """初始化音频输入设备"""
        self.audio = pyaudio.PyAudio()
        self.audio_devices = []  # 存储可用的输入设备
        # 收集可用音频输入设备
        print("\n可用音频输入设备：")
        for i in range(self.audio.get_device_count()):
            dev_info = self.audio.get_device_info_by_index(i)
            if dev_info['maxInputChannels'] > 0:
                device_name = dev_info['name']
                self.audio_devices.append((i, device_name))
                print(f"设备{i}：{device_name}")

    def create_gui(self):
        """创建GUI界面"""
        # 状态提示标签
        self.status_label = ttk.Label(
            self.root,
            text="等待启动识别",
            font=("微软雅黑", 10),
            wraplength=600
        )
        self.status_label.pack(pady=10)

        # 音频设备选择区域
        device_frame = ttk.LabelFrame(self.root, text="音频输入设备")
        device_frame.pack(padx=20, pady=5, fill=tk.X)

        # 设备选择下拉菜单
        self.device_var = tk.StringVar()
        device_names = [f"{idx}: {name}" for idx, name in self.audio_devices]
        if device_names:
            self.device_var.set(device_names[0])  # 默认选择第一个设备

        self.device_combo = ttk.Combobox(
            device_frame,
            textvariable=self.device_var,
            values=device_names,
            state="readonly",
            font=("微软雅黑", 9)
        )
        self.device_combo.pack(padx=10, pady=5, fill=tk.X)

        # 设备说明标签
        device_hint = ttk.Label(
            device_frame,
            text='💡 如需识别电脑播放的音频，请选择"立体声混音"设备',
            font=("微软雅黑", 8),
            foreground="gray"
        )
        device_hint.pack(padx=10, pady=(0, 5))

        # 按钮区域
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=5)

        # 开始/停止按钮
        self.toggle_btn = ttk.Button(
            btn_frame,
            text="🎤 开始录音识别",
            command=self.toggle_recognition,
            style="Accent.TButton"
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=5)

        # 打开音频文件按钮
        self.file_btn = ttk.Button(
            btn_frame,
            text="📂 打开音频文件",
            command=self.open_audio_file
        )
        self.file_btn.pack(side=tk.LEFT, padx=5)

        # 导出文字按钮
        self.export_btn = ttk.Button(
            btn_frame,
            text="💾 导出文字",
            command=self.export_text
        )
        self.export_btn.pack(side=tk.LEFT, padx=5)

        # 识别结果显示区域
        result_frame = ttk.LabelFrame(self.root, text="实时识别结果")
        result_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

        self.result_text = tk.Text(
            result_frame,
            wrap=tk.WORD,
            font=("微软雅黑", 12),
            bg="#f8f9fa",
            relief=tk.FLAT
        )
        self.result_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # 滚动条
        scrollbar = ttk.Scrollbar(self.result_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.result_text.yview)

    def toggle_recognition(self):
        """切换开始/停止识别状态"""
        global FINAL_RECOGNIZED_TEXT  # 声明使用全局变量
        if not self.is_running:
            # 启动识别：清空全局变量和类内临时变量
            FINAL_RECOGNIZED_TEXT = ""  # 清空全局变量，避免残留旧结果
            self.partial_text = ""

            # 检查模型是否加载成功
            if not self.recognizer:
                self.status_label.config(text="❌ 模型未加载，无法启动识别", foreground="red")
                return

            self.is_running = True
            self.toggle_btn.config(text="停止识别")
            self.result_text.delete(1.0, tk.END)  # 清空历史结果
            self.status_label.config(text="🎤 正在实时识别（离线）...", foreground="green")

            # 启动识别线程（避免阻塞GUI）
            self.recog_thread = threading.Thread(target=self.real_time_recognition)
            self.recog_thread.daemon = True
            self.recog_thread.start()
        else:
            # 停止识别
            self.is_running = False
            self.toggle_btn.config(text="开始识别")
            # ========== 2. 识别停止时，更新全局变量 ==========
            # 合并类内临时文本 + 最后剩余结果，写入全局变量
            FINAL_RECOGNIZED_TEXT = self.partial_text.strip()
            # 打印全局变量（验证）
            print(f"\n【全局变量 FINAL_RECOGNIZED_TEXT】：{FINAL_RECOGNIZED_TEXT}")

            self.status_label.config(text="识别已停止", foreground="orange")
            # 关闭音频流
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                self.audio_stream = None

    def real_time_recognition(self):
        """实时录音并识别"""
        # 获取用户选择的设备索引
        device_str = self.device_var.get()
        device_index = int(device_str.split(":")[0])
        device_name = device_str.split(":", 1)[1].strip()
        print(f"使用设备：{device_name} (索引: {device_index})")

        # 打开音频输入流（使用用户选择的设备）
        self.audio_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLERATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK
        )

        # 持续识别直到停止
        while self.is_running:
            try:
                # 读取音频数据
                data = self.audio_stream.read(CHUNK, exception_on_overflow=False)

                # Vosk识别（增量识别，实时返回结果）
                if self.recognizer.AcceptWaveform(data):
                    # 获取完整识别结果（句子级）
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        # 去掉词之间的空格，添加句号表示断句
                        text_no_space = text.replace(" ", "") + "。"
                        self.partial_text += text_no_space  # 累加到类内临时变量
                        self.root.after(0, self.update_result, text_no_space)
            except Exception as e:
                print(f"识别过程出错：{e}")
                continue

        # 识别停止后，获取最后剩余的结果
        final_result = json.loads(self.recognizer.FinalResult())
        final_text = final_result.get("text", "").strip()
        if final_text:
            # 去掉词之间的空格，添加句号
            final_text_no_space = final_text.replace(" ", "") + "。"
            self.partial_text += final_text_no_space  # 追加到临时变量
            self.root.after(0, self.update_result, final_text_no_space)

    def update_result(self, text):
        """更新完整识别结果到文本框（线程安全）"""
        self.result_text.insert(tk.END, text)
        self.result_text.see(tk.END)  # 自动滚动到最后

    def export_text(self):
        """导出识别结果到文本文件"""
        # 获取文本框内容
        content = self.result_text.get("1.0", tk.END).strip()

        if not content:
            self.status_label.config(text="⚠️ 没有可导出的内容", foreground="orange")
            return

        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            title="导出识别结果",
            defaultextension=".txt",
            filetypes=[
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ],
            initialfile="识别结果.txt"
        )

        if not file_path:
            return

        try:
            # 写入文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.status_label.config(text=f"✅ 已导出到: {file_path}", foreground="green")

        except Exception as e:
            self.status_label.config(text=f"❌ 导出失败: {str(e)}", foreground="red")

    def open_audio_file(self):
        """打开音频文件并识别（支持多选）"""
        # 检查模型是否加载
        if not self.recognizer:
            self.status_label.config(text="❌ 模型未加载，无法识别", foreground="red")
            return

        # 如果正在录音，先停止
        if self.is_running:
            self.toggle_recognition()

        # 选择音频文件（支持多选）
        file_paths = filedialog.askopenfilenames(
            title="选择音频文件（可多选）",
            filetypes=[
                ("音频文件", "*.wav *.mp3 *.flac *.ogg *.m4a *.aac *.wma"),
                ("WAV音频", "*.wav"),
                ("MP3音频", "*.mp3"),
                ("FLAC音频", "*.flac"),
                ("所有文件", "*.*")
            ]
        )

        if not file_paths:
            return

        # 清空文本框并开始识别
        self.result_text.delete(1.0, tk.END)

        # 显示文件数量
        if len(file_paths) == 1:
            file_name = file_paths[0].split('/')[-1].split('\\')[-1]
            self.status_label.config(text=f"📂 正在识别: {file_name}", foreground="blue")
        else:
            self.status_label.config(text=f"📂 正在识别 {len(file_paths)} 个文件...", foreground="blue")

        # 启动文件识别线程
        self.file_thread = threading.Thread(target=self.recognize_files, args=(file_paths,))
        self.file_thread.daemon = True
        self.file_thread.start()

    def recognize_files(self, file_paths):
        """识别多个音频文件"""
        total = len(file_paths)
        for idx, file_path in enumerate(file_paths, 1):
            # 显示当前进度
            file_name = file_path.split('/')[-1].split('\\')[-1]
            self.root.after(0, lambda f=file_name, i=idx: self.status_label.config(
                text=f"📂 正在识别 ({i}/{total}): {f}", foreground="blue"))

            # 识别当前文件
            self.recognize_file(file_path, show_header=(total > 1))

            # 多文件时添加分隔线
            if idx < total:
                self.root.after(0, lambda: self.update_result("\n" + "="*40 + "\n"))

        # 全部完成
        self.root.after(0, lambda: self.status_label.config(
            text=f"✅ 识别完成！共处理 {total} 个文件", foreground="green"))

    def recognize_file(self, file_path, show_header=False):
        """识别音频文件（支持多种格式）"""
        temp_wav = None
        try:
            # 多文件模式下显示文件名标题
            if show_header:
                file_name = file_path.split('/')[-1].split('\\')[-1]
                self.root.after(0, lambda f=file_name: self.update_result(f"\n【{f}】\n"))

            # 创建临时文件
            temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_wav.close()

            # 使用 FFmpeg 转换为 WAV 格式（单声道、16kHz、16位）
            cmd = [
                FFMPEG_PATH,
                "-i", file_path,
                "-ar", "16000",      # 采样率 16kHz
                "-ac", "1",          # 单声道
                "-sample_fmt", "s16", # 16位
                "-y",                # 覆盖输出文件
                temp_wav.name
            ]

            # 执行转换
            subprocess.run(cmd, capture_output=True, check=True)

            # 打开转换后的 WAV 文件
            wf = wave.open(temp_wav.name, "rb")

            # 创建识别器
            rec = KaldiRecognizer(self.model, wf.getframerate())
            rec.SetWords(True)

            # 逐块读取并识别
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        text_no_space = text.replace(" ", "") + "。"
                        self.root.after(0, self.update_result, text_no_space)

            # 获取最后的结果
            final_result = json.loads(rec.FinalResult())
            final_text = final_result.get("text", "").strip()
            if final_text:
                final_text_no_space = final_text.replace(" ", "") + "。"
                self.root.after(0, self.update_result, final_text_no_space)

            wf.close()
            self.root.after(0, self.update_result, "\n✅ 文件识别完成！\n")
            self.root.after(0, lambda: self.status_label.config(text="✅ 文件识别完成", foreground="green"))

        except Exception as e:
            error_msg = f"\n❌ 识别出错：{str(e)}\n"
            self.root.after(0, self.update_result, error_msg)
            self.root.after(0, lambda: self.status_label.config(text=f"❌ 识别出错", foreground="red"))
        finally:
            # 清理临时文件
            if temp_wav and os.path.exists(temp_wav.name):
                os.unlink(temp_wav.name)

if __name__ == "__main__":
    # 初始化GUI样式
    root = tk.Tk()
    style = ttk.Style(root)
    style.configure("Accent.TButton", font=("微软雅黑", 11), padding=6)

    # 启动应用
    app = VoskRealTimeASR(root)
    root.mainloop()

    # 程序退出时安全释放资源
    try:
        if hasattr(app, 'audio_stream') and app.audio_stream:
            app.audio_stream.stop_stream()
            app.audio_stream.close()
        if hasattr(app, 'audio') and app.audio:
            app.audio.terminate()
    except Exception as e:
        print(f"释放资源时出错：{e}")