import { useEffect, useRef, useState } from "react";
import "./App.css";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [audioDurationSec, setAudioDurationSec] = useState(null);

  const [errorMsg, setErrorMsg] = useState("");
  const [isDiarizing, setIsDiarizing] = useState(false);
  const [diarizationResult, setDiarizationResult] = useState(null);

  const fileInputRef = useRef(null);
  const [shouldAutoDiarize, setShouldAutoDiarize] = useState(false);

  const API_BASE =
    (import.meta && import.meta.env && import.meta.env.VITE_API_BASE_URL) ||
    "http://localhost:8000";
  // "http://13.125.196.35:8000";

  const pickFile = () => {
    if (fileInputRef.current) fileInputRef.current.click();
  };

  const formatBytes = (bytes) => {
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

  const formatTime = (seconds) => {
    if (!Number.isFinite(seconds)) return "";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const mm = String(m).padStart(2, "0");
    const ss = String(s).padStart(2, "0");
    return `${mm}:${ss}`;
  };

  const acceptAudioFile = (fileList) => {
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

  const onFileChange = (e) => {
    acceptAudioFile(e.target.files);
    e.target.value = "";
  };

  const onDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    acceptAudioFile(e.dataTransfer.files);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  };

  const onDragLeave = (e) => {
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
      const form = new FormData();
      form.append("file", selectedFile);

      const res = await fetch(`${API_BASE}/voice/speaker-diarization-v2`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        let message = `요청 실패 (HTTP ${res.status})`;
        try {
          const errJson = await res.clone().json();
          if (errJson && typeof errJson === "object") {
            message =
              errJson.message || errJson.detail || JSON.stringify(errJson);
          }
        } catch (_) {}
        try {
          const text = await res.text();
          if (text) message = text;
        } catch (_) {}
        throw new Error(message);
      }
      const data = await res.json();
      setDiarizationResult(data);
    } catch (err) {
      setErrorMsg(err?.message || "화자 구분 처리 중 오류가 발생했습니다.");
    } finally {
      setIsDiarizing(false);
    }
  };

  const diarizeAndSplit = async () => {
    if (!selectedFile) {
      alert("먼저 오디오 파일을 선택하세요.");
      return;
    }
    setIsDiarizing(true);
    setDiarizationResult(null);
    setErrorMsg("");
    try {
      const form = new FormData();
      form.append("file", selectedFile);

      const res = await fetch(
        `${API_BASE}/voice/speaker-diarization/split-audio`,
        {
          method: "POST",
          body: form,
        }
      );
      if (!res.ok) {
        let message = `요청 실패 (HTTP ${res.status})`;
        try {
          const errJson = await res.clone().json();
          if (errJson && typeof errJson === "object") {
            message =
              errJson.message || errJson.detail || JSON.stringify(errJson);
          }
        } catch (_) {}
        try {
          const text = await res.text();
          if (text) message = text;
        } catch (_) {}
        throw new Error(message);
      }
      const data = await res.json();
      setDiarizationResult(data);
    } catch (err) {
      setErrorMsg(
        err?.message || "화자 구분 및 오디오 분할 처리 중 오류가 발생했습니다."
      );
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
  }, [shouldAutoDiarize, selectedFile, isDiarizing]);

  return (
    <div className="upload-container">
      <h1 className="title">음성 업로드</h1>

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
            <p className="sub">지원: mp3, wav, m4a 등 오디오 형식</p>
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
                      길이 {formatTime(audioDurationSec)}
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
                          {diarizationResult.speakers.map((speaker, index) => (
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

export default App;
