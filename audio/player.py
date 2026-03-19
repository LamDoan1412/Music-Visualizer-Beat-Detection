"""
audio/player.py
Xử lý phát nhạc: load file, play, pause, stop, seek
Sử dụng pygame.mixer để phát âm thanh
"""

import pygame
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal


class AudioPlayer(QObject):
    # Signals để thông báo trạng thái cho UI
    position_changed = pyqtSignal(float)   # vị trí hiện tại (giây)
    playback_finished = pyqtSignal()       # khi nhạc kết thúc
    state_changed = pyqtSignal(str)        # "playing" | "paused" | "stopped"

    def __init__(self):
        super().__init__()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        self.file_path = None
        self.duration = 0.0
        self.is_playing = False
        self.is_paused = False
        self._position = 0.0
        self._start_time = 0.0
        self._pause_offset = 0.0

        # Thread theo dõi vị trí
        self._monitor_thread = None
        self._stop_monitor = False

    def load(self, file_path: str, duration: float):
        """Load file nhạc vào player"""
        self.stop()
        self.file_path = file_path
        self.duration = duration
        pygame.mixer.music.load(file_path)
        self._position = 0.0
        self._pause_offset = 0.0

    def play(self):
        """Phát nhạc từ vị trí hiện tại"""
        if self.file_path is None:
            return

        pygame.mixer.music.play(start=self._pause_offset)
        self._start_time = time.time() - self._pause_offset
        self.is_playing = True
        self.is_paused = False
        self.state_changed.emit("playing")

        # Khởi động thread monitor
        self._stop_monitor = False
        self._monitor_thread = threading.Thread(target=self._monitor_position, daemon=True)
        self._monitor_thread.start()

    def pause(self):
        """Tạm dừng / tiếp tục phát"""
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self._pause_offset = time.time() - self._start_time
            self.is_paused = True
            self.state_changed.emit("paused")
        elif self.is_paused:
            pygame.mixer.music.unpause()
            self._start_time = time.time() - self._pause_offset
            self.is_paused = False
            self.state_changed.emit("playing")

    def stop(self):
        """Dừng hoàn toàn"""
        self._stop_monitor = True
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self._position = 0.0
        self._pause_offset = 0.0
        self.state_changed.emit("stopped")

    def seek(self, seconds: float):
        """Seek đến vị trí cụ thể (giây)"""
        self._pause_offset = max(0, min(seconds, self.duration))
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.play(start=self._pause_offset)
            self._start_time = time.time() - self._pause_offset

    def set_volume(self, volume: float):
        """Đặt âm lượng (0.0 đến 1.0)"""
        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))

    def get_position(self) -> float:
        """Lấy vị trí phát hiện tại (giây)"""
        if self.is_playing and not self.is_paused:
            return time.time() - self._start_time
        return self._pause_offset

    def _monitor_position(self):
        """Thread theo dõi vị trí và phát hiện kết thúc"""
        while not self._stop_monitor:
            if self.is_playing and not self.is_paused:
                pos = time.time() - self._start_time
                self._position = pos
                self.position_changed.emit(pos)

                # Kiểm tra kết thúc
                if not pygame.mixer.music.get_busy() and not self.is_paused:
                    self.is_playing = False
                    self.playback_finished.emit()
                    break

            time.sleep(0.05)  # Update 20 lần/giây