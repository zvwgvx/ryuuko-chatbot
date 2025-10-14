import React, { useState } from 'react';
import { loginUser } from '../apiClient';
import './Form.css';

const LoginForm = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      const response = await loginUser({ username, password });
      const { access_token } = response.data;
      onLoginSuccess(access_token);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'An unexpected error occurred.';
      setError(errorMessage);
    }
  };

  return (
    <form className="form-container" onSubmit={handleSubmit}>
      <h2>Login</h2>
      {error && <p style={{ color: '#ff6b6b' }}>{error}</p>}
      <div className="form-group">
        <label htmlFor="login-username">Username</label>
        <input 
          id="login-username" 
          type="text" 
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required 
        />
      </div>
      <div className="form-group">
        <label htmlFor="login-password">Password</label>
        <input 
          id="login-password" 
          type="password" 
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required 
        />
      </div>
      <button type="submit" className="form-button">Login</button>
    </form>
  );
};

export default LoginForm;
