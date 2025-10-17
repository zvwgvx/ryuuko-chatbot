import React, { useState } from 'react';
import { generateLinkCode } from '../apiClient';
import Sidebar from './Sidebar';
import UserSettings from './UserSettings';
import './Dashboard.css';
import './Form.css';

const Dashboard = ({ user, onLogout }) => {
  const [activeView, setActiveView] = useState('profile'); // 'profile', 'link', or 'settings'

  const renderContent = () => {
    switch (activeView) {
      case 'link':
        return <LinkAccountView />;
      case 'settings':
        return <UserSettings user={user} />;
      case 'profile':
      default:
        return <ProfileView user={user} />;
    }
  };

  return (
    <div className="dashboard-layout">
      <Sidebar activeView={activeView} setActiveView={setActiveView} onLogout={onLogout} />
      <main className="dashboard-content">
        {renderContent()}
      </main>
    </div>
  );
};

// --- Sub-components for each view ---

const ProfileView = ({ user }) => {
  const PLAN_MAP = { 0: "Basic", 1: "Advanced", 2: "Ultimate", 3: "Owner" };
  const planName = PLAN_MAP[user.access_level] || "Unknown";

  return (
    <>
      <div className="content-header">
        <h1>Profile</h1>
        <p>Your personal and account information.</p>
      </div>
      <div className="dashboard-card">
        <h3>Your Information</h3>
        <div className="info-grid">
          <p><strong>Username:</strong> {user.username}</p>
          <p><strong>Email:</strong> {user.email}</p>
          <p><strong>Plan:</strong> {planName}</p>
          <p><strong>Credits:</strong> {user.credit.toLocaleString()}</p>
        </div>
      </div>
    </>
  );
};

const LinkAccountView = () => {
  const [linkCode, setLinkCode] = useState(null);
  const [error, setError] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerateCode = async () => {
    setError(null);
    setLinkCode(null);
    setIsGenerating(true);
    try {
      const response = await generateLinkCode();
      setLinkCode(response.data.link_code);
    } catch (err) {
      setError('Failed to generate code. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <>
      <div className="content-header">
        <h1>Link Accounts</h1>
        <p>Connect your account to other platforms.</p>
      </div>
      <div className="dashboard-card">
        <h3>Generate a Link Code</h3>
        <p className="card-subtitle">Use this code on a supported platform (e.g., Discord) to link your account.</p>
        <button className="form-button" onClick={handleGenerateCode} disabled={isGenerating} style={{ maxWidth: '200px' }}>
          {isGenerating ? <div className="spinner"></div> : 'Generate Code'}
        </button>
        {error && <p className="form-error" style={{ marginTop: '15px' }}>{error}</p>}
        {linkCode && (
          <div className="link-code-display">
            <p>Your temporary code is:</p>
            <pre>{linkCode}</pre>
            <p>This code will expire in 5 minutes.</p>
          </div>
        )}
      </div>
    </>
  );
};

export default Dashboard;
