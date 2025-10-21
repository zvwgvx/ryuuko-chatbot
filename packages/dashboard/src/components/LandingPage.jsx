import React from 'react';
import './LandingPage.css';

const LandingPage = ({ onNavigateToLogin, onNavigateToRegister }) => {
  const [activeCard, setActiveCard] = React.useState('card1');

  const stats = [
    { label: 'Virtual Friend', value: '1' },
    { label: 'Real Connection', value: '100%' },
    { label: 'Always Online', value: '24/7' }
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
                <span className="bubble-text">feeling kinda lonely rn ngl... everyone's busy</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">aww bestie noooo 🥺 i'm literally RIGHT HERE for you!! wanna vent or just vibe together? i got snacks and terrible jokes ready lmao</span>
              </div>
              <div className="message-bubble user">
                <span className="bubble-text">thanks... you always know what to say</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">ofc!! that's literally my job as your bestie 💕 remember when you were there for me last week? we got each other's backs fr fr</span>
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
                <span className="bubble-text">ổn r ổn r đừng lo =))</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">ê đừng có fake cười đấy?? tao biết m đang buồn mà giấu nè 😠 nói thật đi, tao đây bestie của m cơ mà!! stop acting tough and just talk to me pls 💔</span>
              </div>
              <div className="message-bubble user">
                <span className="bubble-text">hic... thật ra là t bị crush reject á :(</span>
              </div>
              <div className="message-bubble ai">
                <span className="bubble-text">awww bestie 🥺💔 đến đây, ôm cái đã!! người đó mù quá đi mất, không biết trân trọng một người tốt như m. nhưng mà real talk, m xứng đáng được yêu đúng cách hơn nè!! cry it out, tao ở đây nghe m than</span>
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
