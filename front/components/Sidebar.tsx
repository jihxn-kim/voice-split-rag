"use client";

import { useRouter, usePathname } from "next/navigation";
import "./Sidebar.css";

export default function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    router.push("/login");
  };

  const menuItems = [
    { name: "홈", path: "/", icon: "🏠" },
    { name: "내담자 관리", path: "/clients", icon: "👥" },
    { name: "상담 기록", path: "/history", icon: "📋" },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <img className="sidebar-logo" src="/logo.png" alt="마음을담다" />
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <button
            key={item.path}
            className={`nav-item ${
              pathname === item.path || 
              (item.path !== "/" && pathname.startsWith(item.path)) 
                ? "active" 
                : ""
            }`}
            onClick={() => router.push(item.path)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.name}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button className="logout-button" onClick={handleLogout}>
          🚪 로그아웃
        </button>
      </div>
    </div>
  );
}
