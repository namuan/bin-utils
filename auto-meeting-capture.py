#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "openai-whisper",
#   "PyAudio",
# ]
# ///
import os
import queue
import time
import wave
from datetime import datetime
from threading import Event, Thread

import pyaudio
import whisper  # Assuming openai-whisper is installed


class AudioDevice:
    def __init__(self, name: str, id: int):
        self.name = name
        self.id = id


class Application:
    def __init__(self, output_dir: str = "./audio_chunks"):
        self.devices = []
        self.selected_device = None
        self.recorder_thread = None
        self.transcriber_thread = None
        self.audio_queue = queue.Queue()
        self.stop_event = Event()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def list_devices(self) -> list[AudioDevice]:
        p = pyaudio.PyAudio()
        self.devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:  # Input devices only
                self.devices.append(AudioDevice(info["name"], info["index"]))
        p.terminate()
        return self.devices

    def select_device(self, device_id: int):
        for device in self.devices:
            if device.id == device_id:
                self.selected_device = device
                return
        raise ValueError("Device not found")

    def start(self):
        if not self.selected_device:
            raise ValueError("No device selected")
        self.stop_event.clear()
        self.recorder_thread = AudioRecorderThread(
            self.selected_device, 10, self.output_dir, self.audio_queue, self.stop_event
        )
        self.transcriber_thread = AudioTranscriberThread(self.audio_queue, self.output_dir, self.stop_event)
        self.recorder_thread.start()
        self.transcriber_thread.start()

    def stop(self):
        self.stop_event.set()
        if self.recorder_thread:
            self.recorder_thread.join()
        if self.transcriber_thread:
            self.transcriber_thread.join()


class AudioRecorderThread(Thread):

    def __init__(
        self, device: AudioDevice, chunk_duration: int, output_dir: str, audio_queue: queue.Queue, stop_event: Event
    ):
        super().__init__()
        self.device = device
        self.chunk_duration = chunk_duration
        self.output_dir = output_dir
        self.audio_queue = audio_queue
        self.stop_event = stop_event
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.chunk = 1024

    def run(self):
        p = pyaudio.PyAudio()
        stream = p.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            input_device_index=self.device.id,
            frames_per_buffer=self.chunk,
        )
        while not self.stop_event.is_set():
            file_path = self.record_chunk(stream)
            if file_path:
                self.audio_queue.put(file_path)
        stream.stop_stream()
        stream.close()
        p.terminate()

    def record_chunk(self, stream) -> str:
        frames = []
        start_time = time.time()
        while time.time() - start_time < self.chunk_duration and not self.stop_event.is_set():
            data = stream.read(self.chunk)
            frames.append(data)
        if frames:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(self.output_dir, f"chunk_{timestamp}.wav")
            wf = wave.open(file_path, "wb")
            wf.setnchannels(self.channels)
            wf.setsampwidth(pyaudio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b"".join(frames))
            wf.close()
            return file_path
        return None


class AudioTranscriberThread(Thread):
    def __init__(self, audio_queue: queue.Queue, output_dir: str, stop_event: Event):
        super().__init__()
        self.audio_queue = audio_queue
        self.output_dir = output_dir
        self.stop_event = stop_event
        self.model = whisper.load_model("turbo")  # Load Whisper model, e.g., 'base'

    def run(self):
        while not self.stop_event.is_set() or not self.audio_queue.empty():
            try:
                file_path = self.audio_queue.get(timeout=1)
                text = self.transcribe_audio(file_path)
                self.save_transcription(text, file_path)
            except queue.Empty:
                continue

    def transcribe_audio(self, file_path: str) -> str:
        result = self.model.transcribe(file_path)
        return result["text"]

    def save_transcription(self, text: str, original_file: str):
        base_name = os.path.splitext(os.path.basename(original_file))[0]
        txt_path = os.path.join(self.output_dir, f"{base_name}.txt")
        with open(txt_path, "w") as f:
            f.write(text)


if __name__ == "__main__":
    import sys

    app = Application()

    devices = app.list_devices()

    if not devices:
        print("No audio input devices found.")
        sys.exit(1)

    print("Available devices:")
    for i, device in enumerate(devices):
        print(f"{i}: {device.name} (ID: {device.id})")

    try:
        choice = int(input("Select device by number: "))
        if 0 <= choice < len(devices):
            app.select_device(devices[choice].id)
        else:
            raise ValueError("Invalid choice")
    except ValueError:
        print("Invalid input. Exiting.")
        sys.exit(1)

    input("Press Enter to start recording...")

    app.start()

    print("Recording started. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        app.stop()
