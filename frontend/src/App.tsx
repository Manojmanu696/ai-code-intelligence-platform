import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Issues from "./pages/Issues";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/issues" element={<Issues />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}