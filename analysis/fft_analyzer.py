"""
analysis/fft_analyzer.py
Phân tích tín hiệu âm thanh: FFT, tính năng lượng dải tần
Công thức: Xk = Σ x_n * e^(-i2πkn/N)
"""

import numpy as np
from scipy.signal import windows


class FFTAnalyzer:
    # Dải tần số (Hz)
    BASS_RANGE   = (20, 300)
    MID_RANGE    = (300, 4000)
    TREBLE_RANGE = (4000, 20000)

    def __init__(self, sample_rate: int = 44100, fft_size: int = 2048):
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.hop_length = fft_size // 4

        # Tần số tương ứng với mỗi bin FFT
        self.frequencies = np.fft.rfftfreq(fft_size, d=1.0 / sample_rate)

        # Hann window để giảm spectral leakage
        self.window = windows.hann(fft_size)

        # Cache kết quả gần nhất
        self._last_spectrum = np.zeros(fft_size // 2 + 1)
        self._last_magnitude = np.zeros(fft_size // 2 + 1)

    def compute_fft(self, chunk: np.ndarray) -> np.ndarray:
        """
        Tính FFT của đoạn tín hiệu.
        Trả về magnitude spectrum (dB) có độ dài fft_size//2 + 1
        """
        # Đảm bảo đúng kích thước
        if len(chunk) < self.fft_size:
            chunk = np.pad(chunk, (0, self.fft_size - len(chunk)))
        else:
            chunk = chunk[:self.fft_size]

        # Áp dụng Hann window
        windowed = chunk * self.window

        # Tính FFT (dùng rfft vì tín hiệu thực)
        spectrum = np.fft.rfft(windowed)

        # Magnitude (biên độ)
        magnitude = np.abs(spectrum) / self.fft_size

        # Chuyển sang dB scale: 20 * log10(|X|)
        magnitude_db = 20 * np.log10(magnitude + 1e-10)

        # Normalize về [0, 1]
        magnitude_norm = np.clip((magnitude_db + 80) / 80, 0, 1)

        self._last_spectrum = magnitude_db
        self._last_magnitude = magnitude_norm

        return magnitude_norm

    def get_frequency_bands(self, spectrum: np.ndarray) -> dict:
        """
        Tính năng lượng trung bình theo 3 dải tần:
        Bass (20-300Hz), Mid (300-4kHz), Treble (4k-20kHz)
        """
        def band_energy(freq_min, freq_max):
            mask = (self.frequencies >= freq_min) & (self.frequencies <= freq_max)
            if mask.sum() == 0:
                return 0.0
            return float(np.mean(spectrum[mask]))

        return {
            "bass":   band_energy(*self.BASS_RANGE),
            "mid":    band_energy(*self.MID_RANGE),
            "treble": band_energy(*self.TREBLE_RANGE),
        }

    def get_dominant_frequency(self, spectrum: np.ndarray) -> float:
        """Tìm tần số có năng lượng lớn nhất"""
        if len(spectrum) == 0:
            return 0.0
        peak_idx = np.argmax(spectrum)
        if peak_idx < len(self.frequencies):
            return float(self.frequencies[peak_idx])
        return 0.0

    def compute_spectral_centroid(self, spectrum: np.ndarray) -> float:
        """
        Tính spectral centroid — 'trọng tâm' tần số
        Cho biết nhạc đang nặng phần trầm hay phần cao
        """
        mag = spectrum + 1e-10
        return float(np.sum(self.frequencies[:len(mag)] * mag) / np.sum(mag))

    @property
    def num_bins(self) -> int:
        return len(self.frequencies)