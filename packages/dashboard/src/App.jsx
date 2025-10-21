import { useState, useEffect, useCallback } from 'react';
import { setAuthToken, getUserProfile } from './apiClient';
import Dashboard from './components/Dashboard';
import LandingPage from './components/LandingPage';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState('landing'); // 'landing', 'login', 'register'

  const handleLogout = useCallback(() => {
    localStorage.removeItem('token');
    setUser(null);
    setAuthToken(null);
    setCurrentPage('landing');
  }, []);

  const fetchUserProfile = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (token) {
      setAuthToken(token);
      try {
        const response = await getUserProfile();
        setUser(response.data);
      } catch (error) {
        console.error("Session expired or token is invalid.", error);
        handleLogout();
      }
    }
    setIsLoading(false);
  }, [handleLogout]);

  useEffect(() => {
    fetchUserProfile();
  }, [fetchUserProfile]);

  const handleLoginSuccess = (token) => {
    localStorage.setItem('token', token);
    setAuthToken(token);
    fetchUserProfile();
  };

  const handleProfileUpdate = () => {
    fetchUserProfile();
  };

  if (isLoading) {
    return <div className="loading-fullscreen">Loading...</div>;
  }

  // If user is logged in, show dashboard
  if (user) {
    return <Dashboard user={user} onLogout={handleLogout} onProfileUpdate={handleProfileUpdate} />;
  }

  // If not logged in, show appropriate page
  switch (currentPage) {
    case 'login':
      return (
        <LoginPage
          onLoginSuccess={handleLoginSuccess}
          onNavigateToRegister={() => setCurrentPage('register')}
          onNavigateToHome={() => setCurrentPage('landing')}
        />
      );
    case 'register':
      return (
        <RegisterPage
          onRegisterSuccess={handleLoginSuccess}
          onNavigateToLogin={() => setCurrentPage('login')}
          onNavigateToHome={() => setCurrentPage('landing')}
        />
      );
    default:
      return (
        <LandingPage
          onNavigateToLogin={() => setCurrentPage('login')}
          onNavigateToRegister={() => setCurrentPage('register')}
        />
      );
  }
}

export default App;
