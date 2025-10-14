import React, { useState } from 'react';
import { generateLinkCode } from '../apiClient';
import './Dashboard.css';

const Dashboard = ({ user, onLogout }) => {
  const [linkCode, setLinkCode] = useState(null);
  const [error, setError] = useState(null);

  const handleGenerateCode = async () => {
    setError(null);
    setLinkCode(null);
    try {
      const response = await generateLinkCode();
      setLinkCode(response.data.link_code);
    } catch (err) {
      setError('Failed to generate code. Please try again.');
    }
  };

  return (
    <div className="dashboard-container">
      <div className="toolbar">
         <button className="toolbar-button" onClick={onLogout}>Logout</button>
      </div>

      <h1>Welcome, {user.username}!</h1>
      <p>This is your central dashboard.</p>

      <div className="user-info">
        <h3>Your Information</h3>
        <p><strong>Email:</strong> {user.email}</p>
        <p><strong>Linked Accounts:</strong></p>
        {user.linked_accounts.length > 0 ? (
          <ul>
            {user.linked_accounts.map(acc => (
              <li key={acc.platform}>{acc.platform}: {acc.platform_display_name}</li>
            ))}
          </ul>
        ) : (
          <p>No accounts linked yet.</p>
        )}
      </div>

      <div className="link-section">
        <h3>Link Your Accounts</h3>
        <p>Generate a code and use it on a supported platform (e.g., Discord) to link your account.</p>
        <button className="form-button" onClick={handleGenerateCode}>Generate Code</button>
        {error && <p className="error-message">{error}</p>}
        {linkCode && (
          <div className="link-code-display">
            <p>Your code is:</p>
            <pre>{linkCode}</pre>
            <p>This code will expire in 5 minutes.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
