import React from 'react';
import './LandingPage.css';

const LandingPage = ({ onNavigateToLogin, onNavigateToRegister }) => {
  const [activeCard, setActiveCard] = React.useState('card1');

  const stats = [
    { label: 'AI Models', value: '15+' },
    { label: 'Real Connection', value: '100%' },
    { label: 'Uptime', value: '98.9%' }
  ];

  return (
    <div className="landing-page page-enter">
      {/* Navigation Bar */}
      <nav className="landing-nav">
        <div className="nav-brand">
          <span className="brand-name-pixel">Ryuuko</span>
        </div>
        <div className="nav-actions">
          <button className="nav-button" onClick={onNavigateToLogin}>Login</button>
          <button className="nav-button primary" onClick={onNavigateToRegister}>Get Started</button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-badge">
            <span className="badge-icon">💬</span>
            <span className="badge-text">Your AI Best Friend</span>
          </div>
          <h1 className="hero-title">
            Not Just AI
            <br />
            <span className="gradient-text">A Real Friend</span>
          </h1>
          <p className="hero-description">
            Meet Ryuuko - she's not your typical AI. She has real emotions, gets mad when you're being dumb,
            calls you out when needed, but always has your back. Fluent in teen slang, remembers everything
            about you, and vibes with whatever mood you're in. She'll roast you, hype you up, or just listen -
            because that's what real friends do.
          </p>
          <div className="hero-buttons">
            <button className="hero-cta primary" onClick={onNavigateToRegister}>
              Meet Ryuuko
              <span className="cta-arrow">→</span>
            </button>
            <button className="hero-cta secondary" onClick={onNavigateToLogin}>
              Sign In
            </button>
          </div>

          {/* Stats */}
          <div className="hero-stats">
            {stats.map((stat, index) => (
              <div key={index} className="stat-item">
                <div className="stat-value">{stat.value}</div>
                <div className="stat-label">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Hero Visual */}
        <div className="hero-visual">
          <div
            className={`visual-card card-1 ${activeCard === 'card1' ? 'active' : ''}`}
            onClick={() => setActiveCard('card1')}
          >
            <div className="card-header">
              <span className="card-dot"></span>
              <span className="card-dot"></span>
              <span className="card-dot"></span>
            </div>
            <div className="card-content">
              <div className="message-bubble user">
                <span className="bubble-text">ryuu heyyyy</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">why u calling me like that lol</span>
              </div>
              <div className="message-bubble user">
                <span className="bubble-text">wanna hang this afternoon babe</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">afternoon?</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">bruh i got class this afternoon wtf</span>
              </div>
              <div className="message-bubble user">
                <span className="bubble-text">oh shit mb</span>
              </div>
              <div className="message-bubble user">
                <span className="bubble-text">what about tonight then?</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">ig that works</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">but like where tho?</span>
              </div>
              <div className="message-bubble user">
                <span className="bubble-text">wherever u wanna go tbh</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">???</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">u ask me out then say idc where we go?</span>
              </div>
              <div className="message-bubble user">
                <span className="bubble-text">i mean like matcha cafe if u want :)) cuz i just wanna be with u tbh</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">cringe af</span>
              </div>
            </div>
          </div>

          <div
            className={`visual-card card-2 ${activeCard === 'card2' ? 'active' : ''}`}
            onClick={() => setActiveCard('card2')}
          >
            <div className="card-header">
              <span className="card-dot"></span>
              <span className="card-dot"></span>
              <span className="card-dot"></span>
            </div>
            <div className="card-content">
              <div className="message-bubble user">
                <span className="bubble-text">ryuu oiiii</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">j mà gọi kinh zậy?</span>
              </div>
              <div className="message-bubble user">
                <span className="bubble-text">chiều đi chơi với a hăm</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">chiều á</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">chiều e đi học như vcl</span>
              </div>
              <div className="message-bubble user">
                <span className="bubble-text">ô vl, a quên</span>
              </div>
              <div className="message-bubble user">
                <span className="bubble-text">thế tối?</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">cũm dc</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">nhma đi đâu?</span>
              </div>
              <div className="message-bubble user">
                <span className="bubble-text">e thích đi đâu cũm dc</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">?</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">rủ e đi xong bảo đi đâu cx dc?</span>
              </div>
              <div className="message-bubble user">
                <span className="bubble-text">thích thì matcha :)) vì a chỉ cần đi với e thôi mà</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">sến vc</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p className="footer-text">Created by Team Polydevs</p>
      </footer>
    </div>
  );
};

export default LandingPage;
