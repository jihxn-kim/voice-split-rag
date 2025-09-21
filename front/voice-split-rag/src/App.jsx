import { useEffect, useRef, useState } from "react";
import "./App.css";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [audioDurationSec, setAudioDurationSec] = useState(null);
  const [languageCode, setLanguageCode] = useState("ko-KR");
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const fileInputRef = useRef(null);

  const API_BASE =
    (import.meta && import.meta.env && import.meta.env.VITE_API_BASE_URL) ||
    "http://13.125.196.35:8000";

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
    setTranscript("");
    setErrorMsg("");
  };

  const transcribe = async () => {
    if (!selectedFile) {
      alert("먼저 오디오 파일을 선택하세요.");
      return;
    }
    setIsTranscribing(true);
    setTranscript("");
    setErrorMsg("");
    try {
      const form = new FormData();
      form.append("file", selectedFile);
      form.append("language_code", languageCode);

      const res = await fetch(`${API_BASE}/voice/google-stt`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `요청 실패 (HTTP ${res.status})`);
      }
      const data = await res.json();
      setTranscript((data && data.text) || "");
    } catch (err) {
      setErrorMsg(err?.message || "요청 처리 중 오류가 발생했습니다.");
    } finally {
      setIsTranscribing(false);
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

  return (
    <div className="upload-container">
      <h1 className="title">음성 업로드</h1>

      <div
        className={`dropzone${isDragging ? " dragging" : ""}`}
        onClick={pickFile}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") pickFile();
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
            <button type="button" className="btn" onClick={pickFile}>
              파일 선택
            </button>
          </div>
        )}

        {selectedFile && (
          <div className="selected">
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

            <div className="meta" style={{ justifyContent: "center", gap: 8 }}>
              <label htmlFor="lang" className="sub" style={{ marginRight: 6 }}>
                언어
              </label>
              <select
                id="lang"
                value={languageCode}
                onChange={(e) => setLanguageCode(e.target.value)}
              >
                <option value="ko-KR">한국어 (ko-KR)</option>
                <option value="en-US">English (en-US)</option>
                <option value="ja-JP">日本語 (ja-JP)</option>
              </select>
            </div>

            <div className="actions">
              <button type="button" className="btn" onClick={pickFile}>
                다른 파일 선택
              </button>
              <button
                type="button"
                className="btn secondary"
                onClick={clearSelection}
              >
                지우기
              </button>
              <button
                type="button"
                className="btn"
                onClick={transcribe}
                disabled={isTranscribing}
              >
                {isTranscribing ? "변환 중..." : "STT 변환"}
              </button>
            </div>

            {(isTranscribing || errorMsg || transcript) && (
              <div className="selected" style={{ marginTop: 12 }}>
                {isTranscribing && (
                  <p className="sub" style={{ textAlign: "center" }}>
                    변환 중입니다. 길이에 따라 시간이 걸릴 수 있어요...
                  </p>
                )}
                {errorMsg && (
                  <p
                    className="sub"
                    style={{ color: "#dc2626", textAlign: "center" }}
                  >
                    {errorMsg}
                  </p>
                )}
                {transcript && (
                  <div>
                    <h2 className="title" style={{ fontSize: "1.25rem" }}>
                      인식 결과
                    </h2>
                    <pre
                      style={{
                        whiteSpace: "pre-wrap",
                        background: "#f3f4f6",
                        padding: 12,
                        borderRadius: 8,
                      }}
                    >
                      {transcript}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
