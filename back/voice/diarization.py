"""
pyannote 겹침 감지 (Overlapped Speech Detection) 모듈

사용법:
  ENABLE_PYANNOTE=true, HF_TOKEN 환경변수 필요
  pyannote/overlapped-speech-detection 파이프라인 사용 (CPU)

겹침 구간만 감지하고, 해당 구간의 VITO 단어들을
pyannote 화자 분리 결과로 재배정한다.
"""

import logging
from typing import Optional

from logs.logging_util import LoggerSingleton

logger = LoggerSingleton.get_logger(logger_name="diarization", level=logging.INFO)

_osd_pipeline = None
_diarization_pipeline = None


def _get_osd_pipeline(hf_token: str):
    """segmentation-3.0 모델로 겹침 감지 파이프라인을 lazy-load"""
    global _osd_pipeline
    if _osd_pipeline is not None:
        return _osd_pipeline

    try:
        from pyannote.audio import Model, Inference

        logger.info("Loading pyannote/segmentation-3.0 for overlap detection...")
        model = Model.from_pretrained(
            "pyannote/segmentation-3.0",
            token=hf_token,
        )
        _osd_pipeline = Inference(model, step=2.5)
        logger.info("pyannote segmentation model loaded for OSD")
        return _osd_pipeline
    except Exception as e:
        logger.error(f"Failed to load pyannote segmentation model: {e}")
        raise


def _get_diarization_pipeline(hf_token: str):
    """pyannote 화자 분리 파이프라인을 lazy-load (최초 1회만)"""
    global _diarization_pipeline
    if _diarization_pipeline is not None:
        return _diarization_pipeline

    try:
        from pyannote.audio import Pipeline
        import torch

        logger.info("Loading pyannote/speaker-diarization-3.1 pipeline...")
        _diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=hf_token,
        )
        _diarization_pipeline.to(torch.device("cpu"))
        logger.info("pyannote diarization pipeline loaded successfully (CPU)")
        return _diarization_pipeline
    except Exception as e:
        logger.error(f"Failed to load pyannote diarization pipeline: {e}")
        raise


def detect_overlaps(
    audio_path: str,
    hf_token: str,
    min_duration: float = 0.3,
    overlap_threshold: float = 0.5,
) -> list[dict]:
    """
    segmentation-3.0 모델로 겹침 구간 감지

    segmentation 모델은 각 프레임에서 최대 3명의 화자 활성 확률을 출력한다.
    2명 이상의 화자가 동시에 threshold를 넘으면 겹침으로 판단.

    Args:
        audio_path: WAV 오디오 파일 경로
        hf_token: HuggingFace 인증 토큰
        min_duration: 최소 겹침 길이 (초)
        overlap_threshold: 화자 활성 판단 임계값 (0~1)

    Returns:
        [{"start": 3.5, "end": 4.2}, ...]
    """
    import numpy as np

    inference = _get_osd_pipeline(hf_token)

    logger.info(f"Running pyannote segmentation for OSD on {audio_path}")
    output = inference(audio_path)

    # output.data: (frames, 3) — 각 프레임에서 최대 3명 화자의 활성 확률
    # 2명 이상 threshold 초과 → 겹침
    data = output.data
    num_active = np.sum(data > overlap_threshold, axis=1)
    is_overlap = num_active >= 2

    # 프레임 → 시간 변환
    frames = output.sliding_window
    overlaps = []
    in_overlap = False
    start = 0.0

    for i, overlap in enumerate(is_overlap):
        t = frames[i].middle
        if overlap and not in_overlap:
            start = t
            in_overlap = True
        elif not overlap and in_overlap:
            duration = t - start
            if duration >= min_duration:
                overlaps.append({
                    "start": round(start, 3),
                    "end": round(t, 3),
                })
            in_overlap = False

    # 마지막 구간 처리
    if in_overlap:
        t = frames[len(is_overlap) - 1].middle
        duration = t - start
        if duration >= min_duration:
            overlaps.append({
                "start": round(start, 3),
                "end": round(t, 3),
            })

    logger.info(f"pyannote OSD complete: {len(overlaps)} overlap regions detected")
    return overlaps


def run_diarization_on_overlaps(
    audio_path: str,
    hf_token: str,
    overlap_regions: list[dict],
) -> list[dict]:
    """
    겹침 구간에 대해 화자 분리 실행

    전체 오디오에 화자 분리를 돌리고, 겹침 구간에 해당하는 결과만 반환한다.

    Returns:
        [{"speaker": "SPEAKER_00", "start": 3.5, "end": 4.0}, ...]
    """
    if not overlap_regions:
        return []

    pipeline = _get_diarization_pipeline(hf_token)

    logger.info(f"Running pyannote diarization for overlap speaker assignment...")
    diarization = pipeline(audio_path, num_speakers=2)

    # 겹침 구간에 해당하는 화자 분리 결과만 추출
    overlap_speakers = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        for overlap in overlap_regions:
            # 겹침 구간과 화자 구간이 교차하는지 확인
            inter_start = max(turn.start, overlap["start"])
            inter_end = min(turn.end, overlap["end"])
            if inter_end > inter_start:
                overlap_speakers.append({
                    "speaker": speaker,
                    "start": round(inter_start, 3),
                    "end": round(inter_end, 3),
                })

    logger.info(f"Diarization for overlaps: {len(overlap_speakers)} speaker segments in overlap regions")
    return overlap_speakers


def reassign_words_in_overlaps(
    segments: list[dict],
    words: list[dict],
    overlap_regions: list[dict],
    overlap_speakers: list[dict],
) -> list[dict]:
    """
    겹침 구간의 단어들을 pyannote 화자 분리 결과로 재배정하여
    세그먼트를 재구성한다.

    Args:
        segments: VITO 발화 단위 세그먼트 [{speaker_id, text, start_time, end_time, words}, ...]
        words: VITO 단어 리스트 [{speaker_id, text, start_time, end_time}, ...]
        overlap_regions: 겹침 구간 [{start, end}, ...]
        overlap_speakers: 겹침 구간의 pyannote 화자 [{speaker, start, end}, ...]

    Returns:
        재구성된 세그먼트 리스트
    """
    if not overlap_regions or not overlap_speakers or not words:
        return segments

    def is_in_overlap(start: float, end: float) -> bool:
        """단어가 겹침 구간에 포함되는지"""
        for ov in overlap_regions:
            if start < ov["end"] and end > ov["start"]:
                return True
        return False

    def get_pyannote_speaker(start: float, end: float) -> Optional[str]:
        """단어 시간대에 가장 많이 겹치는 pyannote 화자 반환"""
        best_speaker = None
        best_overlap = 0.0
        for ps in overlap_speakers:
            inter_start = max(start, ps["start"])
            inter_end = min(end, ps["end"])
            overlap = max(0, inter_end - inter_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = ps["speaker"]
        return best_speaker

    # 1단계: 각 단어에 최종 화자 배정
    assigned_words = []
    for w in words:
        w_copy = dict(w)
        if is_in_overlap(w["start_time"], w["end_time"]):
            pya_speaker = get_pyannote_speaker(w["start_time"], w["end_time"])
            if pya_speaker:
                w_copy["speaker_id"] = pya_speaker
                w_copy["overlap"] = True
        assigned_words.append(w_copy)

    # 2단계: 연속된 같은 화자의 단어들을 세그먼트로 묶기
    if not assigned_words:
        return segments

    new_segments = []
    current_speaker = assigned_words[0]["speaker_id"]
    current_words = [assigned_words[0]]

    for w in assigned_words[1:]:
        if w["speaker_id"] == current_speaker:
            current_words.append(w)
        else:
            # 현재 세그먼트 저장
            new_segments.append({
                "speaker_id": current_speaker,
                "text": " ".join(cw["text"] for cw in current_words),
                "start_time": current_words[0]["start_time"],
                "end_time": current_words[-1]["end_time"],
                "duration": current_words[-1]["end_time"] - current_words[0]["start_time"],
                "has_overlap": any(cw.get("overlap") for cw in current_words),
            })
            current_speaker = w["speaker_id"]
            current_words = [w]

    # 마지막 세그먼트
    if current_words:
        new_segments.append({
            "speaker_id": current_speaker,
            "text": " ".join(cw["text"] for cw in current_words),
            "start_time": current_words[0]["start_time"],
            "end_time": current_words[-1]["end_time"],
            "duration": current_words[-1]["end_time"] - current_words[0]["start_time"],
            "has_overlap": any(cw.get("overlap") for cw in current_words),
        })

    logger.info(
        f"Word reassignment complete: {len(segments)} original segments → "
        f"{len(new_segments)} new segments "
        f"({sum(1 for s in new_segments if s.get('has_overlap'))} with overlap reassignment)"
    )
    return new_segments
