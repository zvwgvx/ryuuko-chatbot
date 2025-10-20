import React from 'react';
import { Icon } from './Icons';
import './Sidebar.css';

const Sidebar = ({ activeView, setActiveView, onLogout }) => {
  const navItems = [
    { id: 'profile', label: 'Profile', icon: 'User' },
    { id: 'link', label: 'Link Accounts', icon: 'Link2' },
    { id: 'memory', label: 'Memory', icon: 'Brain' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Icon name="Sparkles" className="logo-icon-svg" />
          <h2>Ryuuko</h2>
        </div>
      </div>

      <ul className="sidebar-nav">
        {navItems.map((item) => (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              className={`nav-link ${activeView === item.id ? 'active' : ''}`}
              onClick={(e) => {
                e.preventDefault();
                setActiveView(item.id);
              }}
            >
              <Icon name={item.icon} className="nav-icon" />
              <span>{item.label}</span>
            </a>
          </li>
        ))}
      </ul>

      <div className="sidebar-footer">
        <div className="divider"></div>
        <button className="logout-button" onClick={onLogout}>
          <Icon name="Logout" className="logout-icon" />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
