"""
visual/beat_widget.py
Widget hiệu ứng Beat — vòng tròn pulse khi có nhịp, màu Spotify
"""

import numpy as np
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QRadialGradient
from PyQt5.QtCore import Qt, QTimer, QPointF


class BeatWidget(QWidget):
    COLOR_BG      = QColor("#121212")
    COLOR_BEAT    = QColor("#1DB954")
    COLOR_RING    = QColor("#1ED760")
    COLOR_DIM     = QColor("#0A3D1A")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.setStyleSheet("background-color: #121212; border-radius: 8px;")

        self._beat_energy = 0.0   # Năng lượng beat hiện tại
        self._rings = []           # Danh sách vòng ring đang nở ra
        self._bpm = 0.0
        self._pulse_scale = 0.0   # Scale hiện tại của vòng tròn chính

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(16)

    def on_beat(self, energy: float):
        """Gọi khi phát hiện beat"""
        self._beat_energy = min(1.0, energy * 2)
        self._pulse_scale = 1.0
        # Thêm ring mới
        self._rings.append({"radius": 0.15, "alpha": 200})

    def set_bpm(self, bpm: float):
        self._bpm = bpm

    def _animate(self):
        # Giảm dần pulse
        self._pulse_scale = max(0.0, self._pulse_scale - 0.06)
        self._beat_energy = max(0.0, self._beat_energy - 0.04)

        # Mở rộng và mờ dần các ring
        new_rings = []
        for ring in self._rings:
            ring["radius"] += 0.025
            ring["alpha"]  -= 12
            if ring["alpha"] > 0 and ring["radius"] < 0.9:
                new_rings.append(ring)
        self._rings = new_rings

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx, cy = w // 2, h // 2
        base_r = min(w, h) * 0.28

        # Nền
        painter.fillRect(0, 0, w, h, self.COLOR_BG)

        # Vẽ các ring lan ra
        for ring in self._rings:
            r = ring["radius"] * min(w, h) * 0.9
            alpha = max(0, ring["alpha"])
            color = QColor(29, 185, 84, alpha)
            pen = QPen(color, 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), r, r)

        # Vòng nền mờ
        painter.setPen(QPen(self.COLOR_DIM, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), base_r, base_r)

        # Vòng tròn chính — pulse khi beat
        scale = 1.0 + self._pulse_scale * 0.25
        current_r = base_r * scale

        # Radial gradient
        grad = QRadialGradient(QPointF(cx, cy), current_r)
        energy = self._beat_energy
        inner_color = QColor(
            int(29 + energy * 30),
            int(185 + energy * 30),
            int(84 + energy * 20),
            int(180 + energy * 75)
        )
        outer_color = QColor(29, 185, 84, 40)
        grad.setColorAt(0, inner_color)
        grad.setColorAt(0.6, QColor(29, 185, 84, 100))
        grad.setColorAt(1.0, outer_color)

        painter.setPen(QPen(self.COLOR_RING, 2))
        painter.setBrush(grad)
        painter.drawEllipse(QPointF(cx, cy), current_r, current_r)

        # Hiển thị BPM
        painter.setPen(QColor("#FFFFFF") if self._beat_energy > 0.1 else QColor("#535353"))
        font = QFont("Segoe UI", 18 if self._pulse_scale > 0.1 else 16)
        font.setBold(True)
        painter.setFont(font)
        bpm_text = f"{int(self._bpm)}" if self._bpm > 0 else "--"
        painter.drawText(cx - 28, cy + 8, bpm_text)

        # Label "BPM"
        painter.setPen(QColor("#535353"))
        font2 = QFont("Segoe UI", 8)
        painter.setFont(font2)
        painter.drawText(cx - 12, cy + 22, "BPM")

        # Label góc
        painter.drawText(6, 14, "BEAT")

    def reset(self):
        self._rings = []
        self._pulse_scale = 0.0
        self._beat_energy = 0.0
        self._bpm = 0.0
        self.update()