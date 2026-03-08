"""
pyannote segmentation-3.0 ONNX 겹침 감지 + 화자 재배정 모듈

ONNX Runtime으로 pyannote/segmentation-3.0 모델을 실행하여
두 화자가 동시에 말하는 구간(overlap)을 감지하고,
겹침 구간의 단어를 프레임별 화자 확률 기반으로 재배정한다.

powerset 클래스:
  0=무음, 1=spk1, 2=spk2, 3=spk3,
  4=spk1+spk2, 5=spk1+spk3, 6=spk2+spk3

각 프레임에서 화자별 활성화 확률:
  spk1 = softmax[1] + softmax[4] + softmax[5]
  spk2 = softmax[2] + softmax[4] + softmax[6]
  spk3 = softmax[3] + softmax[5] + softmax[6]

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
NUM_SPEAKERS = 3  # powerset은 최대 3화자

OVERLAP_CLASSES = {4, 5, 6}

SINCNET_OFFSET = 721
SINCNET_STEP = 270

MODEL_URL = "https://huggingface.co/onnx-community/pyannote-segmentation-3.0/resolve/main/onnx/model.onnx"
MODEL_DIR = os.path.join(tempfile.gettempdir(), "pyannote_onnx")
MODEL_PATH = os.path.join(MODEL_DIR, "segmentation-3.0.onnx")

_session: Optional[ort.InferenceSession] = None


def _download_model() -> str:
    if os.path.exists(MODEL_PATH):
        logger.info(f"ONNX model already cached: {MODEL_PATH}")
        return MODEL_PATH

    os.makedirs(MODEL_DIR, exist_ok=True)
    logger.info("Downloading pyannote segmentation-3.0 ONNX model...")

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
    sample = (frame_idx * SINCNET_STEP) + SINCNET_OFFSET + chunk_offset_samples
    return sample / SAMPLE_RATE


def _time_to_frame(time_sec: float) -> int:
    sample = int(time_sec * SAMPLE_RATE)
    return max(0, (sample - SINCNET_OFFSET) // SINCNET_STEP)


def _load_audio_as_mono16k(audio_path: str) -> np.ndarray:
    from pydub import AudioSegment
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_channels(1).set_frame_rate(SAMPLE_RATE).set_sample_width(2)
    samples = np.frombuffer(audio.raw_data, dtype=np.int16).astype(np.float32)
    samples = samples / 32768.0
    return samples


def _softmax(logits: np.ndarray) -> np.ndarray:
    exp = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
    return exp / np.sum(exp, axis=-1, keepdims=True)


def run_segmentation(audio_path: str) -> dict:
    """
    전체 오디오에 대해 pyannote segmentation 실행.

    Returns:
        {
            "speaker_probs": np.ndarray (total_frames, 3),  # 화자별 활성화 확률
            "overlap_regions": list[dict],                    # 겹침 구간
            "total_frames": int,
            "duration": float,
        }
    """
    session = _get_session()
    input_name = session.get_inputs()[0].name

    waveform = _load_audio_as_mono16k(audio_path)
    total_duration = len(waveform) / SAMPLE_RATE
    logger.info(f"OSD: audio loaded, duration={total_duration:.1f}s, samples={len(waveform)}")

    # 슬라이딩 윈도우 — 화자 확률 수집
    all_speaker_probs = []
    overlap_frame_count = 0

    # 전체 프레임 수 계산
    total_samples = len(waveform)
    total_frames = max(0, (total_samples - SINCNET_OFFSET) // SINCNET_STEP)

    # 프레임별 화자 확률 누적 (슬라이딩 윈도우 평균용)
    prob_sum = np.zeros((total_frames, NUM_SPEAKERS), dtype=np.float64)
    prob_count = np.zeros(total_frames, dtype=np.int32)

    start = 0
    chunk_count = 0
    while start < len(waveform):
        end = start + WINDOW_SAMPLES
        chunk = waveform[start:end]

        if len(chunk) < WINDOW_SAMPLES:
            chunk = np.pad(chunk, (0, WINDOW_SAMPLES - len(chunk)))

        input_data = chunk[np.newaxis, np.newaxis, :].astype(np.float32)
        logits = session.run(None, {input_name: input_data})[0][0]  # [num_frames, 7]

        probs = _softmax(logits)  # [num_frames, 7]

        # powerset → 화자별 확률 변환
        chunk_speaker_probs = np.zeros((probs.shape[0], NUM_SPEAKERS), dtype=np.float64)
        chunk_speaker_probs[:, 0] = probs[:, 1] + probs[:, 4] + probs[:, 5]  # spk1
        chunk_speaker_probs[:, 1] = probs[:, 2] + probs[:, 4] + probs[:, 6]  # spk2
        chunk_speaker_probs[:, 2] = probs[:, 3] + probs[:, 5] + probs[:, 6]  # spk3

        # 전체 타임라인에 매핑
        chunk_start_frame = max(0, (start - SINCNET_OFFSET) // SINCNET_STEP) if start > 0 else 0
        for i in range(probs.shape[0]):
            global_frame = chunk_start_frame + i
            if global_frame < total_frames:
                prob_sum[global_frame] += chunk_speaker_probs[i]
                prob_count[global_frame] += 1

        start += STEP_SAMPLES
        chunk_count += 1

    # 평균 화자 확률
    valid = prob_count > 0
    speaker_probs = np.zeros_like(prob_sum)
    speaker_probs[valid] = prob_sum[valid] / prob_count[valid, np.newaxis]

    logger.info(f"OSD: processed {chunk_count} chunks, total_frames={total_frames}")

    # 겹침 구간 추출 (두 화자 확률이 모두 임계값 이상인 프레임)
    ONSET = 0.5
    min_duration = 0.3

    overlap_mask = np.zeros(total_frames, dtype=bool)
    for i in range(total_frames):
        # 활성 화자 수: 확률이 ONSET 이상인 화자
        active_count = np.sum(speaker_probs[i] >= ONSET)
        if active_count >= 2:
            overlap_mask[i] = True

    # 연속 겹침 프레임 → 구간으로 병합
    overlap_regions = []
    in_overlap = False
    ov_start = 0.0

    for i in range(total_frames):
        t = _frame_to_time(i)
        if overlap_mask[i] and not in_overlap:
            in_overlap = True
            ov_start = t
        elif not overlap_mask[i] and in_overlap:
            in_overlap = False
            ov_end = t
            if ov_end - ov_start >= min_duration:
                overlap_regions.append({"start": round(ov_start, 3), "end": round(ov_end, 3)})

    if in_overlap:
        ov_end = _frame_to_time(total_frames - 1)
        if ov_end - ov_start >= min_duration:
            overlap_regions.append({"start": round(ov_start, 3), "end": round(ov_end, 3)})

    logger.info(f"OSD complete: {len(overlap_regions)} overlap regions")
    for i, ov in enumerate(overlap_regions):
        logger.info(f"  overlap[{i}]: {ov['start']:.1f}s - {ov['end']:.1f}s ({ov['end']-ov['start']:.1f}s)")

    return {
        "speaker_probs": speaker_probs,
        "overlap_regions": overlap_regions,
        "total_frames": total_frames,
        "duration": total_duration,
    }


def _map_pyannote_to_vito_speakers(
    speaker_probs: np.ndarray,
    words: list[dict],
    overlap_regions: list[dict],
) -> dict:
    """
    비겹침 구간의 단어들을 이용하여 pyannote 화자 ID → VITO 화자 ID 매핑을 구축한다.

    각 VITO 화자별로 비겹침 단어들의 시간대를 모아서,
    해당 시간대에서 가장 확률이 높은 pyannote 화자를 매핑한다.

    Returns:
        {pyannote_spk_idx: vito_speaker_id, ...}
    """
    def is_in_overlap(start: float, end: float) -> bool:
        for ov in overlap_regions:
            if start < ov["end"] and end > ov["start"]:
                return True
        return False

    # VITO 화자별로 pyannote 화자 확률 누적
    vito_speakers = set(w["speaker_id"] for w in words)
    # {vito_speaker_id: [sum_of_probs_per_pyannote_speaker]}
    vito_to_pyannote_scores = {spk: np.zeros(NUM_SPEAKERS) for spk in vito_speakers}
    vito_word_counts = {spk: 0 for spk in vito_speakers}

    for w in words:
        if is_in_overlap(w["start_time"], w["end_time"]):
            continue  # 겹침 구간 단어는 매핑에 사용하지 않음

        # 이 단어의 시간대에 해당하는 프레임들의 화자 확률 평균
        start_frame = _time_to_frame(w["start_time"])
        end_frame = _time_to_frame(w["end_time"])
        if end_frame <= start_frame:
            end_frame = start_frame + 1

        end_frame = min(end_frame, len(speaker_probs))
        start_frame = min(start_frame, len(speaker_probs) - 1)

        if start_frame >= len(speaker_probs):
            continue

        frame_probs = speaker_probs[start_frame:end_frame]
        if len(frame_probs) == 0:
            continue

        avg_probs = np.mean(frame_probs, axis=0)
        vito_to_pyannote_scores[w["speaker_id"]] += avg_probs
        vito_word_counts[w["speaker_id"]] += 1

    # 각 VITO 화자에 대해 가장 확률이 높은 pyannote 화자 찾기
    pyannote_to_vito = {}
    used_pyannote = set()

    # 단어 수가 많은 VITO 화자부터 매핑 (greedy)
    sorted_vito = sorted(vito_speakers, key=lambda s: vito_word_counts[s], reverse=True)

    for vito_spk in sorted_vito:
        if vito_word_counts[vito_spk] == 0:
            continue
        scores = vito_to_pyannote_scores[vito_spk]
        # 이미 사용된 pyannote 화자 제외
        for idx in used_pyannote:
            scores[idx] = -1
        best_pyannote = int(np.argmax(scores))
        pyannote_to_vito[best_pyannote] = vito_spk
        used_pyannote.add(best_pyannote)
        logger.info(
            f"Speaker mapping: pyannote[{best_pyannote}] → VITO[{vito_spk}] "
            f"(score={vito_to_pyannote_scores[vito_spk][best_pyannote]:.2f}, "
            f"words={vito_word_counts[vito_spk]})"
        )

    return pyannote_to_vito


def reassign_overlap_words(
    segments: list[dict],
    words: list[dict],
    speaker_probs: np.ndarray,
    overlap_regions: list[dict],
) -> list[dict]:
    """
    겹침 구간의 단어를 pyannote 화자 확률 기반으로 재배정하고 세그먼트를 재구성한다.

    비겹침 구간: VITO 화자 유지
    겹침 구간: pyannote 프레임별 화자 확률로 재배정

    Args:
        segments: VITO 발화 단위 세그먼트
        words: VITO 단어 리스트 [{speaker_id, text, start_time, end_time}, ...]
        speaker_probs: pyannote 프레임별 화자 확률 (total_frames, 3)
        overlap_regions: 겹침 구간 [{"start": 3.5, "end": 4.2}, ...]

    Returns:
        재구성된 세그먼트 리스트
    """
    if not words or not overlap_regions:
        return segments

    # 1. pyannote 화자 → VITO 화자 매핑 구축
    pyannote_to_vito = _map_pyannote_to_vito_speakers(
        speaker_probs, words, overlap_regions
    )

    if not pyannote_to_vito:
        logger.warning("Failed to build speaker mapping — using VITO speakers as-is")
        return segments

    def is_in_overlap(start: float, end: float) -> bool:
        for ov in overlap_regions:
            if start < ov["end"] and end > ov["start"]:
                return True
        return False

    def get_pyannote_speaker(start: float, end: float) -> Optional[str]:
        """단어 시간대에서 가장 확률 높은 pyannote 화자의 VITO ID 반환"""
        start_frame = _time_to_frame(start)
        end_frame = _time_to_frame(end)
        if end_frame <= start_frame:
            end_frame = start_frame + 1
        end_frame = min(end_frame, len(speaker_probs))
        start_frame = min(start_frame, len(speaker_probs) - 1)
        if start_frame >= len(speaker_probs):
            return None

        frame_probs = speaker_probs[start_frame:end_frame]
        if len(frame_probs) == 0:
            return None

        avg_probs = np.mean(frame_probs, axis=0)
        best_pyannote = int(np.argmax(avg_probs))
        return pyannote_to_vito.get(best_pyannote)

    # 2. 겹침 구간 단어만 재배정
    reassigned_words = []
    reassign_count = 0
    for w in words:
        w_copy = dict(w)
        if is_in_overlap(w["start_time"], w["end_time"]):
            new_speaker = get_pyannote_speaker(w["start_time"], w["end_time"])
            if new_speaker and new_speaker != w["speaker_id"]:
                w_copy["speaker_id"] = new_speaker
                reassign_count += 1
            w_copy["overlap"] = True
        reassigned_words.append(w_copy)

    # 3. 연속된 같은 화자의 단어들을 세그먼트로 묶기
    new_segments = []
    current_speaker = reassigned_words[0]["speaker_id"]
    current_words = [reassigned_words[0]]

    for w in reassigned_words[1:]:
        if w["speaker_id"] == current_speaker:
            current_words.append(w)
        else:
            new_segments.append(_build_segment(current_speaker, current_words))
            current_speaker = w["speaker_id"]
            current_words = [w]

    if current_words:
        new_segments.append(_build_segment(current_speaker, current_words))

    overlap_word_count = sum(1 for w in reassigned_words if w.get("overlap"))
    logger.info(
        f"Word reassignment complete: {len(segments)} original → "
        f"{len(new_segments)} segments, "
        f"{overlap_word_count} words in overlap, "
        f"{reassign_count} words reassigned to different speaker, "
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
