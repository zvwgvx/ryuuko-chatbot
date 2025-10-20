import { useState, useEffect, useCallback } from 'react';
import { setAuthToken, getUserProfile } from './apiClient';
import Dashboard from './components/Dashboard';
import LandingPage from './components/LandingPage';
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const handleLogout = useCallback(() => {
    localStorage.removeItem('token');
    setUser(null);
    setAuthToken(null);
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
        handleLogout(); // Now safe to call
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
    fetchUserProfile(); // Refetch user profile to update state
  };

  const handleProfileUpdate = () => {
    // Refetch user data to update the UI across the app
    fetchUserProfile();
  };

  if (isLoading) {
    return <div className="loading-fullscreen">Loading...</div>;
  }

  return (
    <>
      {user ? (
        <Dashboard user={user} onLogout={handleLogout} onProfileUpdate={handleProfileUpdate} />
      ) : (
        <LandingPage onLoginSuccess={handleLoginSuccess} />
      )}
    </>
  );
}

export default App;
