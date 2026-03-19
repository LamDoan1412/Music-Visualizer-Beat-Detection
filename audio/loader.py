"""
audio/loader.py
Load file âm thanh (MP3, WAV, OGG, FLAC) và trích xuất dữ liệu thô
Sử dụng librosa để decode và lấy sample data
"""

import numpy as np
import librosa
import os


class AudioLoader:
    SUPPORTED_FORMATS = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac")

    def __init__(self):
        self.file_path = None
        self.sample_rate = 44100
        self.audio_data = None      # numpy array toàn bộ file
        self.duration = 0.0
        self.channels = 1

    def load(self, file_path: str) -> bool:
        """
        Load file âm thanh.
        Trả về True nếu thành công, False nếu lỗi.
        """
        if not os.path.exists(file_path):
            print(f"[Loader] File không tồn tại: {file_path}")
            return False

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_FORMATS:
            print(f"[Loader] Định dạng không hỗ trợ: {ext}")
            return False

        try:
            # librosa load: mono=True để đồng nhất xử lý
            self.audio_data, self.sample_rate = librosa.load(
                file_path,
                sr=44100,
                mono=True
            )
            self.file_path = file_path
            self.duration = librosa.get_duration(y=self.audio_data, sr=self.sample_rate)
            print(f"[Loader] Đã load: {os.path.basename(file_path)}")
            print(f"[Loader] Duration: {self.duration:.2f}s | SR: {self.sample_rate}Hz")
            return True

        except Exception as e:
            print(f"[Loader] Lỗi khi load file: {e}")
            return False

    def get_chunk(self, start_sec: float, duration_sec: float = 0.1) -> np.ndarray:
        """Lấy một đoạn audio data theo giây"""
        if self.audio_data is None:
            return np.zeros(4096)

        start_sample = int(start_sec * self.sample_rate)
        end_sample = int((start_sec + duration_sec) * self.sample_rate)
        end_sample = min(end_sample, len(self.audio_data))

        return self.audio_data[start_sample:end_sample]

    def get_full_waveform(self, downsample: int = 1000) -> np.ndarray:
        """Lấy waveform tổng thể (downsampled để vẽ overview)"""
        if self.audio_data is None:
            return np.zeros(downsample)

        step = max(1, len(self.audio_data) // downsample)
        return self.audio_data[::step][:downsample]

    @property
    def file_name(self) -> str:
        if self.file_path:
            return os.path.splitext(os.path.basename(self.file_path))[0]
        return "Unknown"

    @property
    def file_size_mb(self) -> float:
        if self.file_path and os.path.exists(self.file_path):
            return os.path.getsize(self.file_path) / (1024 * 1024)
        return 0.0