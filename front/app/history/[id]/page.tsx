"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import "./detail.css";

interface VoiceRecordDetail {
  id: number;
  title: string;
  user_id: number;
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
  dialogue: string;
  language_code: string;
  duration: number | null;
  created_at: string;
  updated_at: string;
}

export default function RecordDetailPage() {
  const router = useRouter();
  const params = useParams();
  const recordId = params.id as string;

  const [record, setRecord] = useState<VoiceRecordDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingTitle, setEditingTitle] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  useEffect(() => {
    if (recordId) {
      fetchRecord();
    }
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

  if (loading) {
    return (
      <div className="detail-container">
        <div className="loading">기록을 불러오는 중...</div>
      </div>
    );
  }

  if (error || !record) {
    return (
      <div className="detail-container">
        <div className="error-message">
          {error || "기록을 찾을 수 없습니다."}
          <button onClick={() => router.push("/history")} className="back-btn">
            목록으로
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="detail-container">
      <div className="detail-header">
        <button onClick={() => router.push("/history")} className="back-btn">
          ← 목록으로
        </button>
        <button onClick={() => router.push("/")} className="upload-btn">
          새 음성 업로드
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
              <button
                onClick={() => setEditingTitle(true)}
                className="edit-btn"
              >
                ✏️ 수정
              </button>
            </div>
          )}
        </div>

        <div className="metadata">
          <div className="meta-item">
            <strong>화자 수:</strong> {record.total_speakers}명
          </div>
          <div className="meta-item">
            <strong>언어:</strong> {record.language_code.toUpperCase()}
          </div>
          <div className="meta-item">
            <strong>길이:</strong>{" "}
            {record.duration ? formatTime(record.duration) : "N/A"}
          </div>
          <div className="meta-item">
            <strong>생성일:</strong> {formatDate(record.created_at)}
          </div>
          {record.updated_at !== record.created_at && (
            <div className="meta-item">
              <strong>수정일:</strong> {formatDate(record.updated_at)}
            </div>
          )}
        </div>

        <div className="section">
          <h2 className="section-title">전체 대화</h2>
          <div className="transcript-box">{record.full_transcript}</div>
        </div>

        <div className="section">
          <h2 className="section-title">화자별 대화</h2>
          <div className="speakers-list">
            {record.speakers_data.map((speaker) => (
              <div key={speaker.speaker_id} className="speaker-card">
                <div className="speaker-header">
                  <h3>발화자 {speaker.speaker_id}</h3>
                  <span className="speaker-time">
                    {formatTime(speaker.start_time)} ~{" "}
                    {formatTime(speaker.end_time)} (
                    {formatTime(speaker.duration)})
                  </span>
                </div>
                <p className="speaker-text">{speaker.text}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="section">
          <h2 className="section-title">시간순 대화</h2>
          <div className="segments-list">
            {record.segments_data.map((segment, index) => (
              <div key={index} className="segment-item">
                <div className="segment-header">
                  <span className="segment-speaker">
                    발화자 {segment.speaker_id}
                  </span>
                  <span className="segment-time">
                    {formatTime(segment.start_time)}
                  </span>
                </div>
                <p className="segment-text">{segment.text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
