"""Kaldi-compatible log-Mel filterbanks and ONNX speaker embeddings."""

from __future__ import annotations

import numpy as np

EPS_LOG = 5.19247102e-01
SAMPLE_RATE = 16000


def _mel(f: np.ndarray | float) -> np.ndarray | float:
    return 1127.0 * np.log(1.0 + np.asarray(f, dtype=np.float64) / 700.0)


def _mel_filterbank(n_mels: int, nfft: int, sample_rate: int, low_freq: float, high_freq: float) -> np.ndarray:
    num_bins = nfft // 2
    nyquist = sample_rate / 2.0
    if high_freq <= 0:
        high_freq += nyquist
    bin_width = sample_rate / float(nfft)
    mel_low, mel_high = float(_mel(low_freq)), float(_mel(high_freq))
    mel_delta = (mel_high - mel_low) / (n_mels + 1)

    bins = np.zeros((n_mels, num_bins), dtype=np.float64)
    start = int(round(mel_low / mel_delta))
    for i in range(n_mels):
        left = mel_low + i * mel_delta
        center = left + mel_delta
        right = center + mel_delta
        for j in range(start, num_bins):
            m = float(_mel(j * bin_width))
            if m > right:
                break
            if left <= m <= center:
                weight = (m - left) / mel_delta
            elif center < m <= right:
                weight = (right - m) / mel_delta
            else:
                weight = 0.0
            bins[i, j] = weight
        start = int(round(3 * mel_delta / bin_width))
    return bins


def kaldi_fbank(
    wave: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
    n_mels: int = 80,
    frame_ms: float = 25.0,
    shift_ms: float = 10.0,
    window_type: str = "povey",
    preemph: float = 0.97,
    low_freq: float = 20.0,
    high_freq: float = 0.0,
) -> np.ndarray:
    wave = np.asarray(wave, dtype=np.float64)
    frame_len = int(round(sample_rate * frame_ms / 1000.0))
    frame_shift = int(round(sample_rate * shift_ms / 1000.0))
    if len(wave) < frame_len:
        wave = np.pad(wave, (0, frame_len - len(wave)))

    num_frames = 1 + (len(wave) - frame_len) // frame_shift
    idx = np.arange(frame_len)[None, :] + frame_shift * np.arange(num_frames)[:, None]
    frames = wave[idx]
    frames = frames - frames.mean(axis=1, keepdims=True)
    frames[:, 1:] -= preemph * frames[:, :-1]

    phase = 2.0 * np.pi * np.arange(frame_len) / (frame_len - 1)
    if window_type == "hamming":
        window = 0.54 - 0.46 * np.cos(phase)
    elif window_type == "hanning":
        window = 0.5 - 0.5 * np.cos(phase)
    else:
        window = (0.5 - 0.5 * np.cos(phase)) ** 0.85
    frames *= window

    nfft = 1
    while nfft < frame_len:
        nfft *= 2
    spectrum = np.fft.rfft(frames, n=nfft, axis=1)
    power = spectrum.real**2 + spectrum.imag**2

    mel = _mel_filterbank(n_mels, nfft, sample_rate, low_freq, high_freq)
    power = power[:, : mel.shape[1]]
    energies = power @ mel.T
    energies = np.maximum(energies, EPS_LOG)
    return np.log(energies).astype(np.float32)


class SpeakerEmbedder:
    def __init__(
        self,
        model_path: str,
        window_type: str = "povey",
        num_threads: int = 4,
        device: str = "gpu",
    ) -> None:
        import onnxruntime as ort

        options = ort.SessionOptions()
        options.intra_op_num_threads = num_threads
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        available = ort.get_available_providers()
        providers: list[str] = []
        if device == "gpu":
            if "CUDAExecutionProvider" in available:
                providers.append("CUDAExecutionProvider")
            if "DmlExecutionProvider" in available:
                providers.append("DmlExecutionProvider")
        providers.append("CPUExecutionProvider")

        self.session = ort.InferenceSession(model_path, sess_options=options, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape
        self.window_type = window_type

    def embed(self, wave: np.ndarray, sample_rate: int = SAMPLE_RATE) -> np.ndarray | None:
        if len(wave) < sample_rate * 0.4:
            return None
        fbank = kaldi_fbank(wave, sample_rate, window_type=self.window_type)
        fbank = fbank - fbank.mean(axis=0, keepdims=True)
        inp = fbank[None, :, :]
        out = self.session.run([self.output_name], {self.input_name: inp})[0]
        vector = out.squeeze()
        norm = np.linalg.norm(vector)
        return vector / norm if norm > 1e-8 else None
