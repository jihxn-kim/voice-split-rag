'use client';

import { useEffect, useState } from 'react';

interface Speaker {
  speaker: string;
  total_words: number;
}

interface Segment {
  speaker: string;
  text: string;
  start: number;
  end: number;
}

interface VoiceRecordDetail {
  id: number;
  title: string;
  total_speakers: number;
  full_transcript: string;
  speakers_data: Speaker[];
  segments_data: Segment[];
  dialogue: string;
  duration: number | null;
  created_at: string;
  updated_at: string | null;
}

interface DetailViewProps {
  recordId: string;
}

export default function DetailView({ recordId }: DetailViewProps) {
  const [record, setRecord] = useState<VoiceRecordDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchRecord = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setError('로그인이 필요합니다.');
        setLoading(false);
        return;
      }

      try {
        const res = await fetch(`/api/voice/records/${recordId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (res.ok) {
          const data = await res.json();
          setRecord(data);
        } else if (res.status === 401) {
          setError('인증이 만료되었습니다.');
        } else {
          setError('기록을 불러올 수 없습니다.');
        }
      } catch (err) {
        console.error('Failed to fetch record:', err);
        setError('기록을 불러오는 중 오류가 발생했습니다.');
      } finally {
        setLoading(false);
      }
    };

    if (recordId) {
      fetchRecord();
    }
  }, [recordId]);

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const parseDialogue = (dialogue: string) => {
    const lines = dialogue.split('\n').filter(line => line.trim());
    return lines.map((line, idx) => {
      const match = line.match(/^\[(\d{2}:\d{2})\]\s*(.+?):\s*(.+)$/);
      if (match) {
        const [, time, speaker, text] = match;
        return { time, speaker, text, key: idx };
      }
      return null;
    }).filter(Boolean);
  };

  if (loading) {
    return (
      <div className="detail-loading">
        <div className="spinner" />
        <p>상담 내용을 불러오는 중...</p>
      </div>
    );
  }

  if (error || !record) {
    return (
      <div className="detail-error">
        <p>{error || '상담 기록을 찾을 수 없습니다.'}</p>
      </div>
    );
  }

  const dialogueItems = parseDialogue(record.dialogue);

  return (
    <div className="detail-view-container">
      <div className="dialogue-section">
        <h3 className="dialogue-title">시간순 대화</h3>
        <div className="dialogue-list">
          {dialogueItems.map((item: any) => (
            <div key={item.key} className="dialogue-item">
              <div className="dialogue-time">{item.time}</div>
              <div className="dialogue-bubble">
                <div className="dialogue-speaker">{item.speaker}</div>
                <div className="dialogue-text">{item.text}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
