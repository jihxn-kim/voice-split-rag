'use client';

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Mic, ChevronLeft, ChevronRight, Plus, X, Trash2 } from "lucide-react";
import Sidebar from "../components/Sidebar";
import "./page.css";

interface Appointment {
  id: number;
  user_id: number;
  client_id: number;
  client_name: string;
  session_number: number;
  date: string;
  start_time: string;
  end_time: string;
  memo: string | null;
  created_at: string;
}

interface ClientItem {
  id: number;
  name: string;
}

interface UserInfo {
  username: string;
  full_name: string;
  email: string;
}

const DAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'];

function getCalendarDays(year: number, month: number) {
  const firstDay = new Date(year, month - 1, 1).getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  return cells;
}

function formatTime(t: string) {
  return t.slice(0, 5); // "HH:MM:SS" -> "HH:MM"
}

function getDayOfWeek(dateStr: string) {
  const d = new Date(dateStr);
  return DAY_LABELS[d.getDay()];
}

export default function Home() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);

  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth() + 1);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [presetDate, setPresetDate] = useState<string>('');
  const [clients, setClients] = useState<ClientItem[]>([]);
  const [isLoadingAppointments, setIsLoadingAppointments] = useState(false);

  // Modal form state
  const [formClientId, setFormClientId] = useState<number | ''>('');
  const [formSessionNumber, setFormSessionNumber] = useState<number | ''>('');
  const [formDate, setFormDate] = useState('');
  const [formStartTime, setFormStartTime] = useState('');
  const [formEndTime, setFormEndTime] = useState('');
  const [formMemo, setFormMemo] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const getToken = () => localStorage.getItem('access_token');

  // Auth check
  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/login');
      return;
    }

    const fetchUserInfo = async () => {
      try {
        const res = await fetch('/api/auth/me', {
          headers: { 'Authorization': `Bearer ${token}` },
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

  // Fetch appointments for current month
  const fetchAppointments = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    setIsLoadingAppointments(true);
    try {
      const res = await fetch(
        `/api/appointments?year=${currentYear}&month=${currentMonth}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setAppointments(data.appointments || []);
      }
    } catch (error) {
      console.error('Failed to fetch appointments:', error);
    } finally {
      setIsLoadingAppointments(false);
    }
  }, [currentYear, currentMonth]);

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchAppointments();
  }, [isAuthenticated, fetchAppointments]);

  // Fetch clients for the modal dropdown
  useEffect(() => {
    if (!isAuthenticated) return;
    const token = getToken();
    if (!token) return;

    const fetchClients = async () => {
      try {
        const res = await fetch('/api/clients', {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setClients(
            (data.clients || []).map((c: any) => ({ id: c.id, name: c.name }))
          );
        }
      } catch (error) {
        console.error('Failed to fetch clients:', error);
      }
    };

    fetchClients();
  }, [isAuthenticated]);

  // Month navigation
  const goToPrevMonth = () => {
    if (currentMonth === 1) {
      setCurrentYear(currentYear - 1);
      setCurrentMonth(12);
    } else {
      setCurrentMonth(currentMonth - 1);
    }
    setSelectedDate(null);
  };

  const goToNextMonth = () => {
    if (currentMonth === 12) {
      setCurrentYear(currentYear + 1);
      setCurrentMonth(1);
    } else {
      setCurrentMonth(currentMonth + 1);
    }
    setSelectedDate(null);
  };

  // Get appointments for a specific day
  const getAppointmentsForDay = (day: number) => {
    const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return appointments.filter((a) => a.date === dateStr);
  };

  // Date cell click
  const handleDateClick = (day: number) => {
    const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    setSelectedDate(selectedDate === dateStr ? null : dateStr);
  };

  // Open add modal
  const openAddModal = (dateOverride?: string) => {
    const d = dateOverride || '';
    setPresetDate(d);
    setFormDate(d);
    setFormClientId('');
    setFormSessionNumber('');
    setFormStartTime('');
    setFormEndTime('');
    setFormMemo('');
    setShowAddModal(true);
  };

  // Submit new appointment
  const handleSubmit = async () => {
    if (!formClientId || !formSessionNumber || !formDate || !formStartTime || !formEndTime) return;
    setIsSubmitting(true);
    try {
      const token = getToken();
      const res = await fetch('/api/appointments', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: formClientId,
          session_number: formSessionNumber,
          date: formDate,
          start_time: formStartTime + ':00',
          end_time: formEndTime + ':00',
          memo: formMemo || null,
        }),
      });
      if (res.ok) {
        setShowAddModal(false);
        fetchAppointments();
      }
    } catch (error) {
      console.error('Failed to create appointment:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete appointment
  const handleDelete = async (id: number) => {
    const token = getToken();
    try {
      const res = await fetch(`/api/appointments/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok || res.status === 204) {
        fetchAppointments();
      }
    } catch (error) {
      console.error('Failed to delete appointment:', error);
    }
  };

  const calendarDays = getCalendarDays(currentYear, currentMonth);
  const selectedDayAppointments = selectedDate
    ? appointments
        .filter((a) => a.date === selectedDate)
        .sort((a, b) => a.start_time.localeCompare(b.start_time))
    : [];

  const todayStr = (() => {
    const n = new Date();
    return `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, '0')}-${String(n.getDate()).padStart(2, '0')}`;
  })();

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
          <button className="upload-btn-large" onClick={() => router.push('/upload')}>
            <Mic size={20} /> 녹음 파일 업로드하기
          </button>
        </div>

        <div className="calendar-section">
          <div className="calendar-header">
            <div className="calendar-nav">
              <button className="nav-btn" onClick={goToPrevMonth}>
                <ChevronLeft size={20} />
              </button>
              <h2 className="calendar-title">{currentYear}년 {currentMonth}월</h2>
              <button className="nav-btn" onClick={goToNextMonth}>
                <ChevronRight size={20} />
              </button>
            </div>
            <button className="add-schedule-btn" onClick={() => openAddModal()}>
              <Plus size={16} /> 일정 등록
            </button>
          </div>

          {isLoadingAppointments ? (
            <div className="loading-records">
              <div className="spinner-small" />
              <p>일정을 불러오는 중...</p>
            </div>
          ) : (
            <div className="calendar-grid">
              {DAY_LABELS.map((label) => (
                <div key={label} className={`calendar-day-label ${label === '일' ? 'sunday' : ''} ${label === '토' ? 'saturday' : ''}`}>
                  {label}
                </div>
              ))}
              {calendarDays.map((day, idx) => {
                if (day === null) {
                  return <div key={`empty-${idx}`} className="calendar-cell empty" />;
                }
                const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                const dayAppointments = getAppointmentsForDay(day);
                const isSelected = selectedDate === dateStr;
                const isToday = dateStr === todayStr;
                const dayOfWeek = new Date(currentYear, currentMonth - 1, day).getDay();

                return (
                  <div
                    key={day}
                    className={`calendar-cell ${isSelected ? 'selected' : ''} ${isToday ? 'today' : ''} ${dayOfWeek === 0 ? 'sunday' : ''} ${dayOfWeek === 6 ? 'saturday' : ''}`}
                    onClick={() => handleDateClick(day)}
                  >
                    <span className="cell-day">{day}</span>
                    {dayAppointments.length > 0 && (
                      <div className="appointment-dots">
                        {dayAppointments.slice(0, 3).map((appt) => (
                          <span key={appt.id} className="appointment-dot" title={appt.client_name}>
                            {appt.client_name}
                          </span>
                        ))}
                        {dayAppointments.length > 3 && (
                          <span className="appointment-more">+{dayAppointments.length - 3}</span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {selectedDate && (
            <div className="day-detail">
              <div className="day-detail-header">
                <h3 className="day-detail-title">
                  {parseInt(selectedDate.split('-')[1])}월 {parseInt(selectedDate.split('-')[2])}일 ({getDayOfWeek(selectedDate)}) 일정
                </h3>
                <button
                  className="add-day-btn"
                  onClick={() => openAddModal(selectedDate)}
                >
                  <Plus size={14} /> 이 날짜에 일정 추가
                </button>
              </div>

              {selectedDayAppointments.length === 0 ? (
                <p className="no-appointments">등록된 일정이 없습니다.</p>
              ) : (
                <div className="timeline">
                  {selectedDayAppointments.map((appt) => (
                    <div key={appt.id} className="timeline-item">
                      <div className="timeline-time">
                        {formatTime(appt.start_time)} - {formatTime(appt.end_time)}
                      </div>
                      <div className="timeline-content">
                        <span className="timeline-client">{appt.client_name}</span>
                        <span className="timeline-session">{appt.session_number}회차</span>
                        {appt.memo && <span className="timeline-memo">{appt.memo}</span>}
                      </div>
                      <button
                        className="timeline-delete"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(appt.id);
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="add-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>일정 등록</h3>
              <button className="modal-close" onClick={() => setShowAddModal(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="modal-body">
              <div className="form-group">
                <label>내담자</label>
                <select
                  value={formClientId}
                  onChange={(e) => setFormClientId(e.target.value ? Number(e.target.value) : '')}
                >
                  <option value="">선택해주세요</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>회차</label>
                <input
                  type="number"
                  min={1}
                  placeholder="회차 입력"
                  value={formSessionNumber}
                  onChange={(e) => setFormSessionNumber(e.target.value ? Number(e.target.value) : '')}
                />
              </div>

              <div className="form-group">
                <label>날짜</label>
                <input
                  type="date"
                  value={formDate}
                  onChange={(e) => setFormDate(e.target.value)}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>시작 시간</label>
                  <input
                    type="time"
                    value={formStartTime}
                    onChange={(e) => setFormStartTime(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label>종료 시간</label>
                  <input
                    type="time"
                    value={formEndTime}
                    onChange={(e) => setFormEndTime(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>메모 (선택)</label>
                <textarea
                  placeholder="메모를 입력하세요"
                  value={formMemo}
                  onChange={(e) => setFormMemo(e.target.value)}
                  rows={3}
                />
              </div>
            </div>

            <div className="modal-footer">
              <button className="modal-cancel" onClick={() => setShowAddModal(false)}>
                취소
              </button>
              <button
                className="modal-submit"
                onClick={handleSubmit}
                disabled={isSubmitting || !formClientId || !formSessionNumber || !formDate || !formStartTime || !formEndTime}
              >
                {isSubmitting ? '등록 중...' : '등록'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
