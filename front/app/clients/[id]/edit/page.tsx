'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Sidebar from '../../../../components/Sidebar';
import './edit.css';

interface ClientDetail {
  id: number;
  name: string;
  age: number;
  gender: string;
  consultation_background: string;
  main_complaint: string;
  has_previous_counseling: boolean;
  current_symptoms: string;
  ai_consultation_background: string | null;
  ai_main_complaint: string | null;
  ai_current_symptoms: string | null;
  ai_analysis_completed: boolean;
  created_at: string;
  updated_at: string;
}

export default function ClientEditPage() {
  const router = useRouter();
  const params = useParams();
  const clientId = params.id as string;

  const [client, setClient] = useState<ClientDetail | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // 폼 상태
  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('');
  const [consultationBackground, setConsultationBackground] = useState('');
  const [mainComplaint, setMainComplaint] = useState('');
  const [hasPreviousCounseling, setHasPreviousCounseling] = useState(false);
  const [currentSymptoms, setCurrentSymptoms] = useState('');

  // AI 분석 표시 상태
  const [showAiBackground, setShowAiBackground] = useState(false);
  const [showAiComplaint, setShowAiComplaint] = useState(false);
  const [showAiSymptoms, setShowAiSymptoms] = useState(false);

  // 토스트 알림 및 복사 상태
  const [showToast, setShowToast] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // 클립보드 복사 함수
  const copyToClipboard = async (text: string, fieldName: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(fieldName);
      setShowToast(true);
      setTimeout(() => {
        setShowToast(false);
        setCopiedField(null);
      }, 3000);
    } catch (err) {
      console.error('Failed to copy:', err);
      alert('클립보드 복사에 실패했습니다.');
    }
  };

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
          const data: ClientDetail = await res.json();
          setClient(data);
          
          // 폼 초기화
          setName(data.name);
          setAge(data.age.toString());
          setGender(data.gender);
          setConsultationBackground(data.consultation_background);
          setMainComplaint(data.main_complaint);
          setHasPreviousCounseling(data.has_previous_counseling);
          setCurrentSymptoms(data.current_symptoms);
          
          setIsAuthenticated(true);
        } else if (res.status === 401) {
          localStorage.removeItem('access_token');
          router.push('/login');
        } else {
          alert('내담자 정보를 불러올 수 없습니다.');
          router.push('/clients');
        }
      } catch (error) {
        console.error('Failed to fetch client:', error);
        alert('내담자 정보를 불러오는 중 오류가 발생했습니다.');
        router.push('/clients');
      } finally {
        setIsLoading(false);
      }
    };

    fetchClient();
  }, [clientId, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim() || !age || !gender || !consultationBackground.trim() || 
        !mainComplaint.trim() || !currentSymptoms.trim()) {
      alert('모든 필수 항목을 입력해주세요.');
      return;
    }

    const ageNum = parseInt(age);
    if (isNaN(ageNum) || ageNum < 0 || ageNum > 150) {
      alert('올바른 나이를 입력해주세요.');
      return;
    }

    setIsSaving(true);

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('로그인이 필요합니다.');
      }

      const res = await fetch(`/api/clients/${clientId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: name.trim(),
          age: ageNum,
          gender,
          consultation_background: consultationBackground.trim(),
          main_complaint: mainComplaint.trim(),
          has_previous_counseling: hasPreviousCounseling,
          current_symptoms: currentSymptoms.trim(),
        }),
      });

      if (res.ok) {
        alert('내담자 정보가 수정되었습니다.');
        router.push(`/clients/${clientId}`);
      } else if (res.status === 401) {
        localStorage.removeItem('access_token');
        router.push('/login');
      } else {
        const data = await res.json();
        throw new Error(data.message || '수정에 실패했습니다.');
      }
    } catch (error: any) {
      alert(error.message || '내담자 정보 수정 중 오류가 발생했습니다.');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading || !isAuthenticated || !client) {
    return (
      <div className="main-layout">
        <Sidebar />
        <div className="main-content">
          <div className="loading-screen">
            <div className="spinner" />
            <p>내담자 정보를 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <div className="main-content">
        <div className="edit-container">
          <div className="edit-header">
            <button onClick={() => router.push(`/clients/${clientId}`)} className="back-btn">
              ← 내담자 상세로
            </button>
            <h1 className="page-title">내담자 정보 수정</h1>
          </div>

          <form onSubmit={handleSubmit} className="edit-form">
            <div className="form-group">
              <label htmlFor="name">이름 *</label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="내담자 이름"
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="age">나이 *</label>
                <input
                  id="age"
                  type="number"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  placeholder="나이"
                  min="0"
                  max="150"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="gender">성별 *</label>
                <select
                  id="gender"
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                  required
                >
                  <option value="">선택</option>
                  <option value="남성">남성</option>
                  <option value="여성">여성</option>
                  <option value="기타">기타</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="has_previous_counseling">상담이전경력 *</label>
              <div className="radio-group">
                <label>
                  <input
                    type="radio"
                    checked={hasPreviousCounseling === true}
                    onChange={() => setHasPreviousCounseling(true)}
                  />
                  있음
                </label>
                <label>
                  <input
                    type="radio"
                    checked={hasPreviousCounseling === false}
                    onChange={() => setHasPreviousCounseling(false)}
                  />
                  없음
                </label>
              </div>
            </div>

            <div className="form-group">
              <div className="label-with-ai">
                <label htmlFor="consultation_background">상담 신청 배경 *</label>
                {client.ai_analysis_completed && client.ai_consultation_background && (
                  <button
                    type="button"
                    className="btn-show-ai"
                    onClick={() => setShowAiBackground(!showAiBackground)}
                  >
                    {showAiBackground ? '🔼 AI 분석 숨기기' : '🔽 AI 분석 보기 (1회기 기반)'}
                  </button>
                )}
              </div>
              {showAiBackground && client.ai_consultation_background && (
                <div className="ai-analysis-box">
                  <div className="ai-box-header">
                    <strong>📊 1회기 상담 기반 AI 분석:</strong>
                    <button
                      type="button"
                      className="btn-copy"
                      onClick={() => copyToClipboard(client.ai_consultation_background!, 'aiBackground')}
                      title="클립보드에 복사"
                    >
                      {copiedField === 'aiBackground' ? '✅ 복사 완료' : '📋 복사'}
                    </button>
                  </div>
                  <p>{client.ai_consultation_background}</p>
                </div>
              )}
              <textarea
                id="consultation_background"
                value={consultationBackground}
                onChange={(e) => setConsultationBackground(e.target.value)}
                placeholder="상담을 신청하게 된 배경을 입력하세요"
                rows={4}
                required
              />
            </div>

            <div className="form-group">
              <div className="label-with-ai">
                <label htmlFor="main_complaint">주 호소 문제 *</label>
                {client.ai_analysis_completed && client.ai_main_complaint && (
                  <button
                    type="button"
                    className="btn-show-ai"
                    onClick={() => setShowAiComplaint(!showAiComplaint)}
                  >
                    {showAiComplaint ? '🔼 AI 분석 숨기기' : '🔽 AI 분석 보기 (1회기 기반)'}
                  </button>
                )}
              </div>
              {showAiComplaint && client.ai_main_complaint && (
                <div className="ai-analysis-box">
                  <div className="ai-box-header">
                    <strong>📊 1회기 상담 기반 AI 분석:</strong>
                    <button
                      type="button"
                      className="btn-copy"
                      onClick={() => copyToClipboard(client.ai_main_complaint!, 'aiComplaint')}
                      title="클립보드에 복사"
                    >
                      {copiedField === 'aiComplaint' ? '✅ 복사 완료' : '📋 복사'}
                    </button>
                  </div>
                  <p>{client.ai_main_complaint}</p>
                </div>
              )}
              <textarea
                id="main_complaint"
                value={mainComplaint}
                onChange={(e) => setMainComplaint(e.target.value)}
                placeholder="주요 호소 문제를 입력하세요"
                rows={4}
                required
              />
            </div>

            <div className="form-group">
              <div className="label-with-ai">
                <label htmlFor="current_symptoms">현재 증상 *</label>
                {client.ai_analysis_completed && client.ai_current_symptoms && (
                  <button
                    type="button"
                    className="btn-show-ai"
                    onClick={() => setShowAiSymptoms(!showAiSymptoms)}
                  >
                    {showAiSymptoms ? '🔼 AI 분석 숨기기' : '🔽 AI 분석 보기 (1회기 기반)'}
                  </button>
                )}
              </div>
              {showAiSymptoms && client.ai_current_symptoms && (
                <div className="ai-analysis-box">
                  <div className="ai-box-header">
                    <strong>📊 1회기 상담 기반 AI 분석:</strong>
                    <button
                      type="button"
                      className="btn-copy"
                      onClick={() => copyToClipboard(client.ai_current_symptoms!, 'aiSymptoms')}
                      title="클립보드에 복사"
                    >
                      {copiedField === 'aiSymptoms' ? '✅ 복사 완료' : '📋 복사'}
                    </button>
                  </div>
                  <p>{client.ai_current_symptoms}</p>
                </div>
              )}
              <textarea
                id="current_symptoms"
                value={currentSymptoms}
                onChange={(e) => setCurrentSymptoms(e.target.value)}
                placeholder="현재 증상을 입력하세요"
                rows={4}
                required
              />
            </div>

            <div className="form-actions">
              <button
                type="button"
                onClick={() => router.push(`/clients/${clientId}`)}
                className="btn-cancel"
                disabled={isSaving}
              >
                취소
              </button>
              <button type="submit" className="btn-submit" disabled={isSaving}>
                {isSaving ? '저장 중...' : '저장'}
              </button>
            </div>
          </form>
        </div>

        {/* 토스트 알림 */}
        {showToast && (
          <div className="toast-notification">
            ✅ 클립보드에 복사 완료
          </div>
        )}
      </div>
    </div>
  );
}
