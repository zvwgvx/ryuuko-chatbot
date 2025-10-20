import React, { useState } from 'react';
import { loginUser } from '../apiClient';
import './Form.css';

const LoginForm = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const response = await loginUser({ username, password });
      const { access_token } = response.data;
      onLoginSuccess(access_token);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'An unexpected error occurred. Please try again.';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form className="form-container" onSubmit={handleSubmit}>
      <h2>Welcome Back</h2>

      {error && <div className="form-error">{error}</div>}

      <div className="form-group">
        <input
          id="login-username"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          placeholder=" "
          autoComplete="username"
        />
        <label htmlFor="login-username">Username</label>
      </div>

      <div className="form-group">
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          placeholder=" "
          autoComplete="current-password"
        />
        <label htmlFor="login-password">Password</label>
      </div>

      <button type="submit" className="form-button" disabled={isLoading}>
        {isLoading ? (
          <>
            <div className="spinner"></div>
            <span>Signing in...</span>
          </>
        ) : (
          'Sign In'
        )}
      </button>
    </form>
  );
};

export default LoginForm;