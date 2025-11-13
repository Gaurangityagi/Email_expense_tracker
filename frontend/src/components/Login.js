import React, { useState } from 'react';
import axios from 'axios';

function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post('http://localhost:5000/login', {
        email,
        password
      });

      if (response.data.success) {
        onLogin(email, password);
      } else {
        setError(response.data.message || 'Login failed');
      }
    } catch (err) {
      setError('Failed to connect to server. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-form">
        <h2>📧 Email Order Analysis</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email Address:</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              required
            />
          </div>

          <div className="form-group">
            <label>App Password:</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your Google App Password"
              required
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={loading}>
            {loading ? 'Connecting...' : 'Login'}
          </button>
        </form>

        <div className="info">
          <p>Note: For Gmail, please use an App Password.</p>
          <a href="https://support.google.com/accounts/answer/185833?hl=en" target="_blank" rel="noopener noreferrer">
            Learn how to create one
          </a>
        </div>
      </div>
    </div>
  );
}

export default Login;
