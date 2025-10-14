import { useState, useEffect } from 'react';
import { setAuthToken, getUserProfile } from './apiClient';
import Toolbar from './components/Toolbar';
import Modal from './components/Modal';
import LoginForm from './components/LoginForm';
import RegisterForm from './components/RegisterForm';
import Dashboard from './components/Dashboard';
import './App.css';

function App() {
  const [activeModal, setActiveModal] = useState(null); // null, 'login', or 'register'
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);

  useEffect(() => {
    const fetchUserProfile = async () => {
      if (token) {
        setAuthToken(token);
        try {
          const response = await getUserProfile();
          setUser(response.data);
        } catch (error) {
          // Token is invalid or expired
          handleLogout();
        }
      } else {
        setUser(null);
      }
    };

    fetchUserProfile();
  }, [token]);

  const handleLoginSuccess = (newToken) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setActiveModal(null); // Close login modal
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setAuthToken(null); // Clear token from apiClient headers
  };

  const handleCloseModal = () => {
    setActiveModal(null);
  };

  // If we have a user object, they are logged in.
  if (user) {
    return <Dashboard user={user} onLogout={handleLogout} />;
  }

  // Otherwise, show the public view with login/register options.
  return (
    <>
      <Toolbar 
        onRegisterClick={() => setActiveModal('register')}
        onLoginClick={() => setActiveModal('login')}
      />
      
      <h1>Ryuuko Dashboard</h1>
      <p>Please log in or register to manage your account.</p>

      {activeModal && (
        <Modal onClose={handleCloseModal}>
          {activeModal === 'login' && <LoginForm onLoginSuccess={handleLoginSuccess} />}
          {activeModal === 'register' && <RegisterForm />}
        </Modal>
      )}
    </>
  );
}

export default App;
