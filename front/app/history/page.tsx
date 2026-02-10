"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Mic, Users, RefreshCw } from "lucide-react";
import Sidebar from "../../components/Sidebar";
import "./history.css";

interface VoiceRecord {
  id: number;
  title: string;
  total_speakers: number;
  duration: number | null;
  created_at: string;
  updated_at: string;
}

export default function HistoryPage() {
  const router = useRouter();
  const [records, setRecords] = useState<VoiceRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchRecords();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchRecords = async () => {
    try {
      setLoading(true);
      setError("");

      const token = localStorage.getItem("access_token");
      if (!token) {
        router.push("/login");
        return;
      }

      const response = await fetch("/api/voice/records", {
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
        throw new Error("기록 목록을 가져오는데 실패했습니다.");
      }

      const data = await response.json();
      setRecords(data.records);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return "N/A";
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
  };

  const handleRecordClick = (recordId: number) => {
    router.push(`/history/${recordId}`);
  };

  const handleBackToUpload = () => {
    router.push("/upload");
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

  return (
    <div className="main-layout">
      <Sidebar />
      <div className="main-content">
        <div className="history-container">
          <div className="history-header">
            <div>
              <h1 className="history-title">상담 기록</h1>
              <p className="history-subtitle">총 {total}개의 기록</p>
            </div>
            <button onClick={handleBackToUpload} className="upload-btn">
              <Mic size={18} /> 새 음성 업로드
            </button>
          </div>

          {error && (
            <div className="error-message">
              {error}
              <button onClick={fetchRecords} className="retry-btn">
                다시 시도
              </button>
            </div>
          )}

          {records.length === 0 ? (
            <div className="empty-state">
              <p>아직 기록이 없습니다.</p>
              <button onClick={handleBackToUpload} className="upload-btn">
                첫 음성 업로드하기
              </button>
            </div>
          ) : (
            <div className="records-grid">
              {records.map((record) => (
                <div
                  key={record.id}
                  className="record-card"
                  onClick={() => handleRecordClick(record.id)}
                >
                  <div className="record-title">{record.title}</div>
                  <div className="record-info">
                    <span className="info-item">
                      <Users size={14} /> {record.total_speakers}명
                    </span>
                  </div>
                  <div className="record-date">
                    {formatDate(record.created_at)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
