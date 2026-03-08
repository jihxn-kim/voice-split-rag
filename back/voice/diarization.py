"""
pyannote segmentation-3.0 ONNX 겹침 감지 모듈

ONNX Runtime으로 pyannote/segmentation-3.0 모델을 실행하여
두 화자가 동시에 말하는 구간(overlap)을 감지한다.
PyTorch 불필요, 모델 6MB, CPU에서 30분 오디오 2-5분 처리.

모델: onnx-community/pyannote-segmentation-3.0 (MIT, 인증 불필요)
"""

import logging
import os
import tempfile
from typing import Optional

import numpy as np
import onnxruntime as ort

from logs.logging_util import LoggerSingleton

logger = LoggerSingleton.get_logger(logger_name="diarization", level=logging.INFO)

# --- 상수 ---
SAMPLE_RATE = 16000
WINDOW_DURATION = 10  # 초
WINDOW_SAMPLES = WINDOW_DURATION * SAMPLE_RATE  # 160000
STEP_SAMPLES = WINDOW_SAMPLES // 2  # 5초 스텝 (50% 오버랩)

# powerset 클래스: 4=spk1+spk2, 5=spk1+spk3, 6=spk2+spk3
OVERLAP_CLASSES = {4, 5, 6}

# SincNet 아키텍처 상수
SINCNET_OFFSET = 721  # 첫 프레임 시작 샘플
SINCNET_STEP = 270  # 프레임당 샘플 수

# ONNX 모델 URL (공개, 인증 불필요)
MODEL_URL = "https://huggingface.co/onnx-community/pyannote-segmentation-3.0/resolve/main/onnx/model.onnx"
MODEL_DIR = os.path.join(tempfile.gettempdir(), "pyannote_onnx")
MODEL_PATH = os.path.join(MODEL_DIR, "segmentation-3.0.onnx")

_session: Optional[ort.InferenceSession] = None


def _download_model() -> str:
    """ONNX 모델 다운로드 (이미 있으면 스킵)"""
    if os.path.exists(MODEL_PATH):
        logger.info(f"ONNX model already cached: {MODEL_PATH}")
        return MODEL_PATH

    os.makedirs(MODEL_DIR, exist_ok=True)
    logger.info(f"Downloading pyannote segmentation-3.0 ONNX model...")

    import requests as req
    resp = req.get(MODEL_URL, stream=True, timeout=120)
    resp.raise_for_status()

    tmp_path = MODEL_PATH + ".tmp"
    with open(tmp_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    os.rename(tmp_path, MODEL_PATH)

    size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
    logger.info(f"ONNX model downloaded: {size_mb:.1f}MB → {MODEL_PATH}")
    return MODEL_PATH


def _get_session() -> ort.InferenceSession:
    """ONNX 세션 lazy-load"""
    global _session
    if _session is not None:
        return _session

    model_path = _download_model()
    logger.info("Loading ONNX segmentation model...")
    _session = ort.InferenceSession(
        model_path,
        providers=["CPUExecutionProvider"],
    )
    input_info = _session.get_inputs()[0]
    logger.info(f"ONNX model loaded: input={input_info.name}, shape={input_info.shape}")
    return _session


def _frame_to_time(frame_idx: int, chunk_offset_samples: int = 0) -> float:
    """프레임 인덱스 → 절대 시간(초) 변환"""
    sample = (frame_idx * SINCNET_STEP) + SINCNET_OFFSET + chunk_offset_samples
    return sample / SAMPLE_RATE


def _load_audio_as_mono16k(audio_path: str) -> np.ndarray:
    """오디오 파일을 mono 16kHz numpy 배열로 로드 (librosa 대신 pydub 사용)"""
    from pydub import AudioSegment

    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_channels(1).set_frame_rate(SAMPLE_RATE).set_sample_width(2)

    samples = np.frombuffer(audio.raw_data, dtype=np.int16).astype(np.float32)
    samples = samples / 32768.0  # normalize to [-1, 1]
    return samples


def detect_overlaps(audio_path: str, min_duration: float = 0.3) -> list[dict]:
    """
    오디오 파일에서 겹침 구간(두 화자가 동시에 말하는 구간) 감지

    Args:
        audio_path: 오디오 파일 경로 (WAV, MP3, M4A 등)
        min_duration: 최소 겹침 길이 (초)

    Returns:
        [{"start": 3.5, "end": 4.2}, ...]
    """
    session = _get_session()
    input_name = session.get_inputs()[0].name

    waveform = _load_audio_as_mono16k(audio_path)
    total_duration = len(waveform) / SAMPLE_RATE
    logger.info(f"OSD: audio loaded, duration={total_duration:.1f}s, samples={len(waveform)}")

    # 슬라이딩 윈도우로 전체 오디오 처리
    overlap_frames = []  # (start_time, end_time) 튜플 리스트

    start = 0
    chunk_count = 0
    while start < len(waveform):
        end = start + WINDOW_SAMPLES
        chunk = waveform[start:end]

        # 패딩 (마지막 청크가 10초 미만일 때)
        if len(chunk) < WINDOW_SAMPLES:
            chunk = np.pad(chunk, (0, WINDOW_SAMPLES - len(chunk)))

        # [1, 1, 160000]
        input_data = chunk[np.newaxis, np.newaxis, :].astype(np.float32)
        logits = session.run(None, {input_name: input_data})[0][0]  # [num_frames, 7]

        # 각 프레임에서 가장 높은 확률의 클래스 찾기
        predicted_classes = np.argmax(logits, axis=1)

        # 겹침 클래스(4, 5, 6)인 프레임 → 시간으로 변환
        for frame_idx, cls in enumerate(predicted_classes):
            if cls in OVERLAP_CLASSES:
                t = _frame_to_time(frame_idx, chunk_offset_samples=start)
                frame_duration = SINCNET_STEP / SAMPLE_RATE
                overlap_frames.append((t, t + frame_duration))

        start += STEP_SAMPLES
        chunk_count += 1

    logger.info(f"OSD: processed {chunk_count} chunks, raw overlap frames={len(overlap_frames)}")

    if not overlap_frames:
        logger.info("OSD: no overlap detected")
        return []

    # 중복 제거 (슬라이딩 윈도우 오버랩 구간)
    overlap_frames.sort(key=lambda x: x[0])
    unique_frames = [overlap_frames[0]]
    for f in overlap_frames[1:]:
        if f[0] > unique_frames[-1][1] + 0.001:
            unique_frames.append(f)
        else:
            unique_frames[-1] = (unique_frames[-1][0], max(unique_frames[-1][1], f[1]))

    # 인접 프레임 병합 → 연속 겹침 구간
    merged = []
    cur_start, cur_end = unique_frames[0]
    gap_threshold = SINCNET_STEP / SAMPLE_RATE * 2  # 2프레임 이내 갭은 병합

    for f_start, f_end in unique_frames[1:]:
        if f_start <= cur_end + gap_threshold:
            cur_end = max(cur_end, f_end)
        else:
            if cur_end - cur_start >= min_duration:
                merged.append({"start": round(cur_start, 3), "end": round(cur_end, 3)})
            cur_start, cur_end = f_start, f_end

    if cur_end - cur_start >= min_duration:
        merged.append({"start": round(cur_start, 3), "end": round(cur_end, 3)})

    logger.info(f"OSD complete: {len(merged)} overlap regions (min_duration={min_duration}s)")
    for i, ov in enumerate(merged):
        logger.info(f"  overlap[{i}]: {ov['start']:.1f}s - {ov['end']:.1f}s ({ov['end']-ov['start']:.1f}s)")

    return merged


def reassign_overlap_words(
    segments: list[dict],
    words: list[dict],
    overlap_regions: list[dict],
) -> list[dict]:
    """
    겹침 구간의 단어에 overlap 마커를 추가하여 세그먼트를 재구성한다.

    겹침 구간이 아닌 단어는 VITO 화자를 유지하고,
    겹침 구간의 단어에는 has_overlap=True를 표시한다.

    Args:
        segments: VITO 발화 단위 세그먼트
        words: VITO 단어 리스트 [{speaker_id, text, start_time, end_time}, ...]
        overlap_regions: 겹침 구간 [{"start": 3.5, "end": 4.2}, ...]

    Returns:
        재구성된 세그먼트 리스트 (겹침 구간 표시 포함)
    """
    if not words or not overlap_regions:
        return segments

    def is_in_overlap(start: float, end: float) -> bool:
        for ov in overlap_regions:
            if start < ov["end"] and end > ov["start"]:
                return True
        return False

    # 각 단어에 overlap 마킹
    marked_words = []
    overlap_word_count = 0
    for w in words:
        w_copy = dict(w)
        if is_in_overlap(w["start_time"], w["end_time"]):
            w_copy["overlap"] = True
            overlap_word_count += 1
        marked_words.append(w_copy)

    if not marked_words:
        return segments

    # 연속된 같은 화자의 단어들을 세그먼트로 묶기
    new_segments = []
    current_speaker = marked_words[0]["speaker_id"]
    current_words = [marked_words[0]]

    for w in marked_words[1:]:
        if w["speaker_id"] == current_speaker:
            current_words.append(w)
        else:
            new_segments.append(_build_segment(current_speaker, current_words))
            current_speaker = w["speaker_id"]
            current_words = [w]

    if current_words:
        new_segments.append(_build_segment(current_speaker, current_words))

    logger.info(
        f"Overlap marking complete: {len(segments)} original → "
        f"{len(new_segments)} segments, "
        f"{overlap_word_count} words in overlap regions, "
        f"{len(overlap_regions)} overlap regions"
    )
    return new_segments


def _build_segment(speaker_id: str, words: list[dict]) -> dict:
    return {
        "speaker_id": speaker_id,
        "text": " ".join(w["text"] for w in words),
        "start_time": words[0]["start_time"],
        "end_time": words[-1]["end_time"],
        "duration": words[-1]["end_time"] - words[0]["start_time"],
        "has_overlap": any(w.get("overlap") for w in words),
    }
