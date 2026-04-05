import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import sounddevice as sd
import time


class AudioVisualizer:

    def __init__(self, target_function):
        self.f = target_function
        self.sample_rate = 44100
        self.duration = 0.005

        # Sync states
        self.audio_started = False
        self.start_time = 0

        # Prepare Data
        self._prepare_data()
        self._generate_audio_sequence()
        self._setup_plot()

    def normalize(self, arr, new_min, new_max):
        arr = arr[~np.isnan(arr)]
        arr_min = np.min(arr)
        arr_max = np.max(arr)
        if arr_max - arr_min == 0:
            return np.full_like(arr, (new_min + new_max) / 2)
        return new_min + (arr - arr_min) * (new_max - new_min) / (arr_max - arr_min)

    def generate_audio(self, freqs, sample_rate, duration):
        audio = []
        for freq in freqs:
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            wave = np.sin(2 * np.pi * freq * t)
            envelope = np.linspace(0, 1, len(wave))
            wave = wave * envelope * (1 - envelope)
            audio.extend(wave)
        return np.array(audio)

    def _prepare_data(self):
        self.x_vals = np.linspace(-15, 15, 2000)
        self.y_vals = self.f(self.x_vals)

        # kill asymptote spikes
        self.y_vals[np.abs(self.y_vals) > 10] = np.nan

        # remove NaNs for audio mapping
        nan = np.isnan(self.y_vals)
        self.x_clean = self.x_vals[~nan]
        self.y_clean = self.y_vals[~nan]

    def _generate_audio_sequence(self):
        self.freqs = self.normalize(self.y_clean, 150, 1000)
        self.audio = self.generate_audio(self.freqs, self.sample_rate, self.duration)

    def _setup_plot(self):
        plt.style.use("seaborn-v0_8-whitegrid")
        self.fig, self.ax = plt.subplots(figsize=(9, 5))
        self.fig.patch.set_facecolor("#FFFFFF")
        self.ax.set_facecolor("#F8F9FA")

        self.ax.set_xlabel("x", fontsize=11, color="#333333", labelpad=6)
        self.ax.set_ylabel("f(x)", fontsize=11, color="#333333", labelpad=6)

        self.ax.grid(
            True,
            which="major",
            linestyle="-",
            linewidth=0.7,
            color="#D0D0E0",
            alpha=0.9,
        )
        self.ax.minorticks_on()
        self.ax.axhline(0, color="#AAAACC", linewidth=0.8, zorder=1)
        self.ax.axvline(0, color="#AAAACC", linewidth=0.8, zorder=1)

        self.fig.canvas.mpl_connect("close_event", lambda event: sd.stop())

        self.ax.plot(self.x_vals, self.y_vals, color="#2563EB", linewidth=1.5, zorder=2)
        (self.point,) = self.ax.plot(
            [], [], "o", color="#EF4444", markersize=7, zorder=3
        )

        self.ax.set_xlim(self.x_vals.min(), self.x_vals.max())
        self.fig.tight_layout()

    def update(self, frame):
        if not self.audio_started:
            sd.play(self.audio, samplerate=self.sample_rate)
            self.start_time = time.perf_counter()
            self.audio_started = True

        elapsed_time = time.perf_counter() - self.start_time
        current_index = int(elapsed_time / self.duration)

        if current_index >= len(self.x_clean):
            current_index = len(self.x_clean) - 1

        x = self.x_clean[current_index]
        y = self.y_clean[current_index]
        self.point.set_data([x], [y])

        return (self.point,)

    def play(self):
        self.ani = FuncAnimation(
            self.fig, self.update, interval=20, blit=True, cache_frame_data=False
        )
        plt.show()


# -----------------------
# Execution
# -----------------------


def target_function(x):
    return np.sin(x**2)  # wowowowowowowowowow
    # return -(x % 1.5)  # SFX triangle
    # return np.floor(x * 2)  # SFC stair
    # return np.sign(np.sin(4 * x))  # Police Siren

    # return np.sin(15 * x) * np.exp(-np.abs(x))
    # return np.sin(x) * np.sin(x**2)
    # return np.tan(x)
    # return np.sin(x) * np.cos(5 * x) * x / 5


result = AudioVisualizer(target_function)
result.play()
