"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, Pencil, Trash2, Save, X, Copy, Check, Target, FileText as FileTextIcon, UserCircle, Stethoscope, User } from "lucide-react";
import Sidebar from "../../../components/Sidebar";
import "./detail.css";

interface VoiceRecordDetail {
  id: number;
  title: string;
  user_id: number;
  client_id: number | null;
  s3_key: string | null;
  original_filename: string | null;
  total_speakers: number;
  full_transcript: string;
  speakers_data: Array<{
    speaker_id: string;
    text: string;
    start_time: number;
    end_time: number;
    duration: number;
  }>;
  segments_data: Array<{
    speaker_id: string;
    text: string;
    start_time: number;
    end_time: number;
    duration: number;
  }>;
  segments_merged_data?: Array<{
    speaker_id: string;
    text: string;
    start_time: number;
    end_time: number;
    duration: number;
  }>;
  dialogue: string;
  language_code: string;
  duration: number | null;
  next_session_goal?: string | null;
  created_at: string;
  updated_at: string;
}

export default function RecordDetailPage() {
  const router = useRouter();
  const params = useParams();
  const recordId = params.id as string;
  const [isCopied, setIsCopied] = useState(false);

  const [record, setRecord] = useState<VoiceRecordDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingTitle, setEditingTitle] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [speakerEdits, setSpeakerEdits] = useState<Record<string, string>>({});
  const [isSavingSpeakers, setIsSavingSpeakers] = useState(false);

  useEffect(() => {
    if (recordId) {
      fetchRecord();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordId]);

  const fetchRecord = async () => {
    try {
      setLoading(true);
      setError("");

      const token = localStorage.getItem("access_token");
      if (!token) {
        router.push("/login");
        return;
      }

      const response = await fetch(`/api/voice/records/${recordId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem("access_token");
          router.push("/login");
          return;
        }
        throw new Error("기록을 불러오는데 실패했습니다.");
      }

      const data = await response.json();
      setRecord(data);
      setNewTitle(data.title);
    } catch (err: any) {
      setError(err.message || "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateTitle = async () => {
    if (!newTitle.trim() || !record) return;

    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        router.push("/login");
        return;
      }

      const response = await fetch(`/api/voice/records/${recordId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title: newTitle }),
      });

      if (!response.ok) {
        throw new Error("제목 수정에 실패했습니다.");
      }

      const updatedRecord = await response.json();
      setRecord(updatedRecord);
      setEditingTitle(false);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString("ko-KR");
  };

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
  };

  const formatSpeakerLabel = (speakerId: string) => {
    const trimmed = (speakerId || "").toString().trim();
    if (!trimmed) return "발화자";
    if (
      trimmed.includes("상담사") ||
      trimmed.includes("내담자") ||
      trimmed.includes("발화자")
    ) {
      return trimmed;
    }
    if (/^[A-Za-z0-9]+$/.test(trimmed) && trimmed.length <= 2) {
      return `발화자 ${trimmed}`;
    }
    return trimmed;
  };

  const getDisplaySpeakerLabel = (speakerId: string) => {
    const nextName = (speakerEdits[speakerId] || "").trim();
    return nextName || formatSpeakerLabel(speakerId);
  };

  useEffect(() => {
    const displaySegments = record?.segments_merged_data?.length
      ? record.segments_merged_data
      : record?.segments_data;
    if (!displaySegments?.length) return;
    const seen = new Set<string>();
    const nextEdits: Record<string, string> = {};
    displaySegments.forEach((segment) => {
      const speakerId = (segment.speaker_id || "").toString().trim();
      if (!speakerId || seen.has(speakerId)) return;
      seen.add(speakerId);
      nextEdits[speakerId] = formatSpeakerLabel(speakerId);
    });
    setSpeakerEdits(nextEdits);
  }, [record]);

  const normalizeSpeakerLabel = (label: string) => {
    const trimmed = (label || "").toString().trim().replace(/\s+/g, " ");
    if (!trimmed) return "발화자";
    if (trimmed.startsWith("상담사")) {
      const suffix = trimmed.slice("상담사".length).trim();
      if (!suffix) return "상담사";
      if (/^[A-Za-z]$/.test(suffix) || /^\d+$/.test(suffix)) return "상담사";
      return `상담사 ${suffix}`;
    }
    if (trimmed.startsWith("내담자")) {
      const suffix = trimmed.slice("내담자".length).trim();
      return suffix ? `내담자 ${suffix}` : "내담자";
    }
    if (trimmed.startsWith("발화자")) {
      const suffix = trimmed.slice("발화자".length).trim();
      return suffix ? `발화자 ${suffix}` : "발화자";
    }
    return trimmed;
  };

  const buildDialogueCopyText = () => {
    const displaySegments = record?.segments_merged_data?.length
      ? record.segments_merged_data
      : record?.segments_data;
    if (!displaySegments?.length) return "";
    const speakerCounts = new Map<string, number>();
    return displaySegments
      .map((segment) => {
        const rawLabel = getDisplaySpeakerLabel(segment.speaker_id);
        const label = normalizeSpeakerLabel(rawLabel);
        const nextCount = (speakerCounts.get(label) || 0) + 1;
        speakerCounts.set(label, nextCount);
        const text = (segment.text || "").trim();
        return `${label} ${nextCount} : ${text}`;
      })
      .join("\n");
  };

  const handleCopyDialogue = async () => {
    if (!record?.segments_data?.length) return;
    const text = buildDialogueCopyText();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy dialogue:", err);
      alert("복사에 실패했습니다.");
    }
  };

  const getSpeakerIds = () => {
    const displaySegments = record?.segments_merged_data?.length
      ? record.segments_merged_data
      : record?.segments_data;
    if (!displaySegments?.length) return [];
    const seen = new Set<string>();
    const ordered: string[] = [];
    displaySegments.forEach((segment) => {
      const speakerId = (segment.speaker_id || "").toString().trim();
      if (!speakerId || seen.has(speakerId)) return;
      seen.add(speakerId);
      ordered.push(speakerId);
    });
    return ordered;
  };

  const handleEditSpeaker = (speakerId: string) => {
    const currentName = getDisplaySpeakerLabel(speakerId);
    const nextName = window.prompt("화자 이름을 입력하세요.", currentName);
    if (nextName === null) return;
    const trimmed = nextName.trim();
    setSpeakerEdits((prev) => ({
      ...prev,
      [speakerId]: trimmed,
    }));
  };

  const handleSaveSpeakers = async () => {
    if (!record) return;
    const speakerIds = getSpeakerIds();
    const renames: Record<string, string> = {};

    speakerIds.forEach((speakerId) => {
      const nextName = (speakerEdits[speakerId] || "").trim();
      const baseLabel = formatSpeakerLabel(speakerId);
      if (nextName && nextName !== baseLabel) {
        renames[speakerId] = nextName;
      }
    });

    if (Object.keys(renames).length === 0) {
      return;
    }

    try {
      setIsSavingSpeakers(true);
      const token = localStorage.getItem("access_token");
      if (!token) {
        router.push("/login");
        return;
      }

      const response = await fetch(`/api/voice/records/${recordId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ speaker_renames: renames }),
      });

      if (!response.ok) {
        throw new Error("화자 이름 저장에 실패했습니다.");
      }

      const updatedRecord = await response.json();
      setRecord(updatedRecord);
    } catch (err: any) {
      alert(err.message || "화자 이름 저장 중 오류가 발생했습니다.");
    } finally {
      setIsSavingSpeakers(false);
    }
  };

  const handleDeleteRecord = async () => {
    if (!record) return;
    const confirmDelete = window.confirm("이 회기 상담 기록을 삭제할까요? 복구할 수 없습니다.");
    if (!confirmDelete) return;

    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        router.push("/login");
        return;
      }

      const response = await fetch(`/api/voice/records/${recordId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("삭제에 실패했습니다.");
      }

      if (record.client_id) {
        router.push(`/clients/${record.client_id}`);
      } else {
        router.push("/history");
      }
    } catch (err: any) {
      alert(err.message || "삭제 중 오류가 발생했습니다.");
    }
  };

  const getSpeakerIcon = (label: string) => {
    return null;
  };

  const getSpeakerRole = (speakerId: string) => {
    const label = (speakerId || "").toString();
    if (label.includes("상담사")) return "counselor";
    if (label.includes("내담자")) return "client";
    return "unknown";
  };

  if (loading) {
    return (
      <div className="main-layout">
        <Sidebar />
        <div className="main-content">
          <div className="loading">기록을 불러오는 중...</div>
        </div>
      </div>
    );
  }

  if (error || !record) {
    return (
      <div className="main-layout">
        <Sidebar />
        <div className="main-content">
          <div className="error-message">
            {error || "기록을 찾을 수 없습니다."}
            <button onClick={() => router.push("/history")} className="back-btn">
              목록으로
            </button>
          </div>
        </div>
      </div>
    );
  }

  const speakerIds = getSpeakerIds();
  const hasSpeakerChanges = speakerIds.some((speakerId) => {
    const nextName = (speakerEdits[speakerId] || "").trim();
    const baseLabel = formatSpeakerLabel(speakerId);
    return nextName && nextName !== baseLabel;
  });

  return (
    <div className="main-layout">
      <Sidebar />
      <div className="main-content">
        <div className="detail-container">
          <div className="detail-header">
            <button onClick={() => router.push("/history")} className="back-btn">
              <ArrowLeft size={16} /> 목록으로
            </button>
          </div>

          <div className="detail-card">
            <div className="title-section">
              {editingTitle ? (
                <div className="title-edit">
                  <input
                    type="text"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    className="title-input"
                    autoFocus
                  />
                  <button onClick={handleUpdateTitle} className="save-btn">
                    저장
                  </button>
                  <button
                    onClick={() => {
                      setEditingTitle(false);
                      setNewTitle(record.title);
                    }}
                    className="cancel-btn"
                  >
                    취소
                  </button>
                </div>
              ) : (
                <div className="title-display">
                  <h1 className="detail-title">{record.title}</h1>
                  <div className="title-actions">
                    <button
                      onClick={() => setEditingTitle(true)}
                      className="edit-btn"
                    >
                      <Pencil size={14} /> 수정
                    </button>
                    <button onClick={handleDeleteRecord} className="delete-btn">
                      <Trash2 size={14} /> 삭제
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="metadata">
              <div className="meta-item meta-speakers">
                <div className="meta-speakers-header">
                  <div className="meta-speakers-count">
                    <strong>화자 수:</strong> {record.total_speakers}명
                  </div>
                  <button
                    type="button"
                    className="speaker-save-btn"
                    onClick={handleSaveSpeakers}
                    disabled={!hasSpeakerChanges || isSavingSpeakers}
                  >
                    {isSavingSpeakers ? "저장 중..." : "이름 저장"}
                  </button>
                </div>
                {speakerIds.length > 0 ? (
                  <div className="speaker-chips">
                    {speakerIds.map((speakerId) => {
                      const displayName = getDisplaySpeakerLabel(speakerId);
                      return (
                        <button
                          key={speakerId}
                          type="button"
                          className="speaker-chip"
                          onClick={() => handleEditSpeaker(speakerId)}
                        >
                          <span className="speaker-icon">
                            <UserCircle size={16} />
                          </span>
                          <span className="speaker-name">{displayName}</span>
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
              <div className="meta-item">
                <strong>생성일:</strong> {formatDate(record.created_at)}
              </div>
            </div>

            {record.next_session_goal ? (
              <div className="next-goal-card">
                <h2 className="section-title">다음 회기 상담 목표</h2>
                <p className="next-goal-text">{record.next_session_goal}</p>
              </div>
            ) : null}

            <div className="section">
              <div className="section-header">
                <h2 className="section-title">축어록</h2>
                <button
                  type="button"
                  onClick={handleCopyDialogue}
                  className={`copy-dialogue-btn ${isCopied ? "copied" : ""}`}
                  disabled={!record.segments_data?.length}
                >
                  {isCopied ? "복사됨" : "전체 복사"}
                </button>
              </div>
              <div className="segments-list">
                {(() => {
                  const speakerCounts = new Map<string, number>();
                  const displaySegments = record.segments_merged_data?.length
                    ? record.segments_merged_data
                    : record.segments_data;
                  return displaySegments.map((segment, index) => {
                    const role = getSpeakerRole(segment.speaker_id);
                    const alignClass = role === "client" ? "right" : "left";
                    const speakerKey = (segment.speaker_id || "").toString();
                    const nextCount = (speakerCounts.get(speakerKey) || 0) + 1;
                    speakerCounts.set(speakerKey, nextCount);

                    return (
                      <div key={index} className={`segment-row ${alignClass}`}>
                        <div className={`segment-item ${alignClass}`}>
                          <div className="segment-header">
                            <div className="segment-speaker-group">
                              <span className="segment-speaker">
                                {getDisplaySpeakerLabel(segment.speaker_id)}
                              </span>
                              <span className="segment-count">{nextCount}</span>
                            </div>
                            <span className="segment-time">
                              {formatTime(segment.start_time)}
                            </span>
                          </div>
                          <p className="segment-text">{segment.text}</p>
                        </div>
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
