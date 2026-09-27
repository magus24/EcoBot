import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getSession } from "../api.js";

/** Пускает дальше только операторов с активной сессией. */
export default function RequireAuth({ children }) {
  const location = useLocation();

  if (!getSession()) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}
