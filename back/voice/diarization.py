"""
pyannote 화자 분리 (speaker diarization) 모듈

사용법:
  ENABLE_PYANNOTE=true, HF_TOKEN 환경변수 필요
  pyannote/speaker-diarization-3.1 파이프라인 사용 (CPU 전용)
"""

import logging
import os
from typing import Optional

from logs.logging_util import LoggerSingleton

logger = LoggerSingleton.get_logger(logger_name="diarization", level=logging.INFO)

_pipeline = None


def _get_pipeline(hf_token: str):
    """pyannote 파이프라인을 lazy-load (최초 1회만 로드)"""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    try:
        from pyannote.audio import Pipeline
        import torch

        logger.info("Loading pyannote/speaker-diarization-3.1 pipeline...")
        _pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
        )
        # CPU 강제 설정
        _pipeline.to(torch.device("cpu"))
        logger.info("pyannote pipeline loaded successfully (CPU)")
        return _pipeline
    except Exception as e:
        logger.error(f"Failed to load pyannote pipeline: {e}")
        raise


def run_pyannote_diarization(
    audio_path: str,
    hf_token: str,
    num_speakers: Optional[int] = None,
) -> list[dict]:
    """
    pyannote로 화자 분리 실행

    Args:
        audio_path: WAV 오디오 파일 경로
        hf_token: HuggingFace 인증 토큰
        num_speakers: 화자 수 (None이면 자동 감지)

    Returns:
        [{"speaker": "SPEAKER_00", "start": 0.5, "end": 3.2}, ...]
    """
    pipeline = _get_pipeline(hf_token)

    kwargs = {}
    if num_speakers and num_speakers > 0:
        kwargs["num_speakers"] = num_speakers

    logger.info(f"Running pyannote diarization on {audio_path} (num_speakers={num_speakers})")
    diarization = pipeline(audio_path, **kwargs)

    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "speaker": speaker,
            "start": round(turn.start, 3),
            "end": round(turn.end, 3),
        })

    logger.info(f"pyannote diarization complete: {len(segments)} segments, speakers={set(s['speaker'] for s in segments)}")
    return segments


def align_speakers(
    stt_segments: list[dict],
    pyannote_segments: list[dict],
) -> list[dict]:
    """
    STT 세그먼트의 speaker_id를 pyannote 결과 기반으로 교체

    각 STT 세그먼트의 시간 구간과 가장 많이 겹치는 pyannote 화자를 할당한다.

    Args:
        stt_segments: STT 결과 세그먼트 (speaker_id, start_time, end_time, text ...)
        pyannote_segments: pyannote 결과 ([{speaker, start, end}, ...])

    Returns:
        speaker_id가 교체된 STT 세그먼트 리스트 (원본 수정 없이 복사본 반환)
    """
    if not pyannote_segments:
        return stt_segments

    result = []
    for seg in stt_segments:
        seg_copy = dict(seg)
        seg_start = seg.get("start_time", 0)
        seg_end = seg.get("end_time", 0)

        # 각 pyannote 화자별 겹치는 시간 계산
        speaker_overlaps: dict[str, float] = {}
        for pya_seg in pyannote_segments:
            overlap_start = max(seg_start, pya_seg["start"])
            overlap_end = min(seg_end, pya_seg["end"])
            overlap = max(0, overlap_end - overlap_start)
            if overlap > 0:
                speaker = pya_seg["speaker"]
                speaker_overlaps[speaker] = speaker_overlaps.get(speaker, 0) + overlap

        if speaker_overlaps:
            best_speaker = max(speaker_overlaps, key=speaker_overlaps.get)  # type: ignore
            seg_copy["speaker_id"] = best_speaker

        result.append(seg_copy)

    # pyannote 화자 ID를 순서대로 정규화 (SPEAKER_00 → S1 등)
    unique_speakers = []
    for seg in result:
        spk = seg.get("speaker_id", "")
        if spk not in unique_speakers:
            unique_speakers.append(spk)

    speaker_map = {spk: str(i) for i, spk in enumerate(unique_speakers)}
    for seg in result:
        seg["speaker_id"] = speaker_map.get(seg["speaker_id"], seg["speaker_id"])

    logger.info(f"Speaker alignment complete: {len(unique_speakers)} speakers mapped")
    return result
