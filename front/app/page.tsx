'use client';

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Mic, ArrowRight, Clock } from "lucide-react";
import Sidebar from "../components/Sidebar";
import "./page.css";

interface VoiceRecord {
  id: number;
  title: string;
  created_at: string;
  total_speakers: number;
}

interface UserInfo {
  username: string;
  full_name: string;
  email: string;
}

export default function Home() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [recentRecords, setRecentRecords] = useState<VoiceRecord[]>([]);
  const [isLoadingRecords, setIsLoadingRecords] = useState(false);

  // 사용자 정보 가져오기
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    const fetchUserInfo = async () => {
      try {
        const res = await fetch('/api/auth/me', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!res.ok) {
          if (res.status === 401) {
            localStorage.removeItem('access_token');
            router.push('/login');
          }
          return;
        }

        const data = await res.json();
        setUserInfo(data);
        setIsAuthenticated(true);
      } catch (error) {
        console.error('Failed to fetch user info:', error);
      }
    };

    fetchUserInfo();
  }, [router]);

  // 최근 상담 기록 가져오기
  useEffect(() => {
    if (!isAuthenticated) return;

    const fetchRecentRecords = async () => {
      setIsLoadingRecords(true);
      try {
        const token = localStorage.getItem('access_token');
        const res = await fetch('/api/voice/records', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (res.ok) {
          const data = await res.json();
          // data가 { records: [...], total: N } 형태
          const recordsList = data.records || data;
          setRecentRecords(Array.isArray(recordsList) ? recordsList.slice(0, 5) : []);
        }
      } catch (error) {
        console.error('Failed to fetch recent records:', error);
      } finally {
        setIsLoadingRecords(false);
      }
    };

    fetchRecentRecords();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  const handleUploadClick = () => {
    router.push('/upload');
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '방금 전';
    if (diffMins < 60) return `${diffMins}분 전`;
    if (diffHours < 24) return `${diffHours}시간 전`;
    if (diffDays < 7) return `${diffDays}일 전`;
    
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (!isAuthenticated || !userInfo) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>로그인 확인 중...</p>
      </div>
    );
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <div className="main-content">
        <div className="welcome-section">
          <h1 className="welcome-title">
            반갑습니다, <span className="highlight">{userInfo.full_name || userInfo.username}</span> 선생님
          </h1>
          <p className="welcome-subtitle">
            오늘도 따뜻한 상담이 되시길 바랍니다
          </p>
          <button className="upload-btn-large" onClick={handleUploadClick}>
            <Mic size={20} /> 녹음 파일 업로드하기
          </button>
        </div>

        <div className="recent-section">
          <div className="section-header">
            <h2 className="section-title">지난 상담 기록</h2>
            <button
              className="view-all-btn"
              onClick={() => router.push('/history')}
            >
              전체 보기 →
            </button>
          </div>

          {isLoadingRecords ? (
            <div className="loading-records">
              <div className="spinner-small" />
              <p>기록을 불러오는 중...</p>
            </div>
          ) : recentRecords.length === 0 ? (
            <div className="empty-records">
              <p className="empty-text">아직 상담 기록이 없습니다.</p>
              <p className="empty-subtext">첫 번째 상담을 업로드해보세요!</p>
            </div>
          ) : (
            <div className="records-grid">
              {recentRecords.map((record) => (
                <div
                  key={record.id}
                  className="record-card"
                  onClick={() => router.push(`/history/${record.id}`)}
                >
                  <div className="record-card-header">
                    <h3 className="record-card-title">{record.title}</h3>
                    <span className="record-badge">{record.total_speakers}명</span>
                  </div>
                  <p className="record-date">{formatDate(record.created_at)}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
