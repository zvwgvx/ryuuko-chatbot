import React, { useState } from 'react';
import { registerUser } from '../apiClient';
import './Form.css';

const RegisterForm = ({ onRegisterSuccess }) => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await registerUser({ username, email, password });
      setSuccessMessage(response.data.message + ". You can now log in.");
      // Optional: clear form or call a function to switch to login modal
      // onRegisterSuccess(); 
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'An unexpected error occurred.';
      setError(errorMessage);
    }
  };

  return (
    <form className="form-container" onSubmit={handleSubmit}>
      <h2>Register</h2>
      {error && <p style={{ color: '#ff6b6b' }}>{error}</p>}
      {successMessage && <p style={{ color: '#6bff95' }}>{successMessage}</p>}
      <div className="form-group">
        <label htmlFor="register-username">Username</label>
        <input 
          id="register-username" 
          type="text" 
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required 
        />
      </div>
      <div className="form-group">
        <label htmlFor="register-email">Email</label>
        <input 
          id="register-email" 
          type="email" 
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required 
        />
      </div>
      <div className="form-group">
        <label htmlFor="register-password">Password</label>
        <input 
          id="register-password" 
          type="password" 
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required 
        />
      </div>
      <button type="submit" className="form-button">Create Account</button>
    </form>
  );
};

export default RegisterForm;
