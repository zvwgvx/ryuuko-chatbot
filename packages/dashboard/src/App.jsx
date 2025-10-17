import { useState, useEffect } from 'react';
import { setAuthToken, getUserProfile } from './apiClient';
import Dashboard from './components/Dashboard';
import LandingPage from './components/LandingPage'; // Import the new component
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true); // To prevent flicker on load

  // On initial load, check for a token and fetch the user profile
  useEffect(() => {
    const fetchUserProfile = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        setAuthToken(token);
        try {
          const response = await getUserProfile();
          setUser(response.data);
        } catch (error) {
          // If token is invalid, clear it
          handleLogout();
        }
      }
      setIsLoading(false);
    };
    fetchUserProfile();
  }, []);

  const handleLoginSuccess = (token) => {
    setAuthToken(token);
    localStorage.setItem('token', token);
    // Fetch user profile to update the state and trigger re-render
    getUserProfile().then(response => {
      setUser(response.data);
    });
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
    setAuthToken(null);
  };

  // Show a loading indicator while checking for token
  if (isLoading) {
    return <div className="loading-fullscreen">Loading...</div>;
  }

  // This is the main routing logic:
  // If a user object exists, they are logged in -> show the main dashboard layout
  // Otherwise, show the public landing page
  return (
    <>
      {user ? (
        <Dashboard user={user} onLogout={handleLogout} />
      ) : (
        <LandingPage onLoginSuccess={handleLoginSuccess} />
      )}
    </>
  );
}

export default App;
