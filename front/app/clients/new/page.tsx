'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, AlertCircle } from "lucide-react";
import Sidebar from '../../../components/Sidebar';
import './new.css';

export default function NewClientPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    age: '',
    gender: '남성',
    consultation_background: '',
    main_complaint: '',
    has_previous_counseling: false,
    current_symptoms: '',
  });

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData((prev) => ({ ...prev, [name]: checked }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        router.push('/login');
        return;
      }

      const response = await fetch('/api/clients', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          age: parseInt(formData.age),
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('access_token');
          router.push('/login');
          return;
        }
        const data = await response.json();
        throw new Error(data.detail || '내담자 등록에 실패했습니다.');
      }

      const data = await response.json();
      router.push(`/clients/${data.id}`);
    } catch (err: any) {
      setError(err.message || '오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="main-layout">
      <Sidebar />
      <div className="main-content">
        <div className="new-client-container">
          <div className="page-header">
            <button onClick={() => router.push('/clients')} className="back-btn">
              <ArrowLeft size={16} /> 목록으로
            </button>
            <h1 className="page-title">내담자 등록</h1>
          </div>

          {error && (
            <div className="error-banner">
              <AlertCircle size={18} className="error-icon" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="client-form">
            <div className="form-section">
              <h2 className="section-title">기본 정보</h2>
              
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="name" className="form-label">
                    이름 <span className="required">*</span>
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    className="form-input"
                    required
                    maxLength={100}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="age" className="form-label">
                    나이 <span className="required">*</span>
                  </label>
                  <input
                    type="number"
                    id="age"
                    name="age"
                    value={formData.age}
                    onChange={handleChange}
                    className="form-input"
                    required
                    min="1"
                    max="150"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="gender" className="form-label">
                    성별 <span className="required">*</span>
                  </label>
                  <select
                    id="gender"
                    name="gender"
                    value={formData.gender}
                    onChange={handleChange}
                    className="form-select"
                    required
                  >
                    <option value="남성">남성</option>
                    <option value="여성">여성</option>
                    <option value="기타">기타</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="form-section">
              <h2 className="section-title">상담 정보</h2>

              <div className="form-group">
                <label htmlFor="consultation_background" className="form-label">
                  상담 신청 배경 <span className="required">*</span>
                </label>
                <textarea
                  id="consultation_background"
                  name="consultation_background"
                  value={formData.consultation_background}
                  onChange={handleChange}
                  className="form-textarea"
                  required
                  rows={4}
                  placeholder="내담자가 상담을 신청하게 된 배경을 입력해주세요."
                />
              </div>

              <div className="form-group">
                <label htmlFor="main_complaint" className="form-label">
                  주 호소 문제 <span className="required">*</span>
                </label>
                <textarea
                  id="main_complaint"
                  name="main_complaint"
                  value={formData.main_complaint}
                  onChange={handleChange}
                  className="form-textarea"
                  required
                  rows={4}
                  placeholder="내담자의 주요 호소 문제를 입력해주세요."
                />
              </div>

              <div className="form-group">
                <label htmlFor="current_symptoms" className="form-label">
                  현재 증상 <span className="required">*</span>
                </label>
                <textarea
                  id="current_symptoms"
                  name="current_symptoms"
                  value={formData.current_symptoms}
                  onChange={handleChange}
                  className="form-textarea"
                  required
                  rows={4}
                  placeholder="현재 증상을 입력해주세요."
                />
              </div>

              <div className="form-group checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    name="has_previous_counseling"
                    checked={formData.has_previous_counseling}
                    onChange={handleChange}
                    className="form-checkbox"
                  />
                  <span>상담이전경력 있음</span>
                </label>
              </div>
            </div>

            <div className="form-actions">
              <button
                type="button"
                onClick={() => router.push('/clients')}
                className="cancel-btn"
                disabled={loading}
              >
                취소
              </button>
              <button type="submit" className="submit-btn" disabled={loading}>
                {loading ? '등록 중...' : '등록하기'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
