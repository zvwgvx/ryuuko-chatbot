import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000', // Your API server's address
});

// Function to set the auth token for all subsequent requests
export const setAuthToken = (token) => {
  if (token) {
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete apiClient.defaults.headers.common['Authorization'];
  }
};

// --- API Functions ---

export const registerUser = (userData) => {
  return apiClient.post('/api/auth/register', userData);
};

export const loginUser = (credentials) => {
  const formData = new URLSearchParams();
  formData.append('username', credentials.username);
  formData.append('password', credentials.password);

  return apiClient.post('/api/auth/token', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
};

export const getUserProfile = () => {
  return apiClient.get('/api/users/me');
};

export const generateLinkCode = () => {
  return apiClient.post('/api/link/generate-code');
};

// CORRECTED: Replaced old config update with the new unified profile update function
export const updateUserProfile = (profileData) => {
  return apiClient.put('/api/users/me', profileData);
};

export const getAvailableModels = () => {
  return apiClient.get('/api/models');
};

export const getUserMemory = () => {
  return apiClient.get('/api/memory/dashboard');
};

export const clearUserMemory = () => {
  return apiClient.delete('/api/memory/dashboard');
};

export default apiClient;
