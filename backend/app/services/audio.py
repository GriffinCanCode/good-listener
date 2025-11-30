import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import queue
import threading
import logging
import time

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self, model_size="tiny", device="cpu"):
        self.model = WhisperModel(model_size, device=device, compute_type="int8")
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.sample_rate = 16000
        self.channels = 1
        self.using_system_audio = False
        self.device_index = self._find_loopback_device()
        
        # VAD / Buffer settings
        self.buffer = []
        self.silence_threshold = 0.01 
        self.silence_duration = 1.0 
        self.last_sound_time = time.time()

    def _find_loopback_device(self):
        """Auto-detects BlackHole, Loopback, or Aggregate devices."""
        try:
            targets = {'blackhole', 'vb-cable', 'loopback', 'aggregate'}
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0 and any(t in dev['name'].lower() for t in targets):
                    logger.info(f"Found audio device: {dev['name']} (Index {i})")
                    self.using_system_audio = True
                    return i
            
            logger.warning("No specific loopback device found. Using default input.")
            return None
        except Exception as e:
            logger.error(f"Error finding audio device: {e}")
            return None

    def start_listening(self, callback):
        if self.is_listening:
            return

        self.is_listening = True
        self.callback = callback
        self.stream_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.stream_thread.start()
        logger.info("Audio service started.")

    def stop_listening(self):
        self.is_listening = False
        logger.info("Audio service stopped.")

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())

    def _audio_loop(self):
        try:
            stream_params = {
                'samplerate': self.sample_rate,
                'channels': self.channels,
                'callback': self._audio_callback,
                **({'device': self.device_index} if self.device_index is not None else {})
            }
            
            with sd.InputStream(**stream_params):
                logger.info(f"Listening on device: {self.device_index if self.device_index is not None else 'Default'}")
                while self.is_listening:
                    while not self.audio_queue.empty():
                        self._process_chunk(self.audio_queue.get())
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in audio loop: {e}")
            self.is_listening = False

    def _process_chunk(self, data):
        # Downmix to mono if needed (though we request 1 channel)
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
            
        amplitude = np.max(np.abs(data))
        self.buffer.append(data)
        
        if amplitude > self.silence_threshold:
            self.last_sound_time = time.time()
        
        if (time.time() - self.last_sound_time > self.silence_duration) and len(self.buffer) > 0:
            full_audio = np.concatenate(self.buffer)
            self.buffer = [] 
            
            if len(full_audio) > self.sample_rate * 0.5: 
                self._transcribe(full_audio)

    def _transcribe(self, audio_data):
        audio_data = audio_data.flatten().astype(np.float32)
        try:
            segments, info = self.model.transcribe(audio_data, beam_size=5)
            full_text = " ".join([segment.text for segment in segments]).strip()
            
            if full_text:
                logger.info(f"Transcribed: {full_text}")
                if self.callback:
                    self.callback(full_text)
        except Exception as e:
            logger.error(f"Transcription error: {e}")
