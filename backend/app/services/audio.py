import sounddevice as sd
import numpy as np
import torch
from faster_whisper import WhisperModel
import queue
import threading
import logging
import time
from typing import List, Optional, Callable, Set

logger = logging.getLogger(__name__)

class DeviceListener:
    def __init__(self, device_index: int, sample_rate: int, transcribe_callback: Callable):
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.transcribe_callback = transcribe_callback
        
        # Load VAD per listener for thread safety
        self.vad_model, _ = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', trust_repo=True)
        self.vad_model.reset_states()
        
        self.queue = queue.Queue()
        self.is_listening = False
        self.vad_buffer = []
        self.speech_buffer = []
        self.is_speaking = False
        self.silence_chunks = 0
        self.max_silence_chunks = 30  # ~1 sec
        self.vad_threshold = 0.5
        
    def start(self):
        self.is_listening = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        self.is_listening = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)

    def _callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio status (Device {self.device_index}): {status}")
        self.queue.put(indata.copy())

    def _loop(self):
        logger.info(f"Starting listener on device index: {self.device_index}")
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, 
                              callback=self._callback, device=self.device_index):
                while self.is_listening:
                    while not self.queue.empty():
                        self._process(self.queue.get())
                    time.sleep(0.05)
        except Exception as e:
            logger.error(f"Stream error on device {self.device_index}: {e}")
            self.is_listening = False

    def _process(self, data):
        # Downmix if needed (though channels=1 in InputStream should handle it)
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
            
        self.vad_buffer.extend(data.tolist())
        
        while len(self.vad_buffer) >= 512:
            chunk = self.vad_buffer[:512]
            self.vad_buffer = self.vad_buffer[512:]
            
            tensor = torch.tensor(chunk, dtype=torch.float32)
            speech_prob = self.vad_model(tensor, self.sample_rate).item()
            
            if speech_prob > self.vad_threshold:
                self.is_speaking = True
                self.silence_chunks = 0
                self.speech_buffer.extend(chunk)
            elif self.is_speaking:
                self.speech_buffer.extend(chunk)
                self.silence_chunks += 1
                if self.silence_chunks > self.max_silence_chunks:
                    self.is_speaking = False
                    if len(self.speech_buffer) > self.sample_rate * 0.5:
                        self.transcribe_callback(np.array(self.speech_buffer))
                    self.speech_buffer = []
                    self.vad_model.reset_states()

class AudioService:
    def __init__(self, model_size="tiny", device="cpu"):
        self.model = WhisperModel(model_size, device=device, compute_type="int8")
        self.listeners: List[DeviceListener] = []
        self.lock = threading.Lock()
        self.callback = None

    def start_listening(self, callback: Callable):
        if self.listeners: return
        
        self.callback = callback
        devices = self._get_input_devices()
        logger.info(f"Initializing listeners for devices: {devices}")
        
        for dev_idx in devices:
            try:
                listener = DeviceListener(dev_idx, 16000, self._transcribe)
                listener.start()
                self.listeners.append(listener)
            except Exception as e:
                logger.error(f"Failed to start listener for device {dev_idx}: {e}")

    def stop_listening(self):
        for l in self.listeners:
            l.stop()
        self.listeners.clear()
        logger.info("Audio service stopped.")

    def _transcribe(self, audio_data):
        with self.lock:
            try:
                # Flatten and ensure float32
                audio_data = audio_data.flatten().astype(np.float32)
                segments, _ = self.model.transcribe(audio_data, beam_size=5)
                text = " ".join([s.text for s in segments]).strip()
                
                if text and self.callback:
                    logger.info(f"Transcribed: {text}")
                    self.callback(text)
            except Exception as e:
                logger.error(f"Transcription error: {e}")

    def _get_input_devices(self) -> List[int]:
        """Returns unique list of input device indices (Default + Loopbacks)."""
        device_indices = set()
        
        # 1. Default Input
        try:
            def_idx = sd.default.device[0]
            if def_idx is not None and def_idx >= 0:
                device_indices.add(def_idx)
        except Exception as e:
            logger.warning(f"Could not get default device: {e}")

        # 2. Loopback/Virtual Devices
        targets = {'blackhole', 'vb-cable', 'loopback'}
        try:
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    name = dev['name'].lower()
                    if any(t in name for t in targets):
                        device_indices.add(i)
        except Exception as e:
            logger.error(f"Error querying devices: {e}")
            
        return list(device_indices)
