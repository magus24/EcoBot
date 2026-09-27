import axios from "axios";

/**
 * Единая точка общения с EcoBot API.
 *
 * Адрес берётся из переменной окружения REACT_APP_API_URL (файл frontend/.env),
 * поэтому фронтенд одинаково работает и с локальным бэкендом, и с удалённым:
 *   REACT_APP_API_URL=https://api.example.com npm start
 */
export const API_BASE_URL =
  process.env.REACT_APP_API_URL || "http://127.0.0.1:5000";

const SESSION_KEY = "ecobot.session";

/** Текущая сессия: { Username, isAdmin, token } или null. */
export function getSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY)) || null;
  } catch (error) {
    return null;
  }
}

export function saveSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

/** Логин оператора: "admin" видит все участки, остальные — только свой. */
export function currentUser() {
  return getSession()?.Username ?? "admin";
}

export const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const token = getSession()?.token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Токен протух или был отозван — возвращаем оператора на страницу входа.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && getSession()) {
      clearSession();
      window.location.assign("/login");
    }
    return Promise.reject(error);
  }
);

/**
 * Ссылка на сохранённый кадр. <img> не умеет слать заголовки,
 * поэтому токен передаётся query-параметром.
 */
export function mediaUrl(imagePath) {
  const token = getSession()?.token;
  const query = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${API_BASE_URL}/media/${encodeURIComponent(imagePath)}${query}`;
}
