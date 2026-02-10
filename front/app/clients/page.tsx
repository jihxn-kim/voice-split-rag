'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus } from "lucide-react";
import Sidebar from '../../components/Sidebar';
import './clients.css';

interface Client {
  id: number;
  name: string;
  age: number;
  gender: string;
  main_complaint: string;
  created_at: string;
  total_sessions: number;
  uploaded_sessions: number;
}

export default function ClientsPage() {
  const router = useRouter();
  const [clients, setClients] = useState<Client[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchClients();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchClients = async () => {
    try {
      setLoading(true);
      setError('');

      const token = localStorage.getItem('access_token');
      if (!token) {
        router.push('/login');
        return;
      }

      const response = await fetch('/api/clients', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('access_token');
          router.push('/login');
          return;
        }
        throw new Error('내담자 목록을 가져오는데 실패했습니다.');
      }

      const data = await response.json();
      setClients(data.clients || []);
      setTotal(data.total || 0);
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

  if (loading) {
    return (
      <div className="main-layout">
        <Sidebar />
        <div className="main-content">
          <div className="loading">내담자 목록을 불러오는 중...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <div className="main-content">
        <div className="clients-container">
          <div className="clients-header">
            <div>
              <h1 className="clients-title">내담자 관리</h1>
              <p className="clients-subtitle">총 {total}명의 내담자</p>
            </div>
            <button
              onClick={() => router.push('/clients/new')}
              className="add-client-btn"
            >
              <Plus size={18} /> 내담자 등록
            </button>
          </div>

          {error && (
            <div className="error-message">
              {error}
              <button onClick={fetchClients} className="retry-btn">
                다시 시도
              </button>
            </div>
          )}

          {clients.length === 0 ? (
            <div className="empty-state">
              <p>등록된 내담자가 없습니다.</p>
              <button
                onClick={() => router.push('/clients/new')}
                className="add-client-btn"
              >
                첫 내담자 등록하기
              </button>
            </div>
          ) : (
            <div className="clients-grid">
              {clients.map((client) => {
                const uploadedSessions = client.uploaded_sessions ?? 0;
                const totalSessions = client.total_sessions ?? 0;
                const isCompleted = totalSessions > 0 && uploadedSessions >= totalSessions;
                const sessionLabel = isCompleted ? '완료' : `${uploadedSessions}/${totalSessions}`;

                return (
                  <div
                    key={client.id}
                    className="client-card"
                    onClick={() => router.push(`/clients/${client.id}`)}
                  >
                    <div className="client-card-header">
                      <h3 className="client-name">{client.name}</h3>
                      <div className="client-meta">
                        <span className="client-age">{client.age}세</span>
                        <span className="client-gender">{client.gender}</span>
                      </div>
                    </div>
                    <p className="client-complaint">{client.main_complaint}</p>
                    <div className="client-session-row">
                      <span className="client-session-label">회기</span>
                      <span
                        className={`client-session-badge ${isCompleted ? 'complete' : ''}`}
                      >
                        {sessionLabel}
                      </span>
                    </div>
                    <p className="client-date">등록일: {formatDate(client.created_at)}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
