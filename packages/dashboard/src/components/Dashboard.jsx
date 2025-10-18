import React, { useState, useEffect } from 'react';
import { generateLinkCode, getUserMemory, clearUserMemory } from '../apiClient';
import Sidebar from './Sidebar';
import UserSettings from './UserSettings';
import './Dashboard.css';
import './Form.css';

// --- Self-contained, reliable SVG Icon Component ---
const PlatformLogo = ({ platform, ...props }) => {
  const logos = {
    discord: (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 127.14 96.36" {...props}>
            <path fill="#5865F2" d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21h0A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1A105.25,105.25,0,0,0,126.6,80.22h0C129.24,52.84,122.09,29.11,107.7,8.07ZM42.45,65.69C36.18,65.69,31,60,31,53s5-12.74,11.43-12.74S54,46,53.89,53,48.84,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5-12.74,11.44-12.74S96.23,46,96.12,53,91.08,65.69,84.69,65.69Z"/>
        </svg>
    ),
    telegram: (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" {...props}>
            <circle cx="24" cy="24" r="24" fill="#29B6F6"/>
            <path fill="#FFFFFF" d="M33.95,15l-3.746,19.126c0,0-0.161,0.874-1.245,0.874c-0.576,0-0.873-0.274-0.873-0.274l-8.114-6.733 l-3.97-2.001l-5.095-1.355c0,0-0.907-0.262-0.907-1.012c0-0.625,0.933-0.923,0.933-0.923l21.316-8.468 c-0.001-0.001,0.651-0.235,1.126-0.234C33.667,14,34,14.125,34,14.5C34,14.75,33.95,15,33.95,15z"/>
            <path fill="#B0BEC5" d="M23,30.505l-3.426,3.374c0,0-0.149,0.115-0.348,0.12c-0.069,0.002-0.143-0.009-0.219-0.043 l0.964-5.965L23,30.505z"/>
            <path fill="#CFD8DC" d="M29.897,18.196c-0.169-0.22-0.481-0.26-0.701-0.093L16,26c0,0,2.106,5.892,2.427,6.912 c0.322,1.021,0.58,1.045,0.58,1.045l0.964-5.965l9.832-9.096C30.023,18.729,30.064,18.416,29.897,18.196z"/>
        </svg>
    ),
  };
  return logos[platform] || null;
};

const Dashboard = ({ user, onLogout }) => {
  const [activeView, setActiveView] = useState('profile');

  const renderContent = () => {
    switch (activeView) {
      case 'link':
        return <LinkAccountView user={user} />;
      case 'memory':
        return <MemoryView />;
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

const LinkAccountView = ({ user }) => {
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
      <div className="linked-accounts-grid">
        {user && user.linked_accounts && user.linked_accounts.length > 0 ? (
          user.linked_accounts.map((acc) => {
            const linkDate = acc.created_at || acc.updated_at;
            const dateLabel = acc.created_at ? "Linked on" : "Last updated";
            return (
              <div key={acc.platform} className="linked-account-card">
                <div className="card-header">
                  <PlatformLogo platform={acc.platform.toLowerCase()} className="platform-logo" />
                  <span className="platform-title">{acc.platform}</span>
                </div>
                <div className="card-body">
                  <img src={acc.platform_avatar_url || 'https://via.placeholder.com/80'} alt="User avatar" className="user-avatar"/>
                  <div className="account-details">
                    <p className="account-name">{acc.platform_display_name}</p>
                    <p className="account-id">ID: {acc.platform_user_id}</p>
                  </div>
                </div>
                <div className="card-footer">
                  <p className="link-date">{dateLabel}: {new Date(linkDate).toLocaleDateString()}</p>
                </div>
              </div>
            );
          })
        ) : (
          <div className="dashboard-card full-width">
             <p className="card-subtitle">You have not linked any accounts yet. Generate a code below to get started.</p>
          </div>
        )}
      </div>
      <div className="dashboard-card">
        <h3>Generate a New Link Code</h3>
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

const MessageContent = ({ content }) => {
  try {
    if (typeof content === 'string') {
      return <p>{content}</p>;
    }
    if (Array.isArray(content)) {
      const elements = content.map((part, index) => {
        if (!part || typeof part !== 'object') return null;
        switch (part.type) {
          case 'text':
            return <p key={index}>{typeof part.text === 'string' ? part.text : ''}</p>;
          case 'image_url':
            return <p key={index} className="placeholder-content">[Image]</p>;
          default:
            return null;
        }
      });
      const validElements = elements.filter(Boolean);
      return validElements.length > 0 ? validElements : <p className="placeholder-content">[Empty message]</p>;
    }
    return <p className="placeholder-content">[Unsupported message format]</p>;
  } catch (error) {
    console.error("Ryuuko-Helper: A message could not be rendered. Raw content:", content, "Error:", error);
    return <p className="placeholder-content error">[Error displaying this message]</p>;
  }
};

const MemoryView = () => {
  const [memory, setMemory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMemory = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getUserMemory();
      setMemory(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      setError("Failed to load conversation memory.");
      setMemory([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMemory();
  }, []);

  const handleClearMemory = async () => {
    if (window.confirm("Are you sure you want to permanently delete your entire conversation history?")) {
      try {
        await clearUserMemory();
        fetchMemory();
      } catch (err) {
        setError("Failed to clear memory. Please try again.");
      }
    }
  };

  return (
    <>
      <div className="content-header">
        <h1>Conversation Memory</h1>
        <p>Review and manage your conversation history.</p>
      </div>
      <div className="dashboard-card">
        <div className="memory-toolbar">
            <h3>History</h3>
            <button className="form-button danger" onClick={handleClearMemory} disabled={!memory || memory.length === 0}>
                Clear Memory
            </button>
        </div>
        <div className="memory-log-container">
          {isLoading ? (
            <p>Loading memory...</p>
          ) : error ? (
            <p className="form-error">{error}</p>
          ) : memory && memory.length > 0 ? (
            memory.map((msg, index) => {
              if (!msg || typeof msg.role !== 'string') {
                return null;
              }
              return (
                <div key={index} className={`memory-message ${msg.role}`}>
                  <MessageContent content={msg.content} />
                </div>
              );
            })
          ) : (
            <p>Your conversation memory is empty.</p>
          )}
        </div>
      </div>
    </>
  );
};

export default Dashboard;