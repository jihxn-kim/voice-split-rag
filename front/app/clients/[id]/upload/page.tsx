'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { ArrowLeft, Mic, Upload, Music, AlertCircle, CheckCircle, Clock } from "lucide-react";
import Sidebar from '../../../../components/Sidebar';
import './upload.css';

interface ClientInfo {
  id: number;
  name: string;
}

export default function ClientUploadPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const clientId = params.id as string;
  const sessionNumber = searchParams.get('session') ? parseInt(searchParams.get('session')!) : null;

  const [client, setClient] = useState<ClientInfo | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [audioDurationSec, setAudioDurationSec] = useState<number | null>(null);

  const [errorMsg, setErrorMsg] = useState('');
  const [isDiarizing, setIsDiarizing] = useState(false);
  const [diarizationResult, setDiarizationResult] = useState<any>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [shouldAutoDiarize, setShouldAutoDiarize] = useState(false);

  // 내담자 정보 가져오기
  useEffect(() => {
    const fetchClient = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        router.push('/login');
        return;
      }

      try {
        const res = await fetch(`/api/clients/${clientId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (res.ok) {
          const data = await res.json();
          setClient(data);
          setIsAuthenticated(true);
        } else if (res.status === 401) {
          localStorage.removeItem('access_token');
          router.push('/login');
        } else {
          router.push('/clients');
        }
      } catch (error) {
        console.error('Failed to fetch client:', error);
        router.push('/clients');
      }
    };

    fetchClient();
  }, [clientId, router]);

  const pickFile = () => {
    if (fileInputRef.current) fileInputRef.current.click();
  };

  const formatBytes = (bytes: number) => {
    if (!Number.isFinite(bytes)) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex += 1;
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const formatTime = (seconds: number) => {
    if (!Number.isFinite(seconds)) return '';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const mm = String(m).padStart(2, '0');
    const ss = String(s).padStart(2, '0');
    return `${mm}:${ss}`;
  };

  const acceptAudioFile = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    const firstAudio = Array.from(fileList).find(
      (f) => f.type && f.type.startsWith('audio/')
    );
    if (!firstAudio) {
      alert('오디오 파일만 선택할 수 있습니다.');
      return;
    }
    setSelectedFile(firstAudio);
    setShouldAutoDiarize(true);
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    acceptAudioFile(e.target.files);
    e.target.value = '';
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    acceptAudioFile(e.dataTransfer.files);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const clearSelection = () => {
    setSelectedFile(null);
    setAudioDurationSec(null);
    setErrorMsg('');
    setDiarizationResult(null);
  };

  const diarize = async () => {
    if (!selectedFile || !client) {
      alert('파일 또는 내담자 정보를 확인할 수 없습니다.');
      return;
    }
    setIsDiarizing(true);
    setDiarizationResult(null);
    setErrorMsg('');

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('로그인이 필요합니다.');
      }

      // 1단계: Pre-signed URL 요청
      const uploadUrlRes = await fetch('/api/upload-url', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          filename: selectedFile.name,
          content_type: selectedFile.type || 'audio/mpeg',
        }),
      });

      if (!uploadUrlRes.ok) {
        const errJson = await uploadUrlRes.json();
        if (uploadUrlRes.status === 401) {
          localStorage.removeItem('access_token');
          router.push('/login');
        }
        throw new Error(errJson.message || '업로드 URL 생성 실패');
      }

      const { upload_url, s3_key } = await uploadUrlRes.json();

      // 2단계: S3에 직접 업로드
      const uploadRes = await fetch(upload_url, {
        method: 'PUT',
        headers: {
          'Content-Type': selectedFile.type || 'audio/mpeg',
        },
        body: selectedFile,
      });

      if (!uploadRes.ok) {
        throw new Error(`S3 업로드 실패 (HTTP ${uploadRes.status})`);
      }

      // 3단계: 백엔드에 처리 요청 (client_id, session_number 포함)
      const processRes = await fetch('/api/process-audio-speechmatics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          s3_key,
          client_id: parseInt(clientId),
          session_number: sessionNumber,
          language_code: 'ko',
        }),
      });

      if (!processRes.ok) {
        let message = `처리 실패 (HTTP ${processRes.status})`;
        try {
          const errJson = await processRes.clone().json();
          if (errJson && typeof errJson === 'object') {
            message =
              errJson.message || errJson.detail || JSON.stringify(errJson);
          }
        } catch (_) {}
        try {
          const text = await processRes.text();
          if (text) message = text;
        } catch (_) {}
        throw new Error(message);
      }

      const data = await processRes.json();
      setDiarizationResult(data);

      const isQueued = data?.status === 'queued';
      // 처리 접수 시 바로 다른 행동 가능하도록 이동
      setTimeout(() => {
        router.push(`/clients/${clientId}?refresh=${Date.now()}`);
      }, isQueued ? 800 : 2000);
    } catch (err: any) {
      setErrorMsg(err?.message || '화자 구분 처리 중 오류가 발생했습니다.');
    } finally {
      setIsDiarizing(false);
    }
  };

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl('');
      return undefined;
    }
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    return () => {
      URL.revokeObjectURL(url);
    };
  }, [selectedFile]);

  // 파일 선택 후 자동 화자 구분
  useEffect(() => {
    if (shouldAutoDiarize && selectedFile && !isDiarizing) {
      (async () => {
        try {
          await diarize();
        } finally {
          setShouldAutoDiarize(false);
        }
      })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shouldAutoDiarize, selectedFile, isDiarizing]);

  if (!isAuthenticated || !client) {
    return (
      <div className="main-layout upload-page">
        <Sidebar />
        <div className="main-content">
          <div className="loading-screen">
            <div className="spinner" />
            <p>내담자 정보를 확인하는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="main-layout upload-page">
      <Sidebar />
      <div className="main-content">
        <div className="upload-container">
          <div className="upload-header">
            <button onClick={() => router.push(`/clients/${clientId}`)} className="back-btn">
              <ArrowLeft size={16} /> 내담자 상세로
            </button>
            <h1 className="page-title">
              <Mic size={24} /> {client.name} - {sessionNumber ? `${sessionNumber}회기 ` : ''}상담 음성 업로드
            </h1>
          </div>

          <div
            className={`dropzone${isDragging ? ' dragging' : ''}`}
            onClick={() => {
              if (!selectedFile) pickFile();
            }}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if ((e.key === 'Enter' || e.key === ' ') && !selectedFile) pickFile();
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*"
              onChange={onFileChange}
              className="file-input"
            />

            {!selectedFile && (
              <div className="empty-state">
                <div className="upload-icon"><Upload size={48} strokeWidth={1.5} /></div>
                <p className="headline">
                  파일을 여기로 드래그하거나 클릭하여 선택하세요
                </p>
                <p className="sub">지원 형식: MP3, WAV, M4A, FLAC, OGG, AAC 등</p>
                <button
                  type="button"
                  className="btn-select"
                  onClick={(e) => {
                    e.stopPropagation();
                    pickFile();
                  }}
                >
                  파일 선택
                </button>
              </div>
            )}

            {selectedFile && (
              <div className="selected-file">
                {isDiarizing ? (
                  <div className="processing">
                    <div className="spinner-large" />
                    <p className="processing-text">
                      처리 중입니다. 길이에 따라 시간이 걸릴 수 있어요...
                    </p>
                  </div>
                ) : diarizationResult ? (
                  <div className="success">
                    <div className="success-icon">
                      {diarizationResult?.status === 'queued' ? <Clock size={48} strokeWidth={1.5} /> : <CheckCircle size={48} strokeWidth={1.5} />}
                    </div>
                    <h2>
                      {diarizationResult?.status === 'queued'
                        ? '업로드 접수 완료!'
                        : '업로드 완료!'}
                    </h2>
                    <p>
                      {diarizationResult?.status === 'queued'
                        ? '백그라운드에서 처리 중입니다. 완료되면 기록에 표시됩니다.'
                        : '화자 구분이 성공적으로 완료되었습니다.'}
                    </p>
                    <p className="redirect-text">내담자 페이지로 이동합니다...</p>
                  </div>
                ) : (
                  <>
                    <div className="file-info">
                      <div className="file-icon"><Music size={28} /></div>
                      <div className="file-details">
                        <div className="file-name" title={selectedFile.name}>
                          {selectedFile.name}
                        </div>
                        <div className="file-meta">
                          <span>{formatBytes(selectedFile.size)}</span>
                          {Number.isFinite(audioDurationSec) && (
                            <span>• {formatTime(audioDurationSec!)}</span>
                          )}
                        </div>
                      </div>
                    </div>

                    {previewUrl && (
                      <audio
                        className="audio-player"
                        controls
                        src={previewUrl}
                        onLoadedMetadata={(e) =>
                          setAudioDurationSec(e.currentTarget.duration)
                        }
                      />
                    )}

                    {errorMsg && (
                      <div className="error-message">
                        <AlertCircle size={18} className="error-icon" />
                        <p>{errorMsg}</p>
                      </div>
                    )}

                    <button className="btn-clear" onClick={clearSelection}>
                      다른 파일 선택
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
