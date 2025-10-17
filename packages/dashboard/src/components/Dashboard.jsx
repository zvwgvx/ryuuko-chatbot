import React, { useState, useEffect } from 'react';
import { generateLinkCode, getUserMemory, clearUserMemory } from '../apiClient';
import Sidebar from './Sidebar';
import UserSettings from './UserSettings';
import './Dashboard.css';
import './Form.css';

const Dashboard = ({ user, onLogout }) => {
  const [activeView, setActiveView] = useState('profile'); // 'profile', 'link', 'memory', or 'settings'

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

  const PLATFORM_LOGOS = {
    discord: "https://www.svgrepo.com/show/353655/discord-icon.svg",
    facebook: "https://logotyp.us/files/facebook.svg",
    telegram: "https://logotyp.us/files/telegram.svg",
    zalo: "https://logotyp.us/files/zalo.svg",
  };

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
                  <img src={PLATFORM_LOGOS[acc.platform.toLowerCase()] || ''} alt={`${acc.platform} logo`} className="platform-logo" />
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
            )
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

// A self-contained, crash-proof component for rendering message content.
const MessageContent = ({ content }) => {
  try {
    if (typeof content === 'string') return <p>{content}</p>;
    if (Array.isArray(content)) {
      const elements = content.map((part, index) => {
        if (!part || typeof part !== 'object') return null;
        switch (part.type) {
          case 'text': return <p key={index}>{typeof part.text === 'string' ? part.text : ''}</p>;
          case 'image_url': return <p key={index} className="placeholder-content">[Image]</p>;
          default: return null;
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
    setIsLoading(true); setError(null);
    try {
      const response = await getUserMemory();
      setMemory(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      setError("Failed to load conversation memory.");
      setMemory([]);
    } finally { setIsLoading(false); }
  };

  useEffect(() => { fetchMemory(); }, []);

  const handleClearMemory = async () => {
    if (window.confirm("Are you sure you want to permanently delete your entire conversation history?")) {
      try {
        await clearUserMemory();
        fetchMemory();
      } catch (err) { setError("Failed to clear memory. Please try again."); }
    }
  };

  return (
    <>
      <div className="content-header">
        <h1>Conversation Memory</h1>
        <p>Review and manage your conversation history.</p>
      </div>
      <div className="dashboard-card">
        <div className="memory-toolbar"><h3>History</h3><button className="form-button danger" onClick={handleClearMemory} disabled={!memory || memory.length === 0}>Clear Memory</button></div>
        <div className="memory-log-container">
          {isLoading ? <p>Loading memory...</p> : error ? <p className="form-error">{error}</p> : memory && memory.length > 0 ? (
            memory.map((msg, index) => {
              if (!msg || typeof msg.role !== 'string') return null;
              const roleName = msg.role === 'user' ? 'You' : 'Ryuuko';
              return (
                <div key={index} className={`memory-message ${msg.role}`}>
                  <span className="message-role">{roleName}</span>
                  <MessageContent content={msg.content} />
                </div>
              );
            })
          ) : <p>Your conversation memory is empty.</p>}
        </div>
      </div>
    </>
  );
};

export default Dashboard;
