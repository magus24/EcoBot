import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../login.css";
import { api, saveSession } from "../api.js";

const Login = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const { data } = await api.post("/login", { username, password });
      saveSession(data);
      navigate("/Table", { replace: true });
    } catch (requestError) {
      setError("Invalid username or password");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="bg-login" id="bg-login2">
        <div className="login">
          <div className="login-container">
            <h3>Login</h3>
            <br />
            <div className="txt">Username</div>
            <div>
              <input
                className="Email"
                type="text"
                id="username"
                placeholder=" Username..."
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </div>
            <br />
            <div>
              <div className="txt">Password</div>

              <input
                className="Password"
                type="password"
                id="password"
                placeholder=" Password..."
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <br />
              <br />
              <br />

              <label>
                <input type="checkbox" name="remember" /> Remember me
              </label>

              <div className="forgot">
                <a href="#">Forgot Password?</a>
              </div>
            </div>
            {error ? <p className="login-error">{error}</p> : null}
            <button className="bt-login" type="submit" disabled={submitting}>
              {submitting ? "Signing in..." : "Login"}
            </button>
          </div>
          <div className="side-img"></div>
        </div>
      </div>
    </form>
  );
};

export default Login;
