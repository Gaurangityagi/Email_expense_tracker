import React, { useState } from "react";
import axios from "axios";

function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const API = process.env.REACT_APP_BACKEND_URL;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await axios.post(`${API}/login`, {
        email,
        password,
      });

      if (response.data.success) {
        onLogin(email, password);
      } else {
        setError("Login failed. Check your credentials.");
      }
    } catch (err) {
      setError("Failed to connect to server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-form">
        <h2>OrderInbox</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email:</label>
            <input
              type="email"
              value={email}
              required
              placeholder="Your Gmail address"
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>App Password:</label>
            <input
              type="password"
              value={password}
              required
              placeholder="Gmail App Password"
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <button type="submit" disabled={loading}>
            {loading ? "Connecting..." : "Login"}
          </button>
        </form>
        <div className="info">
          Set up your app password (use Python Email Script as app name).{" "}
          <a
            href="https://support.google.com/mail/answer/185833?hl=en"
            target="_blank"
            rel="noopener noreferrer"
          >
            Learn more
          </a>
        </div>
      </div>
    </div>
  );
}

export default Login;
