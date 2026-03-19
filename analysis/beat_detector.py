"""
analysis/beat_detector.py
Nhận diện nhịp (Beat Detection) dùng librosa + energy-based realtime detection
- Offline: librosa.beat.beat_track() để tính BPM và beat timestamps
- Realtime: so sánh energy bass với threshold động
"""

import numpy as np
import librosa
from PyQt5.QtCore import QObject, pyqtSignal


class BeatDetector(QObject):
    beat_detected = pyqtSignal(float)  # emit khi có beat (kèm energy)
    bpm_updated = pyqtSignal(float)  # emit khi BPM được cập nhật

    def __init__(self, sample_rate: int = 44100):
        super().__init__()
        self.sample_rate = sample_rate
        self.bpm = 0.0
        self.beat_times = np.array([])  # timestamp các beat (giây)

        # Realtime beat detection
        self._energy_history = np.zeros(43)  # ~1 giây lịch sử energy
        self._history_idx = 0
        self._last_beat_time = 0.0
        self._min_beat_interval = 0.3  # tối thiểu 0.3s giữa 2 beat (200 BPM max)

        # BPM tracking realtime
        self._beat_timestamps = []

    # ------------------------------------------------------------------ #
    #  OFFLINE ANALYSIS  (chạy 1 lần khi load file)                       #
    # ------------------------------------------------------------------ #

    def analyze_offline(self, audio_data: np.ndarray, sr: int) -> dict:
        """
        Phân tích toàn bộ file để tính BPM và vị trí beat.
        Dùng librosa.beat.beat_track()
        Trả về dict: {bpm, beat_times, beat_frames}
        """
        print("[BeatDetector] Đang phân tích beat offline...")

        # Tính onset strength envelope
        onset_env = librosa.onset.onset_strength(y=audio_data, sr=sr, hop_length=512)

        # Beat tracking
        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=sr,
            hop_length=512,
            trim=True
        )

        beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=512)

        self.bpm = float(tempo)
        self.beat_times = beat_times
        self._min_beat_interval = 60.0 / max(self.bpm * 1.5, 60)

        print(f"[BeatDetector] BPM: {self.bpm:.1f} | Số beat: {len(beat_times)}")
        self.bpm_updated.emit(self.bpm)

        return {
            "bpm": self.bpm,
            "beat_times": beat_times,
            "beat_frames": beat_frames,
        }

    def is_beat_at(self, current_time: float, tolerance: float = 0.05) -> bool:
        """Kiểm tra có beat tại thời điểm current_time không (dựa trên offline analysis)"""
        if len(self.beat_times) == 0:
            return False
        diffs = np.abs(self.beat_times - current_time)
        return bool(np.min(diffs) < tolerance)

    # ------------------------------------------------------------------ #
    #  REALTIME DETECTION (dựa trên energy)                               #
    # ------------------------------------------------------------------ #

    def process_realtime(self, spectrum: np.ndarray, current_time: float) -> bool:
        """
        Phát hiện beat realtime từ energy của bass spectrum.
        Thuật toán: so sánh energy hiện tại với trung bình lịch sử.

        Args:
            spectrum: magnitude spectrum từ FFTAnalyzer (normalized 0-1)
            current_time: thời gian hiện tại (giây)

        Returns:
            True nếu phát hiện beat
        """
        # Lấy bass energy (phần đầu spectrum tương ứng bass)
        bass_bins = max(1, len(spectrum) // 10)
        bass_energy = float(np.mean(spectrum[:bass_bins]))

        # Cập nhật lịch sử
        self._energy_history[self._history_idx % len(self._energy_history)] = bass_energy
        self._history_idx += 1

        # Tính ngưỡng động (dynamic threshold)
        avg_energy = np.mean(self._energy_history)
        variance = np.var(self._energy_history)

        # Công thức threshold từ nghiên cứu beat detection:
        # C = -0.0025714 * variance + 1.5142857
        C = max(1.1, -0.0025714 * variance * 1000 + 1.5142857)
        threshold = C * avg_energy

        # Điều kiện beat:
        # 1. Energy vượt ngưỡng
        # 2. Energy đủ lớn (tránh noise)
        # 3. Đủ thời gian từ beat trước
        is_beat = (
                bass_energy > threshold
                and bass_energy > 0.1
                and (current_time - self._last_beat_time) > self._min_beat_interval
        )

        if is_beat:
            self._last_beat_time = current_time
            self._update_realtime_bpm(current_time)
            self.beat_detected.emit(bass_energy)

        return is_beat

    def _update_realtime_bpm(self, current_time: float):
        """Cập nhật BPM dựa trên khoảng cách giữa các beat realtime"""
        self._beat_timestamps.append(current_time)
        # Giữ 8 beat gần nhất
        if len(self._beat_timestamps) > 8:
            self._beat_timestamps.pop(0)

        if len(self._beat_timestamps) >= 3:
            intervals = np.diff(self._beat_timestamps)
            avg_interval = np.mean(intervals)
            if avg_interval > 0:
                realtime_bpm = 60.0 / avg_interval
                if 40 < realtime_bpm < 250:  # Lọc BPM hợp lệ
                    self.bpm_updated.emit(realtime_bpm)

    def reset(self):
        """Reset trạng thái để chuẩn bị cho file mới"""
        self._energy_history = np.zeros(43)
        self._history_idx = 0
        self._last_beat_time = 0.0
        self._beat_timestamps = []
        self.bpm = 0.0
        self.beat_times = np.array([])