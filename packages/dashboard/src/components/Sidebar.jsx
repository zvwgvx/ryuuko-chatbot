import React from 'react';
import './Sidebar.css';

const Sidebar = ({ activeView, setActiveView, onLogout }) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Ryuuko</h2>
      </div>
      <ul className="sidebar-nav">
        <li>
          <a 
            href="#profile"
            className={activeView === 'profile' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); setActiveView('profile'); }}
          >
            {/* You can add icons here later */}
            <span>Profile</span>
          </a>
        </li>
        <li>
          <a 
            href="#link"
            className={activeView === 'link' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); setActiveView('link'); }}
          >
            <span>Link Accounts</span>
          </a>
        </li>
        {/* NEW: Memory Link */}
        <li>
          <a 
            href="#memory"
            className={activeView === 'memory' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); setActiveView('memory'); }}
          >
            <span>Memory</span>
          </a>
        </li>
        <li>
          <a 
            href="#settings"
            className={activeView === 'settings' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); setActiveView('settings'); }}
          >
            <span>Settings</span>
          </a>
        </li>
      </ul>
      <button className="logout-button" onClick={onLogout}>
        <span>Logout</span>
      </button>
    </aside>
  );
};

export default Sidebar;
