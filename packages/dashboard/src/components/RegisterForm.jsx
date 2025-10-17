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
  };

  const nextStep = () => {
    if (!formData.firstName || !formData.lastName || !formData.dob) {
      setError('Please fill out all personal information fields.');
      return;
    }
    setError(null);
    setStep(step + 1);
  };

  const prevStep = () => {
    setStep(step - 1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setIsLoading(true);

    try {
      const dataToSend = {
        first_name: formData.firstName,
        last_name: formData.lastName,
        dob: formData.dob,
        username: formData.username,
        email: formData.email,
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
      const errorMessage = err.response?.data?.detail || 'An unexpected error occurred.';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const renderStepIndicator = () => (
    <div className="step-indicator">
      <div className={`step ${step >= 1 ? 'active' : ''}`}>
        <div className="step-number">1</div>
        <div className="step-label">Personal</div>
      </div>
      <div className={`step-connector ${step > 1 ? 'active' : ''}`}></div>
      <div className={`step ${step >= 2 ? 'active' : ''}`}>
        <div className="step-number">2</div>
        <div className="step-label">Account</div>
      </div>
    </div>
  );

  return (
    <form className="form-container" onSubmit={handleSubmit}>
      <h2>Register</h2>
      {renderStepIndicator()}
      {error && <p className="form-error">{error}</p>}

      {step === 1 && (
        <>
          <div className="form-group">
            <input id="firstName" name="firstName" type="text" value={formData.firstName} onChange={handleChange} required placeholder=" " />
            <label htmlFor="firstName">First Name</label>
          </div>
          <div className="form-group">
            <input id="lastName" name="lastName" type="text" value={formData.lastName} onChange={handleChange} required placeholder=" " />
            <label htmlFor="lastName">Last Name</label>
          </div>
          <div className="form-group">
            <input id="dob" name="dob" type="date" value={formData.dob} onChange={handleChange} required placeholder=" " />
            <label htmlFor="dob">Date of Birth</label>
          </div>
          <button type="button" onClick={nextStep} className="form-button">Next</button>
        </>
      )}

      {step === 2 && (
        <>
          <div className="form-group">
            <input id="register-username" name="username" type="text" value={formData.username} onChange={handleChange} required placeholder=" " />
            <label htmlFor="register-username">Username</label>
          </div>
          <div className="form-group">
            <input id="register-email" name="email" type="email" value={formData.email} onChange={handleChange} required placeholder=" " />
            <label htmlFor="register-email">Email</label>
          </div>
          <div className="form-group">
            <input id="register-password" name="password" type="password" value={formData.password} onChange={handleChange} required minLength="8" placeholder=" " />
            <label htmlFor="register-password">Password</label>
          </div>
          <div className="form-group">
            <input id="confirmPassword" name="confirmPassword" type="password" value={formData.confirmPassword} onChange={handleChange} required placeholder=" " />
            <label htmlFor="confirmPassword">Confirm Password</label>
          </div>
          <div className="form-navigation">
            <button type="button" onClick={prevStep} className="form-button secondary">Back</button>
            <button type="submit" className="form-button" disabled={isLoading}>
              {isLoading ? <div className="spinner"></div> : 'Create Account'}
            </button>
          </div>
        </>
      )}
    </form>
  );
};

export default RegisterForm;
