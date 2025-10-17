import React, { useState } from 'react';
import Modal from './Modal';
import LoginForm from './LoginForm';
import RegisterForm from './RegisterForm';
import './LandingPage.css';

const LandingPage = ({ onLoginSuccess }) => {
  const [activeModal, setActiveModal] = useState(null);

  return (
    <div className="landing-page">
      <div className="landing-toolbar">
        <button className="toolbar-button" onClick={() => setActiveModal('login')}>Login</button>
        <button className="toolbar-button primary" onClick={() => setActiveModal('register')}>Register</button>
      </div>
      <div className="landing-content">
        <h1>Ryuuko Dashboard</h1>
        <p>Please log in or register to manage your account.</p>
      </div>

      {activeModal && (
        <Modal onClose={() => setActiveModal(null)}>
          {activeModal === 'login' && <LoginForm onLoginSuccess={onLoginSuccess} />}
          {activeModal === 'register' && <RegisterForm onRegisterSuccess={onLoginSuccess} />}
        </Modal>
      )}
    </div>
  );
};

export default LandingPage;
