"""
ui/main_window.py
Cửa sổ chính — phong cách Spotify Dark
Kết nối tất cả module: Player, Loader, FFT, Beat, Visual
"""

import os
import time
import numpy as np

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QFileDialog,
    QProgressBar, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

from audio.loader import AudioLoader
from audio.player import AudioPlayer
from analysis.fft_analyzer import FFTAnalyzer
from analysis.beat_detector import BeatDetector
from visual.spectrum_widget import SpectrumWidget
from visual.waveform_widget import WaveformWidget
from visual.beat_widget import BeatWidget


# ──────────────────────────────────────────
#  Stylesheet Spotify-inspired
# ──────────────────────────────────────────
SPOTIFY_STYLE = """
QMainWindow, QWidget#central {
    background-color: #121212;
    color: #FFFFFF;
}
QLabel {
    color: #FFFFFF;
    background: transparent;
}
QLabel#subtitle {
    color: #B3B3B3;
    font-size: 12px;
}
QLabel#green {
    color: #1DB954;
    font-weight: bold;
}
QPushButton#btnPlay {
    background-color: #1DB954;
    color: #000000;
    border: none;
    border-radius: 20px;
    font-size: 14px;
    font-weight: bold;
    padding: 8px 24px;
    min-width: 80px;
}
QPushButton#btnPlay:hover {
    background-color: #1ED760;
}
QPushButton#btnPlay:pressed {
    background-color: #17A349;
}
QPushButton#btnSecondary {
    background-color: transparent;
    color: #B3B3B3;
    border: 1px solid #535353;
    border-radius: 16px;
    font-size: 12px;
    padding: 6px 18px;
    min-width: 64px;
}
QPushButton#btnSecondary:hover {
    background-color: #282828;
    color: #FFFFFF;
    border-color: #B3B3B3;
}
QPushButton#btnLoad {
    background-color: transparent;
    color: #1DB954;
    border: 1px solid #1DB954;
    border-radius: 16px;
    font-size: 12px;
    font-weight: bold;
    padding: 6px 18px;
}
QPushButton#btnLoad:hover {
    background-color: #1DB954;
    color: #000000;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #535353;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    border: none;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QSlider::sub-page:horizontal {
    background: #1DB954;
    border-radius: 2px;
}
QSlider::handle:horizontal:hover {
    background: #1DB954;
    width: 14px;
    height: 14px;
    margin: -5px 0;
}
QFrame#separator {
    background-color: #282828;
    border: none;
}
QProgressBar {
    background-color: #535353;
    border: none;
    border-radius: 2px;
    height: 4px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #1DB954;
    border-radius: 2px;
}
"""


def fmt_time(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60}:{s % 60:02d}"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 Music Visualizer — Beat Detection")
        self.setMinimumSize(900, 700)
        self.resize(960, 760)
        self.setStyleSheet(SPOTIFY_STYLE)

        # ── Core components ──
        self.loader   = AudioLoader()
        self.player   = AudioPlayer()
        self.fft      = FFTAnalyzer(sample_rate=44100, fft_size=2048)
        self.detector = BeatDetector(sample_rate=44100)

        # ── State ──
        self._current_pos = 0.0
        self._is_playing  = False
        self._seeking     = False

        self._setup_ui()
        self._connect_signals()

        # Timer để pull audio chunk và update visualizer
        self._viz_timer = QTimer(self)
        self._viz_timer.timeout.connect(self._update_visualizer)
        self._viz_timer.start(33)  # ~30fps

        # Timer để update progress bar
        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._update_progress)
        self._progress_timer.start(100)

    # ──────────────────────────────────────────
    #  UI Setup
    # ──────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # ── Header ──
        header = QHBoxLayout()
        title = QLabel("MUSIC VISUALIZER")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setObjectName("green")

        subtitle = QLabel("FFT · WAVEFORM · BEAT DETECTION")
        subtitle.setObjectName("subtitle")
        subtitle.setFont(QFont("Segoe UI", 10))

        header.addWidget(title)
        header.addWidget(subtitle)
        header.addStretch()

        self.btn_load = QPushButton("📂  LOAD FILE")
        self.btn_load.setObjectName("btnLoad")
        self.btn_load.setFont(QFont("Segoe UI", 11))
        self.btn_load.setCursor(Qt.PointingHandCursor)
        header.addWidget(self.btn_load)

        main_layout.addLayout(header)

        # ── Separator ──
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        main_layout.addWidget(sep)

        # ── Track info ──
        self._build_track_info(main_layout)

        # ── Controls ──
        self._build_controls(main_layout)

        # ── Visualizer Grid ──
        self._build_visualizers(main_layout)

        # ── Stats bar ──
        self._build_stats(main_layout)

    def _build_track_info(self, parent_layout):
        row = QHBoxLayout()
        row.setSpacing(16)

        # Ảnh album placeholder
        self.lbl_album = QLabel("♪")
        self.lbl_album.setFixedSize(60, 60)
        self.lbl_album.setAlignment(Qt.AlignCenter)
        self.lbl_album.setFont(QFont("Segoe UI", 24))
        self.lbl_album.setStyleSheet(
            "background:#282828; border-radius:8px; color:#1DB954;"
        )
        row.addWidget(self.lbl_album)

        meta = QVBoxLayout()
        meta.setSpacing(4)
        self.lbl_track = QLabel("Chưa có file nhạc")
        self.lbl_track.setFont(QFont("Segoe UI", 15, QFont.Bold))

        self.lbl_meta = QLabel("Chọn file MP3 / WAV / OGG / FLAC để bắt đầu")
        self.lbl_meta.setObjectName("subtitle")
        self.lbl_meta.setFont(QFont("Segoe UI", 11))

        meta.addWidget(self.lbl_track)
        meta.addWidget(self.lbl_meta)
        row.addLayout(meta)
        row.addStretch()

        parent_layout.addLayout(row)

    def _build_controls(self, parent_layout):
        frame = QWidget()
        frame.setStyleSheet("background:#181818; border-radius:10px; padding:4px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Progress slider
        progress_row = QHBoxLayout()
        self.lbl_current = QLabel("0:00")
        self.lbl_current.setFont(QFont("Segoe UI", 10))
        self.lbl_current.setObjectName("subtitle")
        self.lbl_current.setFixedWidth(36)

        self.sld_progress = QSlider(Qt.Horizontal)
        self.sld_progress.setRange(0, 1000)
        self.sld_progress.setValue(0)
        self.sld_progress.setEnabled(False)
        self.sld_progress.setCursor(Qt.PointingHandCursor)

        self.lbl_total = QLabel("0:00")
        self.lbl_total.setFont(QFont("Segoe UI", 10))
        self.lbl_total.setObjectName("subtitle")
        self.lbl_total.setFixedWidth(36)
        self.lbl_total.setAlignment(Qt.AlignRight)

        progress_row.addWidget(self.lbl_current)
        progress_row.addWidget(self.sld_progress)
        progress_row.addWidget(self.lbl_total)
        layout.addLayout(progress_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        btn_row.setSpacing(12)

        self.btn_stop = QPushButton("■  STOP")
        self.btn_stop.setObjectName("btnSecondary")
        self.btn_stop.setFont(QFont("Segoe UI", 11))
        self.btn_stop.setEnabled(False)
        self.btn_stop.setCursor(Qt.PointingHandCursor)

        self.btn_play = QPushButton("▶  PLAY")
        self.btn_play.setObjectName("btnPlay")
        self.btn_play.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.btn_play.setEnabled(False)
        self.btn_play.setCursor(Qt.PointingHandCursor)

        self.btn_pause = QPushButton("⏸  PAUSE")
        self.btn_pause.setObjectName("btnSecondary")
        self.btn_pause.setFont(QFont("Segoe UI", 11))
        self.btn_pause.setEnabled(False)
        self.btn_pause.setCursor(Qt.PointingHandCursor)

        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_play)
        btn_row.addWidget(self.btn_pause)

        # Volume
        btn_row.addSpacing(20)
        vol_label = QLabel("🔊")
        vol_label.setFont(QFont("Segoe UI", 12))
        self.sld_volume = QSlider(Qt.Horizontal)
        self.sld_volume.setRange(0, 100)
        self.sld_volume.setValue(80)
        self.sld_volume.setFixedWidth(100)
        self.sld_volume.setCursor(Qt.PointingHandCursor)
        self.lbl_vol = QLabel("80%")
        self.lbl_vol.setObjectName("subtitle")
        self.lbl_vol.setFont(QFont("Segoe UI", 10))
        self.lbl_vol.setFixedWidth(34)

        btn_row.addWidget(vol_label)
        btn_row.addWidget(self.sld_volume)
        btn_row.addWidget(self.lbl_vol)

        layout.addLayout(btn_row)
        parent_layout.addWidget(frame)

    def _build_visualizers(self, parent_layout):
        grid = QHBoxLayout()
        grid.setSpacing(12)

        # Spectrum (trái, rộng hơn)
        left = QVBoxLayout()
        lbl_spec = QLabel("FFT Spectrum")
        lbl_spec.setObjectName("green")
        lbl_spec.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.spectrum_widget = SpectrumWidget()
        self.spectrum_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left.addWidget(lbl_spec)
        left.addWidget(self.spectrum_widget)

        # Waveform
        lbl_wave = QLabel("Waveform")
        lbl_wave.setObjectName("green")
        lbl_wave.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.waveform_widget = WaveformWidget()
        self.waveform_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left.addWidget(lbl_wave)
        left.addWidget(self.waveform_widget)

        # Beat (phải)
        right = QVBoxLayout()
        lbl_beat = QLabel("Beat Detection")
        lbl_beat.setObjectName("green")
        lbl_beat.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.beat_widget = BeatWidget()
        self.beat_widget.setFixedWidth(200)
        self.beat_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right.addWidget(lbl_beat)
        right.addWidget(self.beat_widget)
        right.addStretch()

        grid.addLayout(left, 3)
        grid.addLayout(right, 1)
        parent_layout.addLayout(grid, 1)

    def _build_stats(self, parent_layout):
        row = QHBoxLayout()
        row.setSpacing(12)

        for key, label in [("bass", "BASS"), ("mid", "MID"), ("treble", "TREBLE"), ("bpm", "BPM")]:
            card = QWidget()
            card.setStyleSheet("background:#181818; border-radius:8px;")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            card_layout.setSpacing(2)

            val_lbl = QLabel("--")
            val_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
            val_lbl.setObjectName("green")
            val_lbl.setAlignment(Qt.AlignCenter)

            name_lbl = QLabel(label)
            name_lbl.setObjectName("subtitle")
            name_lbl.setFont(QFont("Segoe UI", 9))
            name_lbl.setAlignment(Qt.AlignCenter)

            card_layout.addWidget(val_lbl)
            card_layout.addWidget(name_lbl)
            row.addWidget(card)

            setattr(self, f"stat_{key}", val_lbl)

        parent_layout.addLayout(row)

    # ──────────────────────────────────────────
    #  Signal connections
    # ──────────────────────────────────────────

    def _connect_signals(self):
        self.btn_load.clicked.connect(self._load_file)
        self.btn_play.clicked.connect(self._play)
        self.btn_pause.clicked.connect(self._pause)
        self.btn_stop.clicked.connect(self._stop)
        self.sld_volume.valueChanged.connect(self._change_volume)
        self.sld_progress.sliderPressed.connect(lambda: setattr(self, '_seeking', True))
        self.sld_progress.sliderReleased.connect(self._seek)

        self.player.state_changed.connect(self._on_state_changed)
        self.player.playback_finished.connect(self._on_finished)
        self.detector.beat_detected.connect(self._on_beat)
        self.detector.bpm_updated.connect(self._on_bpm_updated)

    # ──────────────────────────────────────────
    #  Slots / Event handlers
    # ──────────────────────────────────────────

    @pyqtSlot()
    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file nhạc",
            "",
            "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac)"
        )
        if not path:
            return

        self._stop()
        self.lbl_track.setText("Đang load...")
        self.lbl_meta.setText(os.path.basename(path))

        if self.loader.load(path):
            self.player.load(path, self.loader.duration)
            self.detector.reset()

            # Phân tích offline BPM
            self.detector.analyze_offline(self.loader.audio_data, self.loader.sample_rate)

            self.lbl_track.setText(self.loader.file_name)
            self.lbl_meta.setText(
                f"{self.loader.file_size_mb:.1f} MB  ·  "
                f"{fmt_time(self.loader.duration)}  ·  "
                f"{self.loader.sample_rate // 1000}kHz"
            )
            self.lbl_total.setText(fmt_time(self.loader.duration))
            self.sld_progress.setEnabled(True)

            self.btn_play.setEnabled(True)
            self.btn_stop.setEnabled(True)

    @pyqtSlot()
    def _play(self):
        self.player.play()
        self.btn_play.setText("▶  PLAY")
        self.btn_pause.setEnabled(True)

    @pyqtSlot()
    def _pause(self):
        self.player.pause()

    @pyqtSlot()
    def _stop(self):
        self.player.stop()
        self.waveform_widget.clear()
        self.beat_widget.reset()
        self.spectrum_widget.update_spectrum(np.zeros(80))
        self.sld_progress.setValue(0)
        self.lbl_current.setText("0:00")

    @pyqtSlot()
    def _seek(self):
        if self.loader.duration > 0:
            ratio = self.sld_progress.value() / 1000
            seek_to = ratio * self.loader.duration
            self.player.seek(seek_to)
        self._seeking = False

    @pyqtSlot(int)
    def _change_volume(self, value: int):
        self.player.set_volume(value / 100.0)
        self.lbl_vol.setText(f"{value}%")

    @pyqtSlot(str)
    def _on_state_changed(self, state: str):
        if state == "playing":
            self.btn_play.setText("▶  PLAY")
            self._is_playing = True
        elif state == "paused":
            self.btn_pause.setText("▶  RESUME")
            self._is_playing = False
        elif state == "stopped":
            self.btn_pause.setText("⏸  PAUSE")
            self.btn_pause.setEnabled(False)
            self._is_playing = False

    @pyqtSlot()
    def _on_finished(self):
        self._stop()

    @pyqtSlot(float)
    def _on_beat(self, energy: float):
        self.beat_widget.on_beat(energy)

    @pyqtSlot(float)
    def _on_bpm_updated(self, bpm: float):
        self.beat_widget.set_bpm(bpm)
        self.stat_bpm.setText(str(int(bpm)))

    # ──────────────────────────────────────────
    #  Timers
    # ──────────────────────────────────────────

    @pyqtSlot()
    def _update_visualizer(self):
        """Pull audio chunk realtime và update visual"""
        if not self._is_playing or self.loader.audio_data is None:
            return

        pos = self.player.get_position()
        chunk = self.loader.get_chunk(pos, duration_sec=0.05)

        if len(chunk) == 0:
            return

        # FFT
        spectrum = self.fft.compute_fft(chunk)
        bands = self.fft.get_frequency_bands(spectrum)

        # Update visuals
        self.spectrum_widget.update_spectrum(spectrum)
        self.waveform_widget.update_waveform(chunk)

        # Beat detection realtime
        self.detector.process_realtime(spectrum, pos)

        # Update stats
        self.stat_bass.setText(str(int(bands["bass"] * 100)))
        self.stat_mid.setText(str(int(bands["mid"] * 100)))
        self.stat_treble.setText(str(int(bands["treble"] * 100)))

    @pyqtSlot()
    def _update_progress(self):
        if not self._is_playing or self._seeking:
            return
        if self.loader.duration <= 0:
            return

        pos = self.player.get_position()
        self._current_pos = pos
        ratio = min(pos / self.loader.duration, 1.0)

        self.sld_progress.blockSignals(True)
        self.sld_progress.setValue(int(ratio * 1000))
        self.sld_progress.blockSignals(False)
        self.lbl_current.setText(fmt_time(pos))

    def closeEvent(self, event):
        self.player.stop()
        event.accept()