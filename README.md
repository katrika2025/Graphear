# Graphear

Graphear is a small Python application that allows you to hear 2D graphs. The program samples a target function across a range of `x` values, converts the valid `y` values into audio frequencies, and then animates a moving point along the graph while the generated audio plays in sync.

## Features

- Synchronizes sound playback with an animated point on the graph
- Handles problematic values such as `NaN`, `0/0`, and large asymptote spikes
- Supports normal functions, horizontal lines, and a simple vertical line mode
- Keeps the program running when a function produces only undefined values by showing a safe fallback screen

## Main Dependencies

This project mainly depends on:

- `numpy` for numeric arrays, sampling, normalization, and waveform generation
- `matplotlib` for drawing the graph and running the animation
- `sounddevice` for real-time audio playback

## Quick Start

These steps are written for Windows. After cloning this repository to your device, open it in an IDE (e.g. VSCode) and type these commands in the terminal:

### 1. Create a virtual environment

```powershell
py -m venv .venv
```

### 2. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If the script execution is blocked, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate the environment again.

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```
Make sure the 2 files, `requirements.txt` and `graphear.py`, are in the same directory.

### 4. Choose function

Choose one of the built-in 2D mathematical functions or insert your own:
```python
def target_function(x):
    return np.sin(x**2)
    ...
```

You can also test a vertical line with:

```python
def target_function(x):
    return ("vertical", 3)
```

### 5. Run the program

```powershell
py graphear.py
```

When the window opens, the graph will appear and the generated sound will begin when the animation starts.

## Input Validation And Error Handling

Graphear has an explicit validation path so different kinds of bad input are handled in different ways:

- If the function raises a direct `ZeroDivisionError` such as `return np.full_like(x, 0 / 0)`, the program converts that into an all-`NaN` result instead of crashing immediately.
- If the function returns values with the wrong shape, the program raises a `ValueError` because the graph needs one `y` value for each sampled `x` value.
- If the function returns a vertical line tuple like `("vertical", 3)`, the program builds a vertical line instead of a normal `y = f(x)` graph.
- If every point becomes invalid after evaluation and cleanup, the program stays open, shows a message in the plot window, and skips animation/audio playback for that run.
- If the vertical line position is not finite, or if the function raises some other unexpected error, the program raises a `ValueError` with a clear message.

## How The Program Works

In simple terms, Graphear works like this:

1. `target_function(x)` Read a mathematical function.
2. `_evaluate_target_function(self, x_values)` Run the function and catch direct arithmetic failures such as `0/0`.
3. `_prepare_data(self)` Sample many points from that function and clean the result.
4. `_validate_y_values(self, y_values)` Check whether the returned data is shaped correctly and usable.
5. `normalize(arr, new_min, new_max)` Scale the clean graph values into a frequency range.
6. `generate_audio(freqs, sample_rate, duration)` Convert the function values into one smooth audio signal.
7. `_generate_audio_sequence(self)` Build one long audio signal.
8. `_setup_plot(self)` Draw the graph or show a fallback message when no valid points exist.
9. `play(self)` Start playback.
10. `update(self, frame)` Move a point along the curve so the user can both see and hear the function at the same time.

## State Machine Diagram

![Graphear's SMD](out/state_diagram/state_diagram.svg)

## Function And Method Breakdown

### `target_function(x)`

This is the mathematical function the program will visualize and sonify. The default is:

```python
return np.sin(x**2)
```

You can replace this with other functions to create different visual and audio patterns.

You can also use:

```python
return ("vertical", 3)
```

to test the vertical line `x = 3`.

### `AudioVisualizer`

This class declares the initial state of the program. 

It sets the `sample_rate` to 44100, which means the sound is cut into 44,100 data slices (samples) played per second, which is also the standard for CDs. This rate determines the smoothness of the sound; the higher the sample rate, the smoother the audio will be.

It also sets each point on the graph to run for a duration of 0.005 seconds (5ms), meaning each point contains roughly 220.5 audio samples. This duration determines the running speed of the graph: the lower the duration, the faster the animation runs. 

Finally, it prepares the numeric data `_prepare_data()`, converts it to sound `_generate_audio_sequence()`, and sets up the plot `_setup_plot()`.

### `_prepare_data()`

The goal here is to get 2 arrays (`x` and `y`) of the points that need to produce sound. 

First, the mathematical function is received, and we preset an array of 2000 numbers, spread evenly in the range from -15 to 15.

Then, we pass each `x` value into the function to calculate `y`, meaning `y` is also an array of 2000 numbers. This step now goes through `_evaluate_target_function()`, which catches direct division-by-zero cases such as `0/0` and converts them into `NaN` values.

If the function returns `("vertical", value)`, the program builds a vertical line instead. In that case, all `x` values are set to that one value, and the `y` values run from -15 to 15.

Next, we eliminate outliers (like asymptote spikes). We find any `y` elements with an absolute value greater than 10 and assign them as `np.nan` (which stands for "Not a Number" in Python). 

Finally, we filter out these `NaN` values by moving the valid numbers to a clean, new array for audio mapping.

If every point becomes invalid, the program creates a safe fallback version so it can still run. In that case, it marks that there is no real plot data, shows a message on the graph, and avoids trying to animate or play meaningful audio from invalid points.

### `_evaluate_target_function()`

This method runs the user-supplied function inside a `try` block.

If the function contains a direct arithmetic error like:

```python
return np.full_like(x, 0 / 0)
```

Python raises `ZeroDivisionError` before `np.full_like()` can finish. Graphear now catches that exact error and returns an array of `np.nan` values instead.

If some other unexpected error happens, the method raises a cleaner `ValueError` so the program reports a more understandable problem.

### `_validate_y_values()`

This method checks whether the function output can be treated as graph data.

- If the output shape is wrong, it raises an error.
- If the output is fully undefined (`NaN` or infinity everywhere), it passes that result forward so `_prepare_data()` can switch into the safe fallback path instead of crashing immediately.
- If the output is usable, it returns the numeric array normally.

### `_generate_audio_sequence()`

After we've obtained the clean coordinates of the points (free of `NaN`s), we want to generate its audio sequences. This basically turns each of the cleaned `y` values of your function into values to make sound (frequencies) and then generates the audio array from them.

In this code, we normalize the clean `y` values into a frequency range of 150 Hz to 1000 Hz.

### `normalize(arr, new_min, new_max)`

Since we are technically mapping an old range into a new range, we use a mathematical algorithm known as [Min-Max Normalization (or Linear Interpolation/Scaling)](https://apxml.com/courses/intro-feature-engineering/chapter-4-feature-scaling-transformation/normalization-scaling).

It also includes a crucial safety check: if `arr_max` and `arr_min` are the exact same number (meaning your graph is just a straight horizontal line), `arr_max - arr_min` equals 0. If you didn't have this `if` statement to handle the flatline, the formula below it would try to divide by zero, which would instantly crash your entire program.

### `generate_audio(freqs, sample_rate, duration)`

This method creates the full audio signal from the frequencies.

First, it spreads the frequencies smoothly across the whole sound timeline.

Then, it builds one continuous sine wave and applies a fade-in and fade-out envelope so the sound starts and ends smoothly.

The result is one stereo NumPy array with the same sound sent to both ears, and it can be played by `sounddevice`.

### `_setup_plot()`

This method handles all the visuals:

- applies a clean matplotlib style
- creates the figure and axes
- labels the axes
- draws the grid and axis lines
- plots the full function
- creates a red marker point that will move during playback
- displays a message when the current input has no valid graph points
- connects the window close event to `sd.stop()` so audio stops when the window closes

### `play()`

This method starts the full experience:

- creates a `FuncAnimation`
- repeatedly calls `update(frame)`
- opens the matplotlib window with `plt.show()`

### `update(frame)`

This is the animation callback that runs constantly to keep the audio and visuals in perfect sync.

If the current input produced no plottable data, the method returns immediately and leaves the empty graph message in place.

On its very first update, it starts the audio playback and reads timing information from the audio stream itself.

On every frame after that, it measures the elapsed time, divides it by the duration per point (0.005s) to find the current sample index, and moves the red point to the matching `(x, y)` coordinate.

## Future Improvement Ideas

- Allow users to choose functions from a menu
- Add keyboard controls for pause, restart, or speed changes
- Separate audio generation, plotting, and function processing into multiple classes
- Add tests for normalization and data-cleaning behavior
- Export generated audio to a file


