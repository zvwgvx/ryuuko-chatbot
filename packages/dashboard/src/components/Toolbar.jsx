import React from 'react';
import './Toolbar.css';

const Toolbar = ({ onRegisterClick, onLoginClick }) => {
  return (
    <div className="toolbar">
      <div className="toolbar-actions">
        <button className="toolbar-button" onClick={onRegisterClick}>Register</button>
        <button className="toolbar-button login" onClick={onLoginClick}>Login</button>
      </div>
    </div>
  );
};

export default Toolbar;
