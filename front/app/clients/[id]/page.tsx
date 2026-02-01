'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Sidebar from '../../../components/Sidebar';
import './detail.css';

interface ClientDetail {
  id: number;
  name: string;
  age: number;
  gender: string;
  consultation_background: string;
  main_complaint: string;
  has_previous_counseling: boolean;
  current_symptoms: string;
  created_at: string;
  updated_at: string | null;
}

interface VoiceRecord {
  id: number;
  title: string;
  total_speakers: number;
  duration: number | null;
  created_at: string;
  updated_at: string | null;
}

export default function ClientDetailPage() {
  const router = useRouter();
  const params = useParams();
  const clientId = params.id as string;

  const [client, setClient] = useState<ClientDetail | null>(null);
  const [voiceRecords, setVoiceRecords] = useState<VoiceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (clientId) {
      fetchClientData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId]);

  const fetchClientData = async () => {
    try {
      setLoading(true);
      setError('');

      const token = localStorage.getItem('access_token');
      if (!token) {
        router.push('/login');
        return;
      }

      // 내담자 정보 조회
      const clientRes = await fetch(`/api/clients/${clientId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!clientRes.ok) {
        if (clientRes.status === 401) {
          localStorage.removeItem('access_token');
          router.push('/login');
          return;
        }
        throw new Error('내담자 정보를 불러오는데 실패했습니다.');
      }

      const clientData = await clientRes.json();
      setClient(clientData);

      // 음성 기록 조회
      const recordsRes = await fetch(`/api/clients/${clientId}/voice-records`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (recordsRes.ok) {
        const recordsData = await recordsRes.json();
        setVoiceRecords(recordsData.records || []);
      }
    } catch (err: any) {
      setError(err.message || '오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatTime = (seconds: number | null) => {
    if (!seconds) return 'N/A';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="main-layout">
        <Sidebar />
        <div className="main-content">
          <div className="loading">내담자 정보를 불러오는 중...</div>
        </div>
      </div>
    );
  }

  if (error || !client) {
    return (
      <div className="main-layout">
        <Sidebar />
        <div className="main-content">
          <div className="error-container">
            <p>{error || '내담자를 찾을 수 없습니다.'}</p>
            <button onClick={() => router.push('/clients')} className="back-btn">
              목록으로
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <div className="main-content">
        <div className="client-detail-container">
          <div className="detail-header">
            <button onClick={() => router.push('/clients')} className="back-btn">
              ← 목록으로
            </button>
          </div>

          <div className="client-info-card">
            <div className="client-header">
              <div>
                <h1 className="client-name">{client.name}</h1>
                <div className="client-meta">
                  <span className="meta-badge">{client.age}세</span>
                  <span className="meta-badge">{client.gender}</span>
                  <span className="meta-badge">
                    {client.has_previous_counseling ? '상담경력 있음' : '상담경력 없음'}
                  </span>
                </div>
              </div>
              <button
                onClick={() => router.push(`/clients/${clientId}/upload`)}
                className="upload-voice-btn"
              >
                🎙️ 음성 업로드
              </button>
            </div>

            <div className="info-grid">
              <div className="info-section">
                <h3 className="info-title">상담신청배경</h3>
                <p className="info-text">{client.consultation_background}</p>
              </div>

              <div className="info-section">
                <h3 className="info-title">주호소문제</h3>
                <p className="info-text">{client.main_complaint}</p>
              </div>

              <div className="info-section">
                <h3 className="info-title">현재 증상(본인호소)</h3>
                <p className="info-text">{client.current_symptoms}</p>
              </div>
            </div>

            <div className="info-footer">
              <span className="info-date">등록일: {formatDate(client.created_at)}</span>
            </div>
          </div>

          <div className="voice-records-section">
            <h2 className="section-title">상담 기록 ({voiceRecords.length})</h2>

            {voiceRecords.length === 0 ? (
              <div className="empty-records">
                <p>아직 상담 기록이 없습니다.</p>
                <button
                  onClick={() => router.push(`/clients/${clientId}/upload`)}
                  className="upload-voice-btn"
                >
                  첫 상담 기록 업로드하기
                </button>
              </div>
            ) : (
              <div className="records-list">
                {voiceRecords.map((record) => (
                  <div
                    key={record.id}
                    className="record-item"
                    onClick={() => router.push(`/history/${record.id}`)}
                  >
                    <div className="record-info">
                      <h3 className="record-title">{record.title}</h3>
                      <div className="record-meta">
                        <span className="meta-item">👥 {record.total_speakers}명</span>
                        <span className="meta-item">⏱️ {formatTime(record.duration)}</span>
                      </div>
                    </div>
                    <div className="record-date">{formatDate(record.created_at)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
