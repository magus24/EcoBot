import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "./App";
import { clearSession, saveSession } from "./api.js";

beforeEach(() => {
  clearSession();
});

test("anonymous visitor is redirected to the login screen", () => {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>
  );

  expect(screen.getByRole("heading", { name: "Login" })).toBeInTheDocument();
});

test("operator with a session sees the pending detections table", () => {
  saveSession({ Username: "admin", isAdmin: true, token: "test-token" });

  render(
    <MemoryRouter initialEntries={["/Table"]}>
      <App />
    </MemoryRouter>
  );

  expect(screen.getByText("MAC Address")).toBeInTheDocument();
  expect(screen.getByText("Logout")).toBeInTheDocument();
});
