import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar.js";
import Table from "./components/Table.js";
import Delete from "./components/Delete.js";
import Verified from "./components/Verified.js";
import History from "./components/History.js";
import Login from "./components/Login.js";
import RequireAuth from "./components/RequireAuth.js";

const withAuth = (element) => <RequireAuth>{element}</RequireAuth>;

function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={withAuth(<Table />)} />
        <Route path="/Table" element={withAuth(<Table />)} />
        <Route path="/Verified" element={withAuth(<Verified />)} />
        <Route path="/Delete" element={withAuth(<Delete />)} />
        <Route path="/History" element={withAuth(<History />)} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export default App;
