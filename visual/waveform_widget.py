"""
visual/waveform_widget.py
Widget vẽ Waveform realtime — tín hiệu trong miền thời gian
Màu xanh Spotify với glow effect
"""

import numpy as np
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPainterPath
from PyQt5.QtCore import Qt, QTimer


class WaveformWidget(QWidget):
    COLOR_BG      = QColor("#121212")
    COLOR_WAVE    = QColor("#A855F7")
    COLOR_WAVE_DIM = QColor("#7C3AED")
    COLOR_CENTER  = QColor("#282828")
    COLOR_LABEL   = QColor("#535353")

    HISTORY_LEN = 512   # Số sample hiển thị

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.setStyleSheet("background-color: #121212; border-radius: 8px;")

        self._samples = np.zeros(self.HISTORY_LEN)
        self._smooth  = np.zeros(self.HISTORY_LEN)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(16)

        self._alpha = 0.3  # Smoothing factor

    def update_waveform(self, chunk: np.ndarray):
        """Cập nhật dữ liệu waveform"""
        if len(chunk) == 0:
            return

        # Resample về HISTORY_LEN
        if len(chunk) != self.HISTORY_LEN:
            indices = np.linspace(0, len(chunk) - 1, self.HISTORY_LEN).astype(int)
            self._samples = chunk[indices].astype(float)
        else:
            self._samples = chunk.astype(float)

        # Normalize
        max_val = np.max(np.abs(self._samples)) + 1e-10
        self._samples /= max_val

    def _animate(self):
        # Smooth nhẹ
        self._smooth = self._smooth * (1 - self._alpha) + self._samples * self._alpha
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        mid = h // 2

        # Nền
        painter.fillRect(0, 0, w, h, self.COLOR_BG)

        # Đường giữa
        painter.setPen(QPen(self.COLOR_CENTER, 1, Qt.DotLine))
        painter.drawLine(0, mid, w, mid)

        if np.all(self._smooth == 0):
            painter.setPen(QColor("#535353"))
            painter.drawText(QWidget.rect(self), Qt.AlignCenter, "Chưa có tín hiệu")
            return

        # Vẽ waveform bằng QPainterPath
        path = QPainterPath()
        step = w / (self.HISTORY_LEN - 1)

        for i, val in enumerate(self._smooth):
            x = i * step
            y = mid - val * (mid - 6)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        # Vẽ shadow mờ
        shadow_pen = QPen(self.COLOR_WAVE_DIM, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(shadow_pen)
        painter.drawPath(path)

        # Vẽ đường chính
        main_pen = QPen(self.COLOR_WAVE, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(main_pen)
        painter.drawPath(path)

        # Label
        painter.setPen(self.COLOR_LABEL)
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        painter.drawText(6, 14, "WAVEFORM")

    def clear(self):
        self._samples = np.zeros(self.HISTORY_LEN)
        self._smooth  = np.zeros(self.HISTORY_LEN)
        self.update()