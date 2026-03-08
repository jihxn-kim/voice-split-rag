"""
Falcon 화자 분리 + 겹침 구간 단어 재배정 모듈

Picovoice Falcon으로 화자 분리를 수행하고,
VITO STT 단어 타임스탬프와 매칭하여 겹침 구간의 화자를 재배정한다.

사용법:
  ENABLE_FALCON=true, PICOVOICE_ACCESS_KEY 환경변수 필요
"""

import logging
from typing import Optional

from logs.logging_util import LoggerSingleton

logger = LoggerSingleton.get_logger(logger_name="diarization", level=logging.INFO)

_falcon = None


def _get_falcon(access_key: str):
    """Falcon 인스턴스를 lazy-load (최초 1회만)"""
    global _falcon
    if _falcon is not None:
        return _falcon

    try:
        import pvfalcon

        logger.info("Loading Picovoice Falcon...")
        _falcon = pvfalcon.create(access_key=access_key)
        logger.info("Falcon loaded successfully")
        return _falcon
    except Exception as e:
        logger.error(f"Failed to load Falcon: {e}")
        raise


def run_falcon_diarization(
    audio_path: str,
    access_key: str,
) -> list[dict]:
    """
    Falcon으로 화자 분리 실행

    Args:
        audio_path: WAV 오디오 파일 경로
        access_key: Picovoice Access Key

    Returns:
        [{"speaker": 0, "start": 0.5, "end": 3.2}, ...]
    """
    falcon = _get_falcon(access_key)

    logger.info(f"Running Falcon diarization on {audio_path}")
    segments = falcon.process_file(audio_path)

    result = []
    for seg in segments:
        result.append({
            "speaker": seg.speaker_tag,
            "start": round(seg.start_sec, 3),
            "end": round(seg.end_sec, 3),
        })

    speakers = set(s["speaker"] for s in result)
    logger.info(f"Falcon diarization complete: {len(result)} segments, {len(speakers)} speakers")
    return result


def detect_overlaps_from_falcon(
    falcon_segments: list[dict],
    min_duration: float = 0.3,
) -> list[dict]:
    """
    Falcon 화자 구간에서 겹침 구간 추출

    서로 다른 화자의 구간이 시간적으로 겹치면 겹침으로 판단.

    Args:
        falcon_segments: Falcon 결과 [{speaker, start, end}, ...]
        min_duration: 최소 겹침 길이 (초)

    Returns:
        [{"start": 3.5, "end": 4.2}, ...]
    """
    overlaps = []

    for i, seg_a in enumerate(falcon_segments):
        for seg_b in falcon_segments[i + 1:]:
            if seg_a["speaker"] == seg_b["speaker"]:
                continue
            # 두 구간의 교차 계산
            inter_start = max(seg_a["start"], seg_b["start"])
            inter_end = min(seg_a["end"], seg_b["end"])
            if inter_end - inter_start >= min_duration:
                overlaps.append({
                    "start": round(inter_start, 3),
                    "end": round(inter_end, 3),
                })

    # 겹침 구간 병합 (중복 제거)
    if not overlaps:
        return []

    overlaps.sort(key=lambda x: x["start"])
    merged = [overlaps[0]]
    for ov in overlaps[1:]:
        if ov["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], ov["end"])
        else:
            merged.append(ov)

    logger.info(f"Overlap detection: {len(merged)} overlap regions found")
    return merged


def reassign_words_with_falcon(
    segments: list[dict],
    words: list[dict],
    falcon_segments: list[dict],
) -> list[dict]:
    """
    VITO 단어들을 Falcon 화자 분리 결과로 재배정하여 세그먼트를 재구성한다.

    겹침 구간이 아닌 단어는 VITO 화자를 유지하고,
    겹침 구간의 단어만 Falcon 화자로 재배정한다.

    Args:
        segments: VITO 발화 단위 세그먼트
        words: VITO 단어 리스트 [{speaker_id, text, start_time, end_time}, ...]
        falcon_segments: Falcon 결과 [{speaker, start, end}, ...]

    Returns:
        재구성된 세그먼트 리스트
    """
    if not words or not falcon_segments:
        return segments

    # 겹침 구간 감지
    overlap_regions = detect_overlaps_from_falcon(falcon_segments)

    if not overlap_regions:
        logger.info("No overlap regions — using VITO speakers as-is")
        return segments

    def is_in_overlap(start: float, end: float) -> bool:
        for ov in overlap_regions:
            if start < ov["end"] and end > ov["start"]:
                return True
        return False

    def get_falcon_speaker(start: float, end: float) -> Optional[int]:
        """단어 시간대에 가장 많이 겹치는 Falcon 화자 반환"""
        best_speaker = None
        best_overlap = 0.0
        for fs in falcon_segments:
            inter_start = max(start, fs["start"])
            inter_end = min(end, fs["end"])
            overlap = max(0, inter_end - inter_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = fs["speaker"]
        return best_speaker

    # 1단계: 겹침 구간 단어만 Falcon 화자로 재배정
    assigned_words = []
    for w in words:
        w_copy = dict(w)
        if is_in_overlap(w["start_time"], w["end_time"]):
            falcon_speaker = get_falcon_speaker(w["start_time"], w["end_time"])
            if falcon_speaker is not None:
                w_copy["speaker_id"] = str(falcon_speaker)
                w_copy["overlap"] = True
        assigned_words.append(w_copy)

    if not assigned_words:
        return segments

    # 2단계: 연속된 같은 화자의 단어들을 세그먼트로 묶기
    new_segments = []
    current_speaker = assigned_words[0]["speaker_id"]
    current_words = [assigned_words[0]]

    for w in assigned_words[1:]:
        if w["speaker_id"] == current_speaker:
            current_words.append(w)
        else:
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

    overlap_count = sum(1 for s in new_segments if s.get("has_overlap"))
    logger.info(
        f"Word reassignment complete: {len(segments)} original → "
        f"{len(new_segments)} new segments "
        f"({overlap_count} with overlap reassignment, "
        f"{len(overlap_regions)} overlap regions)"
    )
    return new_segments
