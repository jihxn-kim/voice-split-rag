'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import Sidebar from '../../../components/Sidebar';
import './detail.css';

interface ClientDetail {
  id: number;
  name: string;
  age: number;
  gender: string;
  total_sessions: number;
  consultation_background: string;
  main_complaint: string;
  has_previous_counseling: boolean;
  current_symptoms: string;
  ai_consultation_background: string | null;
  ai_main_complaint: string | null;
  ai_current_symptoms: string | null;
  ai_analysis_completed: boolean;
  created_at: string;
  updated_at: string | null;
}

interface VoiceRecord {
  id: number;
  title: string;
  total_speakers: number;
  duration: number | null;
  session_number: number | null;
  created_at: string;
  updated_at: string | null;
}

interface UploadStatus {
  id: number;
  session_number: number | null;
  status: 'queued' | 'processing' | 'failed' | string;
  error_message?: string | null;
  created_at: string;
  updated_at: string | null;
}

export default function ClientDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const clientId = params.id as string;

  const [client, setClient] = useState<ClientDetail | null>(null);
  const [voiceRecords, setVoiceRecords] = useState<VoiceRecord[]>([]);
  const [pendingUploads, setPendingUploads] = useState<UploadStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [newSessionCount, setNewSessionCount] = useState('');
  const [showRecordsView, setShowRecordsView] = useState(true); // 기본적으로 펼쳐진 상태
  const hasPendingRef = useRef(false);

  useEffect(() => {
    if (clientId) {
      fetchClientData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId, searchParams]);

  const fetchVoiceRecords = useCallback(async (tokenOverride?: string) => {
    try {
      const token = tokenOverride || localStorage.getItem('access_token');
      if (!token) {
        router.push('/login');
        return;
      }

      const recordsRes = await fetch(`/api/clients/${clientId}/voice-records`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (recordsRes.ok) {
        const recordsData = await recordsRes.json();
        const records = recordsData?.records;
        setVoiceRecords(Array.isArray(records) ? records : Array.isArray(recordsData) ? recordsData : []);
      } else if (recordsRes.status === 401) {
        localStorage.removeItem('access_token');
        router.push('/login');
      }
    } catch (err) {
      console.error('Failed to fetch voice records:', err);
    }
  }, [clientId, router]);

  const fetchUploadStatus = useCallback(async (tokenOverride?: string) => {
    try {
      const token = tokenOverride || localStorage.getItem('access_token');
      if (!token) {
        router.push('/login');
        return;
      }

      const statusRes = await fetch(`/api/clients/${clientId}/upload-status`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (statusRes.ok) {
        const statusData = await statusRes.json();
        const uploads = Array.isArray(statusData?.uploads) ? statusData.uploads : [];
        setPendingUploads(uploads);

        const hasPending = uploads.some(
          (upload: UploadStatus) =>
            upload.status === 'queued' || upload.status === 'processing'
        );
        if (hasPendingRef.current && !hasPending) {
          await fetchVoiceRecords(token);
        }
        hasPendingRef.current = hasPending;
      } else if (statusRes.status === 401) {
        localStorage.removeItem('access_token');
        router.push('/login');
      }
    } catch (err) {
      console.error('Failed to fetch upload status:', err);
    }
  }, [clientId, fetchVoiceRecords, router]);

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

      await fetchVoiceRecords(token);
      await fetchUploadStatus(token);
    } catch (err: any) {
      setError(err.message || '오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!clientId) return;
    const hasPending = pendingUploads.some(
      (upload) => upload.status === 'queued' || upload.status === 'processing'
    );
    if (!hasPending) return;

    const intervalId = setInterval(() => {
      fetchUploadStatus();
    }, 5000);

    return () => clearInterval(intervalId);
  }, [clientId, pendingUploads, fetchUploadStatus]);

  const updateSessionCount = async () => {
    const count = parseInt(newSessionCount);
    if (isNaN(count) || count < 1 || count > 100) {
      alert('1에서 100 사이의 숫자를 입력해주세요.');
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/api/clients/${clientId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ total_sessions: count }),
      });

      if (res.ok) {
        // 업데이트 후 전체 데이터 다시 로드
        await fetchClientData();
        setShowSessionModal(false);
        setNewSessionCount('');
      } else {
        alert('회기 수 수정에 실패했습니다.');
      }
    } catch (err) {
      console.error('Failed to update sessions:', err);
      alert('회기 수 수정 중 오류가 발생했습니다.');
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

  const getSessionBoxes = () => {
    const boxes = [];
    const totalSessions = client?.total_sessions || 0;
    
    // 회기가 0이면 빈 배열 반환
    if (totalSessions === 0) {
      return [];
    }

    const uploadsBySession = new Map<number, UploadStatus>();
    pendingUploads.forEach((upload) => {
      const sessionNum = Number(upload.session_number);
      if (!Number.isFinite(sessionNum) || sessionNum < 1) return;
      const existing = uploadsBySession.get(sessionNum);
      if (!existing) {
        uploadsBySession.set(sessionNum, upload);
        return;
      }
      const existingTime = new Date(existing.created_at).getTime();
      const nextTime = new Date(upload.created_at).getTime();
      if (nextTime > existingTime) {
        uploadsBySession.set(sessionNum, upload);
      }
    });
    
    for (let i = 1; i <= totalSessions; i++) {
      // session_number로 해당 회기의 기록 찾기
      const record = voiceRecords.find((r: any) => {
        // session_number가 숫자일 수도 있고 문자열일 수도 있으므로 비교
        const sessionNum = typeof r.session_number === 'string' 
          ? parseInt(r.session_number, 10) 
          : r.session_number;
        return sessionNum === i;
      });
      boxes.push({
        sessionNumber: i,
        record: record || null,
        upload: uploadsBySession.get(i) || null,
      });
    }
    return boxes;
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
              <div className="header-buttons">
                <button
                  onClick={() => setShowSessionModal(true)}
                  className="session-btn"
                >
                  📊 회기 추가
                </button>
              </div>
            </div>

            <div className="info-grid">
              <div className="info-section">
                <h3 className="info-title">상담 신청 배경 (입력)</h3>
                <p className="info-text">{client.consultation_background}</p>
              </div>

              <div className="info-section">
                <h3 className="info-title">주 호소 문제 (입력)</h3>
                <p className="info-text">{client.main_complaint}</p>
              </div>

              <div className="info-section">
                <h3 className="info-title">현재 증상</h3>
                <p className="info-text">{client.current_symptoms}</p>
              </div>
            </div>

            <div className="action-buttons">
              <button
                onClick={() => router.push(`/clients/${clientId}/edit`)}
                className="edit-btn"
              >
                ✏️ 정보 수정
              </button>
            </div>

            <div className="info-footer">
              <span className="info-date">등록일: {formatDate(client.created_at)}</span>
            </div>
          </div>

          {/* AI 분석 결과 섹션 - 1회기 기반 */}
          {client.ai_analysis_completed && (
            <div className="ai-analysis-section">
              <h2 className="ai-section-title">📊 1회기 상담 기반 AI 분석</h2>
              
              <div className="ai-info-grid">
                {client.ai_consultation_background && (
                  <div className="ai-info-section">
                    <h3 className="ai-info-title">✨ 상담 신청 배경</h3>
                    <p className="ai-info-text">{client.ai_consultation_background}</p>
                  </div>
                )}

                {client.ai_main_complaint && (
                  <div className="ai-info-section">
                    <h3 className="ai-info-title">💡 주 호소 문제</h3>
                    <p className="ai-info-text">{client.ai_main_complaint}</p>
                  </div>
                )}

                {client.ai_current_symptoms && (
                  <div className="ai-info-section">
                    <h3 className="ai-info-title">🩺 현재 증상</h3>
                    <p className="ai-info-text">{client.ai_current_symptoms}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="records-summary">
            <button
              onClick={() => setShowRecordsView(!showRecordsView)}
              className="records-summary-btn"
            >
              <span className="records-summary-text">
                📋 상담 기록 ({voiceRecords.length}
                {client.total_sessions > 0 ? `/${client.total_sessions}` : ''})
              </span>
              <span className="toggle-icon">{showRecordsView ? '▲' : '▼'}</span>
            </button>
          </div>

          {showRecordsView && (
            <div className="session-boxes-container">
              {client.total_sessions === 0 ? (
                <div className="no-sessions-message">
                  <p>📊 회기를 먼저 추가한 후, 회기별로 상담 음성을 업로드할 수 있습니다.</p>
                  <p className="sub-text">
                    상단의 &quot;회기 추가&quot; 버튼을 눌러 전체 회기 수를 설정해주세요.
                  </p>
                </div>
              ) : (
                <div className="session-boxes-grid">
                  {getSessionBoxes().map((box) => {
                    const uploadStatus = box.upload?.status;
                    const isUploading = uploadStatus === 'queued' || uploadStatus === 'processing';
                    const isFailed = uploadStatus === 'failed';
                    const record = box.record;
                    const hasRecord = Boolean(record);
                    const showFailed = isFailed && !hasRecord && !isUploading;
                    const boxState = isUploading
                      ? 'uploading'
                      : hasRecord
                        ? 'filled'
                        : showFailed
                          ? 'failed'
                          : 'empty';
                    return (
                      <div
                        key={box.sessionNumber}
                        className={`session-box ${boxState}`}
                        onClick={() => {
                          if (isUploading) return;
                          if (box.record) {
                            router.push(`/history/${box.record.id}`);
                          } else {
                            router.push(`/clients/${clientId}/upload?session=${box.sessionNumber}`);
                          }
                        }}
                      >
                        <div className="session-number">{box.sessionNumber}회기</div>
                        {isUploading ? (
                          <div className="session-uploading">
                            <div className="uploading-spinner" />
                            <div className="uploading-text">업로드 중...</div>
                          </div>
                        ) : record ? (
                          <div className="session-info">
                            <div className="session-title">{record.title}</div>
                            <div className="session-date">
                              {formatDate(record.created_at)}
                            </div>
                          </div>
                        ) : showFailed ? (
                          <div className="session-failed">
                            <span className="failed-icon">⚠️</span>
                            <span className="failed-text">업로드 실패</span>
                            <span className="failed-subtext">클릭해서 다시 업로드</span>
                          </div>
                        ) : (
                          <div className="session-empty">
                            <span className="upload-icon">📁</span>
                            <span className="upload-text">업로드</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* 회기 추가 모달 */}
          {showSessionModal && (
            <div className="modal-overlay" onClick={() => setShowSessionModal(false)}>
              <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <h2 className="modal-title">회기 수 변경</h2>
                <p className="modal-desc">전체 상담 회기 수를 입력해주세요 (1-100)</p>
                <input
                  type="number"
                  value={newSessionCount}
                  onChange={(e) => setNewSessionCount(e.target.value)}
                  placeholder={`현재: ${client.total_sessions}회기`}
                  min="1"
                  max="100"
                  className="modal-input"
                  autoFocus
                />
                <div className="modal-actions">
                  <button
                    onClick={() => {
                      setShowSessionModal(false);
                      setNewSessionCount('');
                    }}
                    className="modal-btn-cancel"
                  >
                    취소
                  </button>
                  <button onClick={updateSessionCount} className="modal-btn-confirm">
                    변경
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
