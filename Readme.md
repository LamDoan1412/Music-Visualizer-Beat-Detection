# 🎵 Music Visualizer + Beat Detection

Ứng dụng phát nhạc kết hợp phân tích tín hiệu âm thanh realtime — phong cách Spotify.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15-green)
![librosa](https://img.shields.io/badge/librosa-0.10-orange)

---

## ✨ Tính năng

| Tính năng | Mô tả |
|-----------|-------|
| 🎵 **Audio Player** | Phát MP3, WAV, OGG, FLAC với Play/Pause/Stop/Seek |
| 📊 **FFT Spectrum** | 80 cột tần số realtime, phân 3 dải Bass/Mid/Treble |
| 〰️ **Waveform** | Hiển thị tín hiệu thời gian realtime |
| 🥁 **Beat Detection** | Phát hiện nhịp realtime + phân tích offline (librosa) |
| 🎆 **Beat Visual** | Hiệu ứng pulse + ring khi có nhịp |
| 📈 **BPM Counter** | Đếm BPM tự động |

---

## 📐 Kỹ thuật DSP

### FFT (Fast Fourier Transform)
```
Xk = Σ(n=0 → N-1)  x_n · e^(-i·2π·k·n/N)
```
- Chuyển tín hiệu từ **miền thời gian → miền tần số**
- Dùng `numpy.fft.rfft` + Hann window để giảm spectral leakage
- Scale về dB: `20 · log10(|X|)`

### Beat Detection (Realtime)
```
C = -0.0025714 · variance + 1.5142857
threshold = C · avg_energy
beat = (energy > threshold) AND (energy > 0.1) AND (Δt > min_interval)
```

### Beat Detection (Offline)
```python
tempo, beats = librosa.beat.beat_track(y=audio, sr=sr)
```

---

## 🗂️ Cấu trúc project

```
music_visualizer/
│
├── main.py                     # Entry point
├── requirements.txt
├── README.md
│
├── audio/
│   ├── loader.py               # Load file âm thanh (librosa)
│   └── player.py               # Phát nhạc (pygame.mixer)
│
├── analysis/
│   ├── fft_analyzer.py         # Tính FFT + dải tần
│   └── beat_detector.py        # Phát hiện nhịp
│
├── visual/
│   ├── spectrum_widget.py      # Widget FFT spectrum
│   ├── waveform_widget.py      # Widget waveform
│   └── beat_widget.py          # Widget beat animation
│
├── ui/
│   └── main_window.py          # Cửa sổ chính PyQt5
│
└── assets/                     # Icon, âm thanh mẫu
```

---

## 🚀 Cài đặt & Chạy

### 1. Clone repo
```bash
git clone https://github.com/LamDoan1412/Music-Visualizer-Beat-Detection.git
cd Music-Visualizer-Beat-Detection
```

### 2. Tạo virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux
```

### 3. Cài thư viện
```bash
pip install -r requirements.txt
```

> ⚠️ **Lưu ý**: `librosa` cần `ffmpeg` để đọc MP3.  
> Cài ffmpeg: https://ffmpeg.org/download.html hoặc `conda install ffmpeg`

### 4. Chạy ứng dụng
```bash
python main.py
```

---

## 👥 Phân công nhóm

| Thành viên | Phần đảm nhận |
|-----------|---------------|
| Người 1 | `audio/player.py` — Phát nhạc, điều khiển |
| Người 2 | `analysis/fft_analyzer.py` — Xử lý FFT |
| Người 3 | `analysis/beat_detector.py` — Beat detection |
| Người 4 | `visual/` — Spectrum, Waveform, Beat widget |
| Người 5 | `ui/main_window.py` — Giao diện PyQt5 |

---

## 📅 Timeline

- **Tuần 1**: Player + Loader + Waveform cơ bản
- **Tuần 2**: FFT + Spectrum + Beat detection
- **Tuần 3**: Visual effects + UI hoàn chỉnh + Demo

---

## 🛠️ Tech Stack

- **Python 3.12**
- **PyQt5** — GUI framework
- **pygame** — Audio playback
- **librosa** — Audio analysis & beat tracking
- **numpy / scipy** — DSP & FFT