import React, { useState } from 'react';
import { registerUser } from '../apiClient';
import './Form.css';

const RegisterForm = ({ onRegisterSuccess }) => {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    dob: '',
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({ ...prevState, [name]: value }));
    // Clear error when user starts typing
    if (error) setError(null);
  };

  const validateStep1 = () => {
    if (!formData.firstName.trim()) {
      setError('First name is required.');
      return false;
    }
    if (!formData.lastName.trim()) {
      setError('Last name is required.');
      return false;
    }
    if (!formData.dob) {
      setError('Date of birth is required.');
      return false;
    }

    // Validate age (must be at least 13 years old)
    const today = new Date();
    const birthDate = new Date(formData.dob);
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();

    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }

    if (age < 13) {
      setError('You must be at least 13 years old to register.');
      return false;
    }

    return true;
  };

  const validateStep2 = () => {
    if (!formData.username.trim()) {
      setError('Username is required.');
      return false;
    }
    if (formData.username.length < 3) {
      setError('Username must be at least 3 characters long.');
      return false;
    }
    if (!formData.email.trim()) {
      setError('Email is required.');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setError('Please enter a valid email address.');
      return false;
    }
    if (!formData.password) {
      setError('Password is required.');
      return false;
    }
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return false;
    }
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      return false;
    }
    return true;
  };

  const nextStep = () => {
    if (!validateStep1()) {
      return;
    }
    setError(null);
    setStep(2);
  };

  const prevStep = () => {
    setError(null);
    setStep(1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!validateStep2()) {
      return;
    }

    setIsLoading(true);

    try {
      const dataToSend = {
        first_name: formData.firstName.trim(),
        last_name: formData.lastName.trim(),
        dob: formData.dob,
        username: formData.username.trim(),
        email: formData.email.trim().toLowerCase(),
        password: formData.password,
      };

      const response = await registerUser(dataToSend);
      const token = response.data.token.access_token;

      if (token && onRegisterSuccess) {
        onRegisterSuccess(token);
      } else {
        setError("Registration successful, but auto-login failed. Please log in manually.");
      }

    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'An unexpected error occurred. Please try again.';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const renderStepIndicator = () => (
    <div className="step-indicator">
      <div className={`step ${step >= 1 ? 'active' : ''}`}>
        <div className="step-number">1</div>
        <div className="step-label">Personal Info</div>
      </div>
      <div className={`step-connector ${step > 1 ? 'active' : ''}`}></div>
      <div className={`step ${step >= 2 ? 'active' : ''}`}>
        <div className="step-number">2</div>
        <div className="step-label">Account Setup</div>
      </div>
    </div>
  );

  return (
    <form className="form-container" onSubmit={handleSubmit}>
      <h2>Create Account</h2>

      {renderStepIndicator()}

      {error && <div className="form-error">{error}</div>}

      {step === 1 && (
        <>
          <div className="form-group">
            <input
              id="firstName"
              name="firstName"
              type="text"
              value={formData.firstName}
              onChange={handleChange}
              required
              placeholder=" "
              autoComplete="given-name"
            />
            <label htmlFor="firstName">First Name</label>
          </div>

          <div className="form-group">
            <input
              id="lastName"
              name="lastName"
              type="text"
              value={formData.lastName}
              onChange={handleChange}
              required
              placeholder=" "
              autoComplete="family-name"
            />
            <label htmlFor="lastName">Last Name</label>
          </div>

          <div className="form-group">
            <input
              id="dob"
              name="dob"
              type="date"
              value={formData.dob}
              onChange={handleChange}
              required
              placeholder=" "
              max={new Date().toISOString().split('T')[0]}
            />
            <label htmlFor="dob">Date of Birth</label>
          </div>

          <button type="button" onClick={nextStep} className="form-button">
            Continue to Account Setup
          </button>
        </>
      )}

      {step === 2 && (
        <>
          <div className="form-group">
            <input
              id="register-username"
              name="username"
              type="text"
              value={formData.username}
              onChange={handleChange}
              required
              placeholder=" "
              autoComplete="username"
              minLength="3"
            />
            <label htmlFor="register-username">Username</label>
          </div>

          <div className="form-group">
            <input
              id="register-email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              required
              placeholder=" "
              autoComplete="email"
            />
            <label htmlFor="register-email">Email Address</label>
          </div>

          <div className="form-group">
            <input
              id="register-password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              required
              minLength="8"
              placeholder=" "
              autoComplete="new-password"
            />
            <label htmlFor="register-password">Password</label>
          </div>

          <div className="form-group">
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
              placeholder=" "
              autoComplete="new-password"
            />
            <label htmlFor="confirmPassword">Confirm Password</label>
          </div>

          <div className="form-navigation">
            <button type="button" onClick={prevStep} className="form-button secondary">
              Back
            </button>
            <button type="submit" className="form-button" disabled={isLoading}>
              {isLoading ? (
                <>
                  <div className="spinner"></div>
                  <span>Creating...</span>
                </>
              ) : (
                'Create Account'
              )}
            </button>
          </div>
        </>
      )}
    </form>
  );
};

export default RegisterForm;