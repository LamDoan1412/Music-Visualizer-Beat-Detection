"""
analysis/beat_detector.py
Nhận diện nhịp (Beat Detection) dùng librosa + energy-based realtime detection
- Offline: librosa.beat.beat_track() để tính BPM và beat timestamps
- Realtime: so sánh energy bass với threshold động

FIX: Chạy analyze_offline() trong QThread riêng để tránh crash
     Stack Overflow (0xC0000409) khi xử lý file dài trên main thread
"""

import numpy as np
import librosa
from PyQt5.QtCore import QObject, pyqtSignal, QThread


# ══════════════════════════════════════════════════════════════════
#  WORKER chạy trong QThread riêng — tránh crash main thread
# ══════════════════════════════════════════════════════════════════
class _AnalyzeWorker(QObject):
    """Worker nội bộ, không dùng trực tiếp — dùng qua BeatDetector."""
    finished  = pyqtSignal(dict)   # emit kết quả khi xong
    error     = pyqtSignal(str)    # emit nếu lỗi

    # Tối đa 90 giây đầu để phân tích BPM — đủ chính xác, tránh OOM
    MAX_ANALYZE_SEC = 90

    def __init__(self, audio_data: np.ndarray, sr: int):
        super().__init__()
        self.audio_data = audio_data
        self.sr         = sr

    def run(self):
        try:
            audio = self.audio_data
            sr    = self.sr

            # ── Giới hạn độ dài để tránh stack overflow ──────────────
            max_samples = int(self.MAX_ANALYZE_SEC * sr)
            if len(audio) > max_samples:
                print(f"[BeatDetector] File dài, chỉ phân tích {self.MAX_ANALYZE_SEC}s đầu")
                audio = audio[:max_samples]

            # ── Onset strength ────────────────────────────────────────
            onset_env = librosa.onset.onset_strength(
                y=audio, sr=sr, hop_length=512
            )

            # ── Beat tracking ─────────────────────────────────────────
            tempo, beat_frames = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=512,
                trim=True
            )

            beat_times = librosa.frames_to_time(
                beat_frames, sr=sr, hop_length=512
            )

            self.finished.emit({
                "bpm": float(np.atleast_1d(tempo)[0]),
                "beat_times" : beat_times,
                "beat_frames": beat_frames,
            })

        except Exception as e:
            self.error.emit(str(e))


# ══════════════════════════════════════════════════════════════════
#  BeatDetector — public API
# ══════════════════════════════════════════════════════════════════
class BeatDetector(QObject):
    beat_detected  = pyqtSignal(float)   # emit khi có beat (kèm energy)
    bpm_updated    = pyqtSignal(float)   # emit khi BPM được cập nhật
    analysis_done  = pyqtSignal(dict)    # emit khi offline analysis xong ← MỚI
    analysis_error = pyqtSignal(str)     # emit nếu phân tích lỗi       ← MỚI

    def __init__(self, sample_rate: int = 44100):
        super().__init__()
        self.sample_rate = sample_rate
        self.bpm         = 0.0
        self.beat_times  = np.array([])

        # Realtime beat detection
        self._energy_history    = np.zeros(43)
        self._history_idx       = 0
        self._last_beat_time    = 0.0
        self._min_beat_interval = 0.3

        # BPM tracking realtime
        self._beat_timestamps = []

        # Thread quản lý
        self._thread = None
        self._worker = None

    # ------------------------------------------------------------------ #
    #  OFFLINE ANALYSIS — chạy trong QThread riêng                        #
    # ------------------------------------------------------------------ #

    def analyze_offline(self, audio_data: np.ndarray, sr: int):
        """
        Phân tích BPM và beat trong QThread riêng.
        Kết quả trả về qua signal analysis_done(dict).

        ⚠️  KHÔNG block main thread — không crash nữa!
        Lắng nghe signal:
            detector.analysis_done.connect(my_callback)
            detector.analysis_error.connect(my_error_handler)
        """
        print("[BeatDetector] Đang phân tích beat offline (background thread)...")

        # Dọn thread cũ nếu còn
        self._cleanup_thread()

        # Tạo thread + worker mới
        self._thread = QThread()
        self._worker = _AnalyzeWorker(audio_data, sr)
        self._worker.moveToThread(self._thread)

        # Kết nối signal
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)

        self._thread.start()

    def _on_analysis_done(self, result: dict):
        """Nhận kết quả từ worker thread."""
        self.bpm        = result["bpm"]
        self.beat_times = result["beat_times"]
        self._min_beat_interval = 60.0 / max(self.bpm * 1.5, 60)

        print(f"[BeatDetector] BPM: {self.bpm:.1f} | Số beat: {len(self.beat_times)}")
        self.bpm_updated.emit(self.bpm)
        self.analysis_done.emit(result)

    def _on_analysis_error(self, msg: str):
        print(f"[BeatDetector] Lỗi phân tích: {msg}")
        self.analysis_error.emit(msg)

    def _cleanup_thread(self):
        """Dọn thread và worker cũ."""
        if self._thread is not None:
            try:
                if self._thread.isRunning():
                    self._thread.quit()
                    self._thread.wait(3000)  # chờ tối đa 3s
            except Exception:
                pass
            self._thread = None
            self._worker = None

    def is_beat_at(self, current_time: float, tolerance: float = 0.05) -> bool:
        """Kiểm tra có beat tại thời điểm current_time không."""
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
        """
        bass_bins   = max(1, len(spectrum) // 10)
        bass_energy = float(np.mean(spectrum[:bass_bins]))

        self._energy_history[self._history_idx % len(self._energy_history)] = bass_energy
        self._history_idx += 1

        avg_energy = np.mean(self._energy_history)
        variance   = np.var(self._energy_history)

        C         = max(1.1, -0.0025714 * variance * 1000 + 1.5142857)
        threshold = C * avg_energy

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
        """Cập nhật BPM dựa trên khoảng cách giữa các beat realtime."""
        self._beat_timestamps.append(current_time)
        if len(self._beat_timestamps) > 8:
            self._beat_timestamps.pop(0)

        if len(self._beat_timestamps) >= 3:
            intervals   = np.diff(self._beat_timestamps)
            avg_interval = np.mean(intervals)
            if avg_interval > 0:
                realtime_bpm = 60.0 / avg_interval
                if 40 < realtime_bpm < 250:
                    self.bpm_updated.emit(realtime_bpm)

    def reset(self):
        """Reset trạng thái để chuẩn bị cho file mới."""
        self._cleanup_thread()
        self._energy_history    = np.zeros(43)
        self._history_idx       = 0
        self._last_beat_time    = 0.0
        self._beat_timestamps   = []
        self.bpm                = 0.0
        self.beat_times         = np.array([])