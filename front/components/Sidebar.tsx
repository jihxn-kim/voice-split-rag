"use client";

import { useRouter, usePathname } from "next/navigation";
import { Home, Users, FileText, LogOut } from "lucide-react";
import "./Sidebar.css";

export default function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    router.push("/login");
  };

  const menuItems = [
    { name: "홈", path: "/", icon: Home },
    { name: "내담자 관리", path: "/clients", icon: Users },
    { name: "상담 기록", path: "/history", icon: FileText },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <img className="sidebar-logo" src="/logo.png" alt="마음을담다" />
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.path ||
            (item.path !== "/" && pathname.startsWith(item.path));
          return (
            <button
              key={item.path}
              className={`nav-item ${isActive ? "active" : ""}`}
              onClick={() => router.push(item.path)}
            >
              <Icon className="nav-icon" size={20} strokeWidth={isActive ? 2.2 : 1.8} />
              <span className="nav-label">{item.name}</span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <button className="logout-button" onClick={handleLogout}>
          <LogOut size={18} strokeWidth={1.8} />
          <span>로그아웃</span>
        </button>
      </div>
    </div>
  );
}
