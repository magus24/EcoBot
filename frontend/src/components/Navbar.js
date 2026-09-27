import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Menu } from "antd";
import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "../navbar.css";
import logo from "../img/notification.gif";
import { api, clearSession, currentUser, getSession } from "../api.js";

const POLL_INTERVAL_MS = 5000;

function Navbar() {
  const [pendingCount, setPendingCount] = useState(0);
  const [selectedKey, setSelectedKey] = useState("home");
  const session = getSession();
  const navigate = useNavigate();

  useEffect(() => {
    if (!session) {
      return undefined;
    }

    const loadCount = async () => {
      try {
        const { data } = await api.get(`/count/${currentUser()}`);
        setPendingCount(data.count);
      } catch (error) {
        // Счётчик не критичен: при 401 интерцептор сам уведомит о протухшем токене.
      }
    };

    loadCount();
    const intervalId = setInterval(loadCount, POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [session]);

  const handleLogout = () => {
    if (!window.confirm("Do you want to logout?")) {
      return;
    }
    clearSession();
    navigate("/login", { replace: true });
  };

  if (!session) {
    return (
      <nav className="topnav-guest">
        <Link to="/login">Login</Link>
      </nav>
    );
  }

  const itemStyle = { backgroundColor: "rgb(105, 181, 231)", color: "black" };

  return (
    <nav>
      <Menu
        className="topnav"
        theme="light"
        mode="horizontal"
        selectedKeys={[selectedKey]}
        onClick={({ key }) => setSelectedKey(key)}
      >
        <Menu.Item key="home" className="menu-item" style={selectedKey === "home" ? itemStyle : null}>
          <Link to="/Table" className="testd">
            Home
          </Link>
        </Menu.Item>

        <Menu.Item
          key="verified"
          className="menu-item"
          style={selectedKey === "verified" ? itemStyle : null}
        >
          <Link to="/Verified">Verified</Link>
        </Menu.Item>

        <Menu.Item
          key="delete"
          className="menu-item"
          style={selectedKey === "delete" ? itemStyle : null}
        >
          <Link to="/Delete">Deleted</Link>
        </Menu.Item>

        <Menu.Item
          key="history"
          className="menu-item"
          style={selectedKey === "history" ? itemStyle : null}
        >
          <Link to="/History">History</Link>
        </Menu.Item>

        <Menu.Item key="logout" className="menu-item">
          <Link to="/login" onClick={handleLogout}>
            Logout
          </Link>
        </Menu.Item>

        <Link to="/Table">
          <img
            className="ghantdi"
            onClick={() => toast(`Remain notification is ${pendingCount}`)}
            src={logo}
            alt="pending detections"
          />
          <span className="notifications-count">{pendingCount}</span>

          <ToastContainer
            position="top-right"
            autoClose={500}
            closeOnClick
            draggable
            theme="dark"
          />
        </Link>
      </Menu>
    </nav>
  );
}

export default Navbar;
