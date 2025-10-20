import React, { useState } from 'react';
import Sidebar from './Sidebar';
import UserSettings from './UserSettings';
import UserCard from './UserCard';
import LinkAccount from './LinkAccount';
import Memory from './Memory';
import { UserIcon, LinkIcon, BrainIcon } from './Icons';

import './Dashboard.css';
import './Form.css';
import './UserSettings.css';

const Dashboard = ({ user, onLogout, onProfileUpdate }) => {
  const [activeView, setActiveView] = useState('profile');

  const renderContent = () => {
    switch (activeView) {
      case 'link':
        return (
          <>
            <div className="content-header">
              <div className="header-title-wrapper">
                <LinkIcon className="header-icon" />
                <div>
                  <h1>Link Accounts</h1>
                  <p>Connect your Discord and Telegram accounts to your dashboard.</p>
                </div>
              </div>
            </div>
            <LinkAccount user={user} />
          </>
        );
      case 'memory':
        return (
          <>
            <div className="content-header">
              <div className="header-title-wrapper">
                <BrainIcon className="header-icon" />
                <div>
                  <h1>Conversation Memory</h1>
                  <p>View and manage your AI conversation history.</p>
                </div>
              </div>
            </div>
            <Memory user={user} />
          </>
        );
      case 'profile':
      case 'settings':
      default:
        return (
          <>
            <div className="content-header">
              <div className="header-title-wrapper">
                <UserIcon className="header-icon" />
                <div>
                  <h1>Profile & Settings</h1>
                  <p>Manage your personal information and AI preferences.</p>
                </div>
              </div>
            </div>
            <div className="profile-grid">
              <div className="profile-settings">
                <UserSettings user={user} onProfileUpdate={onProfileUpdate} />
              </div>
              <div className="profile-card">
                <UserCard user={user} />
              </div>
            </div>
          </>
        );
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

export default Dashboard;
