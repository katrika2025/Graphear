import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import sounddevice as sd


class AudioVisualizer:
    """Main class that handles graphing and sound."""



    def __init__(self, target_function):
        """Initialize the visualizer state, data, audio, and plot objects."""
        self.f = target_function
        self.sample_rate = 44100  # audio samples played each second.
        self.duration = 0.005  # how long each tone slice lasts in seconds.
        self.animation_interval_ms = max(1, int(round(self.duration * 1000)))  # Match the animation speed to the audio slice length.

        self.audio_started = False
        self.has_plot_data = True  # Track whether the current function produced visible graph points.

        self.audio_stream = None  # An object referring to the active audio stream.
        self.audio_stream_start_time = 0.0  # Remember when the audio stream started.
        self.audio_latency = 0.0  # Store the audio output delay reported by the device.

        self._prepare_data()  # Build the x and y values for the graph.
        self._generate_audio_sequence()  # Create the audio from the graph values.
        self._setup_plot()  # Prepare the figure, axes, and moving point.



    def _use_no_plot_fallback(self, x_values):
        """Set a safe fallback state when the input cannot produce usable graph data."""
        self.has_plot_data = False
        self.x_vals = np.array(x_values, dtype=float) # Store the attempted x-values so the axes can still be scaled to the correct range.
        self.y_vals = np.full_like(self.x_vals, np.nan, dtype=float) # Fill all y-values with NaN to prevent plotting.
        self.x_clean = np.array([0.0]) # Set a default point for the animation, though it won't be visible.
        self.y_clean = np.array([0.0])



    def normalize(self, arr, new_min, new_max):
        """Rescales numbers into a new range."""
        arr = arr[~np.isnan(arr)]  # Remove any NaN values before scaling.
        if arr.size == 0:  # Check whether any valid values are left.
            return np.array([])  # Return an empty array when there is nothing to scale.

        arr_min = np.min(arr)  # Find the smallest value in the array.
        arr_max = np.max(arr)  # Find the largest value in the array.
        if arr_max - arr_min == 0:  # Check whether all values are the same.
            return np.full_like(arr, (new_min + new_max) / 2)  # Fill the result with the middle of the new range.

        return new_min + (arr - arr_min) * (new_max - new_min) / (arr_max - arr_min)  # Convert each value into the target range.



    def generate_audio(self, freqs, sample_rate, duration):
        """turns frequencies into sound."""
        if len(freqs) == 0:  # Check whether there are any frequencies to play.
            return np.zeros((0, 2))  # Return empty stereo audio when nothing exists.

        # How many audio samples?
        samples_per_step = max(1, int(sample_rate * duration))  # Calculate how many samples belong to each graph point. (44100*0.005=~220.5 samples/point)
        total_samples = (len(freqs) * samples_per_step)  # Calculate the total number of output samples. (2000*220 = 440,000 samples for the whole graph)

        # Smooth out by interpolating frequencies across the full sample count
        source_positions = np.arange(len(freqs))  # Create an array of positions corresponding to each original frequency point. (0, 1, 2, ..., 1999)
        target_positions = np.linspace(0, len(freqs) - 1, total_samples)  # Spread positions across the full sample count.
        smooth_freqs = np.interp(target_positions, source_positions, freqs)  # new_val = np.interp(new_freq_pos, old_freq_pos, old_val)

        # Synthesis with sine wave
        phase = (2 * np.pi * np.cumsum(smooth_freqs) / sample_rate)  # Build a continuous phase so the waveform stays smooth.
        wave = 0.2 * np.sin(phase)  # Create a sine wave at a safe volume.

        # Add fade in and out
        fade = np.ones(total_samples)  # Create a fade envelope that starts fully on.
        edge_size = min(samples_per_step * 4, total_samples // 2)  # Define how many samples the fade should last, but don't let it exceed half the total audio length.
        if edge_size > 0:  # Check whether a fade should be applied.
            fade[:edge_size] = np.linspace(0, 1, edge_size)  # Fade in the start of the sound.
            fade[-edge_size:] = np.linspace(1, 0, edge_size)  # Fade out the end of the sound.

        # Left and right channels distribution
        wave = wave * fade  # Apply the fade envelope to the waveform.
        return np.column_stack((wave, wave))  # Duplicate the waveform into left and right channels.



    def _evaluate_target_function(self, x_values):
        """Run the input function and handle error."""
        try:
            return self.f(x_values)  # Return the function output for the given x-values.
        except Exception:
            return np.full_like(x_values, np.nan, dtype=float)



    def _validate_y_values(self, y_values):
        """Check the returned y-values and handle errors."""
        y_array = np.asarray(y_values, dtype=float)  # Convert the result into a numeric NumPy array.
        if (y_array.shape != self.x_vals.shape):  # Check whether the result matches the x-value count.
            raise ValueError("Invalid function input: the expression must return one y-value for each x-value.")
        return y_array  # Return the cleaned numeric array.



    def _prepare_data(self):
        """Sample the function, validate it, and keep only plottable graph points."""
        default_x = np.linspace(-15, 15, 2000)  # Create the default x-range for the graph.
        try:
            result = self._evaluate_target_function(default_x) 

            if (
                isinstance(result, tuple)
                and len(result) == 2
                and result[0] == "vertical"
            ):  
                x_position = float(result[1])  # Convert the vertical line position into a number.
                if not np.isfinite(x_position):  # Check whether the vertical line position is valid.
                    self._use_no_plot_fallback(default_x)
                    return
                self.x_vals = np.full(2000, x_position)  # Fill all x-values with the same vertical line position.
                self.y_vals = np.linspace(-15, 15, 2000)  # Create y-values that span the visible graph height.
            else:  # Handle the normal y = f(x) case.
                self.x_vals = default_x  # Store the default x-values.
                self.y_vals = self._validate_y_values(result)  # Validate and store the computed y-values.
        except ValueError:
            self._use_no_plot_fallback(default_x)
            return

        self.y_vals[np.abs(self.y_vals) > 10] = np.nan  # Replace very large spikes with NaN to hide asymptotes.

        nan = np.isnan(self.y_vals)  # Mark every invalid y-value.
        self.x_clean = self.x_vals[~nan]  # Keep only x-values that pair with valid y-values.
        self.y_clean = self.y_vals[~nan]  # Keep only valid y-values.

        if self.x_clean.size == 0:  # Check whether any plottable points remain.
            self._use_no_plot_fallback(self.x_vals)



    def _generate_audio_sequence(self):
        """Map cleaned graph values into frequencies and synthesize the final audio array."""
        self.freqs = self.normalize(self.y_clean, 150, 1000)  # Convert y-values into a frequency range [150, 1000].
        self.audio = self.generate_audio(self.freqs, self.sample_rate, self.duration)  # Build the final audio waveform from those frequencies.



    def _setup_plot(self):
        """Create and style the Matplotlib window."""
        plt.style.use("seaborn-v0_8-whitegrid")  # Apply a built-in plotting style.
        self.fig, self.ax = plt.subplots(figsize=(9, 5))  # Create the figure and axes.
        self.fig.patch.set_facecolor("#FFFFFF")  # Set the figure background color.
        self.ax.set_facecolor("#F8F9FA")  # Set the plot area background color.

        self.ax.set_xlabel("x", fontsize=11, color="#333333", labelpad=6)  # Label the x-axis.
        self.ax.set_ylabel("f(x)", fontsize=11, color="#333333", labelpad=6)  # Label the y-axis.

        self.ax.grid(  # Configure the visible grid.
            True,  # Enable the grid.
            which="major",  # Show the main grid lines.
            linestyle="-",  # Draw solid grid lines.
            linewidth=0.7,  # Set the line thickness.
            color="#D0D0E0",  # Set the grid color.
            alpha=0.9,  # Set the grid transparency.
        )
        self.ax.minorticks_on()  # Show smaller tick marks between major ticks.
        self.ax.axhline(0, color="#AAAACC", linewidth=0.8, zorder=1)  # Draw the horizontal axis line.
        self.ax.axvline(0, color="#AAAACC", linewidth=0.8, zorder=1)  # Draw the vertical axis line.

        self.fig.canvas.mpl_connect("close_event", lambda event: sd.stop())  # Stop audio when the plot window closes.

        self.ax.plot(self.x_vals, self.y_vals, color="#2563EB", linewidth=1.5, zorder=2)  # Draw the full graph line.
        (self.point,) = self.ax.plot([], [], "o", color="#EF4444", markersize=7, zorder=3)  # Create the moving red point.

        if (not self.has_plot_data):  # Check whether the function produced any visible points.
            self.ax.text(
                0.5,
                0.5,
                "No valid graph points for this input",
                transform=self.ax.transAxes,
                ha="center",
                va="center",
                color="#B91C1C",
                fontsize=12,
            )  # Show a clear message when the function is fully undefined.

        self.ax.set_xlim(self.x_vals.min(), self.x_vals.max())  # Match the x-axis limits to the sampled data.
        self.fig.tight_layout()  # Adjust spacing so labels fit nicely.



    def update(self, frame):
        """Move the red dot so it follows the current audio playback position."""
        if not self.has_plot_data:  # Check whether there is any valid point to animate.
            return (self.point,)  # Keep the empty marker unchanged when no graph data exists.

        if not self.audio_started:  # Check whether playback has already begun.
            sd.play(self.audio, samplerate=self.sample_rate, latency="low")  # Start playing the generated audio.
            self.audio_stream = (sd.get_stream())  # Read the active stream so timing can be tracked.
            self.audio_stream_start_time = getattr(self.audio_stream, "time", 0.0) # Store the stream's starting clock value, or zero if unavailable.
            self.audio_latency = getattr(self.audio_stream, "latency", 0.0) # Store the reported output latency, or zero if unavailable.

            self.audio_started = True  # Mark the audio as started.

        elapsed_time = max(  # Compute how much audible playback time has passed.
            0.0,  # Prevent negative playback time.
            self.audio_stream.time
            - self.audio_stream_start_time
            - self.audio_latency,  # Subtract the start time and delay from the current stream time.
        )
        current_index = int(elapsed_time / self.duration)  # Convert elapsed time into the current graph index.

        if current_index >= len(self.x_clean):  # Check whether playback has reached the end.
            current_index = (len(self.x_clean) - 1)  # Clamp the index to the last valid point.

        x = self.x_clean[current_index]  # Read the current x-value.
        y = self.y_clean[current_index]  # Read the current y-value.
        self.point.set_data([x], [y])  # Move the red point to the current graph position.

        return (self.point,)  # Return the updated artist for efficient animation.

    def play(self):
        """Create the animation loop and open the interactive window."""
        self.ani = FuncAnimation(  # Create the animation object.
            self.fig,  # Use the prepared figure.
            self.update,  # Call the update method each frame.
            interval=self.animation_interval_ms,  # Set the frame interval in milliseconds.
            blit=True,  # Redraw only changed artists for speed.
            cache_frame_data=False,  # Avoid storing all animation frames in memory.
        )
        plt.show()  # Open the graph window and start the event loop.


def target_function(x):
    """Input the graph formula to visualize and sonify."""
    # Desmos: https://www.desmos.com/calculator/lzc5jdirrq

    # return np.full_like(x, 0 / 0)  # invalid values on purpose
    # return np.sin(x**2)  # WOWOWOWOW
    return np.sin(x)  # sine-wave function.
    # return np.e**x  # exponential curve
    # return np.log10(x)    #  logarithmic curve
    # return -(x % 1.5)    #  repeating ramp pattern
    # return np.floor(x * 2)    # step pattern
    # return np.sign(np.sin(4 * x))    # square-wave-like pattern
    # return np.full_like(x, 3.0)    # flat horizontal line
    # return ("vertical", np.log10(-4))  # vertical line request
    # return np.full_like(x, np.log10(-5))
    # return 2 * x    # straight sloped line
    # return np.tan(x)    # tangent curve with asymptotes
    # return np.sin(15 * x) * np.exp(-np.abs(x))    # damped fast wave
    # return np.sin(x) * np.sin(x**2)    # layered oscillating pattern
    # return np.sin(15 * x) * np.cos(x) * x / 5    # mixed modulated wave
    # return np.where(x == 0, 0, np.sin(1 / x)) # curve that changes rapidly near zero
    # return np.where(np.abs(x) < 1, np.nan, np.sin(x)) # NaN in the center region


result = AudioVisualizer(target_function)
result.play()
