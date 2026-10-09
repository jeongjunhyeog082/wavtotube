import os
import wave
import numpy as np
from typing import Dict, Any, Tuple

PITCH_CLASSES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

class AudioAnalyzer:
    @staticmethod
    def _read_wav_sample(file_path: str, max_seconds: float = 25.0) -> Tuple[np.ndarray, int, float]:
        with wave.open(file_path, 'rb') as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            total_duration = n_frames / float(framerate)

            frames_to_read = min(int(max_seconds * framerate), n_frames)
            raw_bytes = wf.readframes(frames_to_read)

            dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
            dtype = dtype_map.get(sampwidth, np.int16)
            data = np.frombuffer(raw_bytes, dtype=dtype).astype(np.float32)

            if n_channels > 1:
                data = data.reshape(-1, n_channels).mean(axis=1)

            max_val = np.max(np.abs(data))
            if max_val > 0:
                data /= max_val

            return data, framerate, total_duration

    @staticmethod
    def estimate_bpm_numpy(signal: np.ndarray, sr: int) -> float:
        if len(signal) < sr * 2:
            return 120.0

        target_sr = 1000
        step = max(1, sr // target_sr)
        sig_down = signal[::step]
        sr_down = sr // step

        diff = np.diff(np.abs(sig_down))
        envelope = np.maximum(0, diff)

        min_lag = int(sr_down * 60.0 / 200.0)
        max_lag = int(sr_down * 60.0 / 60.0)

        if len(envelope) <= max_lag:
            return 120.0

        lags = np.arange(min_lag, min_lag + min(len(envelope) - max_lag, max_lag - min_lag))
        ref = envelope[:len(lags)]
        corrs = []
        for lag in range(min_lag, max_lag):
            c = np.dot(ref, envelope[lag : lag + len(ref)])
            corrs.append(c)

        if not corrs:
            return 120.0

        best_lag = min_lag + np.argmax(corrs)
        bpm = (60.0 * sr_down) / float(best_lag)

        if bpm < 75:
            bpm *= 2
        elif bpm > 180:
            bpm /= 2

        return round(float(bpm), 1)

    @staticmethod
    def estimate_key_chroma(signal: np.ndarray, sr: int) -> str:
        if len(signal) < 2048:
            return "C Major"

        fft_size = 4096
        hop_size = 2048
        chroma = np.zeros(12, dtype=np.float32)
        f_c0 = 440.0 * (2.0 ** (-57.0 / 12.0))

        num_windows = min(20, (len(signal) - fft_size) // hop_size)
        if num_windows <= 0:
            num_windows = 1

        freqs = np.fft.rfftfreq(fft_size, d=1.0 / sr)

        for w in range(num_windows):
            start = w * hop_size
            window = signal[start : start + fft_size] * np.hanning(fft_size)
            spectrum = np.abs(np.fft.rfft(window))

            for idx, f in enumerate(freqs):
                if 65.0 <= f <= 2000.0:
                    semitone = int(np.round(12.0 * np.log2(f / f_c0))) % 12
                    chroma[semitone] += spectrum[idx]

        norm = np.linalg.norm(chroma)
        if norm > 0:
            chroma /= norm

        best_score = -np.inf
        best_key = "C Major"

        for i in range(12):
            rotated = np.roll(chroma, -i)
            major_corr = np.corrcoef(rotated, MAJOR_PROFILE)[0, 1]
            minor_corr = np.corrcoef(rotated, MINOR_PROFILE)[0, 1]
            if major_corr > best_score:
                best_score = major_corr
                best_key = f"{PITCH_CLASSES[i]} Major"
            if minor_corr > best_score:
                best_score = minor_corr
                best_key = f"{PITCH_CLASSES[i]} Minor"

        return best_key

    @classmethod
    def analyze(cls, file_path: str, max_seconds: float = 25.0) -> Dict[str, Any]:
        try:
            if file_path.lower().endswith(".wav"):
                sig, sr, total_dur = cls._read_wav_sample(file_path, max_seconds=max_seconds)
                bpm = cls.estimate_bpm_numpy(sig, sr)
                key = cls.estimate_key_chroma(sig, sr)
                return {
                    "bpm": bpm,
                    "key": key,
                    "duration": round(total_dur, 1),
                    "engine": "fast_numpy"
                }

            try:
                import librosa
                y, sr = librosa.load(file_path, sr=22050, duration=max_seconds)
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                bpm = round(float(tempo[0] if isinstance(tempo, (list, np.ndarray)) else tempo), 1)
                
                chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
                chroma_avg = np.mean(chroma, axis=1)
                best_score = -np.inf
                best_key = "C Major"
                for i in range(12):
                    rotated = np.roll(chroma_avg, -i)
                    major_corr = np.corrcoef(rotated, MAJOR_PROFILE)[0, 1]
                    minor_corr = np.corrcoef(rotated, MINOR_PROFILE)[0, 1]
                    if major_corr > best_score:
                        best_score = major_corr
                        best_key = f"{PITCH_CLASSES[i]} Major"
                    if minor_corr > best_score:
                        best_score = minor_corr
                        best_key = f"{PITCH_CLASSES[i]} Minor"
                
                duration = round(librosa.get_duration(path=file_path), 1)
                return {"bpm": bpm, "key": best_key, "duration": duration, "engine": "librosa"}
            except ImportError:
                return {"bpm": 120.0, "key": "C Major", "duration": 180.0, "engine": "fallback"}

        except Exception as e:
            return {"bpm": 120.0, "key": "C Major", "duration": 180.0, "error": str(e)}