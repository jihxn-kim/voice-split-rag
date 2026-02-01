'use client'

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import "./page.css";

export default function Home() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [audioDurationSec, setAudioDurationSec] = useState<number | null>(null);

  const [errorMsg, setErrorMsg] = useState("");
  const [isDiarizing, setIsDiarizing] = useState(false);
  const [diarizationResult, setDiarizationResult] = useState<any>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [shouldAutoDiarize, setShouldAutoDiarize] = useState(false);

  // 로그아웃 함수
  const handleLogout = () => {
    localStorage.removeItem('access_token');
    router.push('/login');
  };

  const pickFile = () => {
    if (fileInputRef.current) fileInputRef.current.click();
  };

  const formatBytes = (bytes: number) => {
    if (!Number.isFinite(bytes)) return "";
    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex += 1;
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const formatTime = (seconds: number) => {
    if (!Number.isFinite(seconds)) return "";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const mm = String(m).padStart(2, "0");
    const ss = String(s).padStart(2, "0");
    return `${mm}:${ss}`;
  };

  const acceptAudioFile = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    const firstAudio = Array.from(fileList).find(
      (f) => f.type && f.type.startsWith("audio/")
    );
    if (!firstAudio) {
      alert("오디오 파일만 선택할 수 있습니다.");
      return;
    }
    setSelectedFile(firstAudio);
    setShouldAutoDiarize(true);
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    acceptAudioFile(e.target.files);
    e.target.value = "";
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
    setErrorMsg("");
    setDiarizationResult(null);
  };

  const diarize = async () => {
    if (!selectedFile) {
      alert("먼저 오디오 파일을 선택하세요.");
      return;
    }
    setIsDiarizing(true);
    setDiarizationResult(null);
    setErrorMsg("");
    
    try {
      // JWT 토큰 가져오기 (필수)
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error("로그인이 필요합니다.");
      }

      // 1단계: Pre-signed URL 요청
      const uploadUrlRes = await fetch("/api/upload-url", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          filename: selectedFile.name,
          content_type: selectedFile.type || "audio/mpeg",
        }),
      });

      if (!uploadUrlRes.ok) {
        const errJson = await uploadUrlRes.json();
        // 401이면 로그아웃
        if (uploadUrlRes.status === 401) {
          localStorage.removeItem('access_token');
          router.push('/login');
        }
        throw new Error(errJson.message || "업로드 URL 생성 실패");
      }

      const { upload_url, s3_key } = await uploadUrlRes.json();

      // 2단계: S3에 직접 업로드
      const uploadRes = await fetch(upload_url, {
        method: "PUT",
        headers: {
          "Content-Type": selectedFile.type || "audio/mpeg",
        },
        body: selectedFile,
      });

      if (!uploadRes.ok) {
        throw new Error(`S3 업로드 실패 (HTTP ${uploadRes.status})`);
      }

      // 3단계: 백엔드에 처리 요청
      const processRes = await fetch("/api/process-audio", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          s3_key,
          language_code: "ko",
        }),
      });

      if (!processRes.ok) {
        let message = `처리 실패 (HTTP ${processRes.status})`;
        try {
          const errJson = await processRes.clone().json();
          if (errJson && typeof errJson === "object") {
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
    } catch (err: any) {
      setErrorMsg(err?.message || "화자 구분 처리 중 오류가 발생했습니다.");
    } finally {
      setIsDiarizing(false);
    }
  };


  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl("");
      return undefined;
    }
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    return () => {
      URL.revokeObjectURL(url);
    };
  }, [selectedFile]);

  // 인증 체크 (필수)
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
    } else {
      setIsAuthenticated(true);
    }
  }, [router]);

  // 파일 선택 후 자동 화자 구분 한 번 실행
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

  // 인증되지 않았으면 로딩 표시
  if (!isAuthenticated) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        fontSize: '1.2rem',
        color: '#6b7280'
      }}>
        로그인 확인 중...
      </div>
    );
  }

  return (
    <div className="upload-container">
      <div className="header">
        <h1 className="title">음성 업로드</h1>
        <button onClick={handleLogout} className="logout-btn">
          로그아웃
        </button>
      </div>

      <div
        className={`dropzone${isDragging ? " dragging" : ""}`}
        onClick={() => {
          if (!selectedFile) pickFile();
        }}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && !selectedFile) pickFile();
        }}
        aria-label="오디오 파일 드래그 앤 드롭 또는 클릭하여 선택"
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
            <p className="headline">
              파일을 여기로 드래그하거나 클릭하여 선택하세요
            </p>
            <p className="sub">지원 형식: MP3, WAV, M4A, FLAC, OGG, AAC 등 모든 오디오 파일</p>
            <button
              type="button"
              className="btn"
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
          <div className="selected">
            {isDiarizing ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 12,
                  padding: 20,
                }}
              >
                <div className="spinner" aria-label="로딩" />
                <p className="sub" style={{ textAlign: "center" }}>
                  처리 중입니다. 길이에 따라 시간이 걸릴 수 있어요...
                </p>
              </div>
            ) : (
              <>
                <div className="meta">
                  <div className="name" title={selectedFile.name}>
                    {selectedFile.name}
                  </div>
                  <div className="size">{formatBytes(selectedFile.size)}</div>
                  {Number.isFinite(audioDurationSec) && (
                    <div className="duration">
                      길이 {formatTime(audioDurationSec!)}
                    </div>
                  )}
                </div>

                {previewUrl && (
                  <audio
                    className="player"
                    controls
                    src={previewUrl}
                    onLoadedMetadata={(e) =>
                      setAudioDurationSec(e.currentTarget.duration)
                    }
                  />
                )}

                {(errorMsg || diarizationResult) && (
                  <div className="selected" style={{ marginTop: 12 }}>
                    {errorMsg && (
                      <p
                        className="sub"
                        style={{ color: "#dc2626", textAlign: "center" }}
                      >
                        {errorMsg}
                      </p>
                    )}

                    {diarizationResult && (
                      <div>
                        <h2 className="title" style={{ fontSize: "1.25rem" }}>
                          화자 구분 결과 ({diarizationResult.total_speakers}명)
                        </h2>
                        {diarizationResult.dialogue && (
                          <div style={{ marginBottom: 16 }}>
                            <h3
                              style={{
                                fontSize: "1rem",
                                marginBottom: 8,
                                color: "#374151",
                              }}
                            >
                              시간순 대화
                            </h3>
                            <pre
                              style={{
                                whiteSpace: "pre-wrap",
                                background: "#f3f4f6",
                                padding: 12,
                                borderRadius: 8,
                                fontSize: "0.9rem",
                              }}
                            >
                              {diarizationResult.dialogue}
                            </pre>
                          </div>
                        )}
                        <div style={{ marginBottom: 16 }}>
                          <h3
                            style={{
                              fontSize: "1rem",
                              marginBottom: 8,
                              color: "#374151",
                            }}
                          >
                            전체 대화
                          </h3>
                          <pre
                            style={{
                              whiteSpace: "pre-wrap",
                              background: "#f3f4f6",
                              padding: 12,
                              borderRadius: 8,
                              fontSize: "0.9rem",
                            }}
                          >
                            {diarizationResult.full_transcript}
                          </pre>
                        </div>
                        <div>
                          <h3
                            style={{
                              fontSize: "1rem",
                              marginBottom: 8,
                              color: "#374151",
                            }}
                          >
                            화자별 발화
                          </h3>
                          {diarizationResult.speakers.map((speaker: any, index: number) => (
                            <div
                              key={speaker.speaker_id}
                              style={{
                                marginBottom: 12,
                                padding: 12,
                                background: "#f9fafb",
                                borderRadius: 8,
                                border: "1px solid #e5e7eb",
                              }}
                            >
                              <div
                                style={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "center",
                                  marginBottom: 8,
                                }}
                              >
                                <h4
                                  style={{
                                    margin: 0,
                                    color: "#1f2937",
                                    fontSize: "0.9rem",
                                  }}
                                >
                                  화자 {speaker.speaker_id}
                                </h4>
                                <div
                                  style={{
                                    fontSize: "0.8rem",
                                    color: "#6b7280",
                                  }}
                                >
                                  {formatTime(speaker.start_time)} -{" "}
                                  {formatTime(speaker.end_time)}(
                                  {formatTime(speaker.duration)})
                                </div>
                              </div>
                              <p
                                style={{
                                  margin: 0,
                                  fontSize: "0.9rem",
                                  lineHeight: 1.4,
                                }}
                              >
                                {speaker.text}
                              </p>
                              {diarizationResult.split_audio_files && (
                                <div
                                  style={{
                                    marginTop: 8,
                                    fontSize: "0.8rem",
                                    color: "#6b7280",
                                  }}
                                >
                                  분할된 오디오:{" "}
                                  {speaker.filename ||
                                    `speaker_${speaker.speaker_id}.wav`}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
