"""
visual/spectrum_widget.py
Widget vẽ FFT Spectrum (cột tần số) theo phong cách Spotify
Màu xanh lá (#A855F7) như Spotify
"""

import numpy as np
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QPen, QFont
from PyQt5.QtCore import Qt, QRect, QTimer


class SpectrumWidget(QWidget):
    # Màu Spotify
    COLOR_SPOTIFY_GREEN = QColor("#A855F7")
    COLOR_SPOTIFY_MID   = QColor("#9333EA")
    COLOR_SPOTIFY_LOW   = QColor("#7C3AED")
    COLOR_BG            = QColor("#121212")
    COLOR_GRID          = QColor("#282828")

    NUM_BARS = 80   # Số cột spectrum

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.setStyleSheet("background-color: #121212; border-radius: 8px;")

        self._spectrum = np.zeros(self.NUM_BARS)
        self._smooth   = np.zeros(self.NUM_BARS)   # Giá trị smooth hiện tại
        self._peaks    = np.zeros(self.NUM_BARS)   # Đỉnh rơi (peak fall-off)
        self._peak_vel = np.zeros(self.NUM_BARS)   # Tốc độ rơi

        # Timer animation mượt
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(16)  # ~60fps

    def update_spectrum(self, spectrum: np.ndarray):
        """Cập nhật dữ liệu spectrum mới"""
        # Resample về NUM_BARS
        if len(spectrum) != self.NUM_BARS:
            indices = np.linspace(0, len(spectrum) - 1, self.NUM_BARS).astype(int)
            self._spectrum = spectrum[indices]
        else:
            self._spectrum = spectrum.copy()

    def _animate(self):
        """Animation mượt: smooth + peak fall-off"""
        alpha_rise = 0.4   # Tốc độ tăng
        alpha_fall = 0.15  # Tốc độ giảm

        for i in range(self.NUM_BARS):
            target = self._spectrum[i]

            if target > self._smooth[i]:
                self._smooth[i] = self._smooth[i] * (1 - alpha_rise) + target * alpha_rise
            else:
                self._smooth[i] = self._smooth[i] * (1 - alpha_fall) + target * alpha_fall

            # Peak fall-off
            if self._smooth[i] >= self._peaks[i]:
                self._peaks[i] = self._smooth[i]
                self._peak_vel[i] = 0.0
            else:
                self._peak_vel[i] += 0.002
                self._peaks[i] = max(0, self._peaks[i] - self._peak_vel[i])

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Nền
        painter.fillRect(0, 0, w, h, self.COLOR_BG)

        # Vẽ lưới ngang
        painter.setPen(QPen(self.COLOR_GRID, 1, Qt.DotLine))
        for level in [0.25, 0.5, 0.75]:
            y = int(h * (1 - level))
            painter.drawLine(0, y, w, y)

        # Tính kích thước cột
        margin = 4
        total_margin = margin * (self.NUM_BARS - 1)
        bar_w = max(2, (w - total_margin) // self.NUM_BARS)
        gap = (w - bar_w * self.NUM_BARS) // max(1, self.NUM_BARS - 1)

        for i in range(self.NUM_BARS):
            val = max(0.0, min(1.0, self._smooth[i]))
            bar_h = int(val * (h - 8))
            x = i * (bar_w + gap)
            y = h - bar_h

            if bar_h < 2:
                bar_h = 2
                y = h - 2

            # Gradient màu xanh Spotify
            grad = QLinearGradient(x, y, x, h)

            if val > 0.75:
                grad.setColorAt(0.0, QColor("#C084FC"))   # Sáng nhất
                grad.setColorAt(0.5, self.COLOR_SPOTIFY_GREEN)
                grad.setColorAt(1.0, self.COLOR_SPOTIFY_LOW)
            elif val > 0.4:
                grad.setColorAt(0.0, self.COLOR_SPOTIFY_GREEN)
                grad.setColorAt(1.0, self.COLOR_SPOTIFY_LOW)
            else:
                grad.setColorAt(0.0, self.COLOR_SPOTIFY_MID)
                grad.setColorAt(1.0, QColor("#0A4A22"))

            painter.fillRect(x, y, bar_w, bar_h, grad)

            # Peak indicator (chấm trắng ở đỉnh)
            peak_val = self._peaks[i]
            if peak_val > 0.05:
                peak_y = h - int(peak_val * (h - 8)) - 3
                painter.fillRect(x, max(0, peak_y), bar_w, 2, QColor("#FFFFFF"))

        # Label "SPECTRUM"
        painter.setPen(QColor("#535353"))
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        painter.drawText(6, 14, "SPECTRUM")