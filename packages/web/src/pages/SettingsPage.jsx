import React, { useState, useEffect } from 'react';
import axios from 'axios';

function SettingsPage() {
  const [model, setModel] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const fetchConfig = async () => {
      const token = localStorage.getItem('accessToken');
      if (!token) {
        setError('You must be logged in to view settings.');
        setIsLoading(false);
        return;
      }
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;

      try {
        const response = await axios.get('/api/users/me/config');
        setModel(response.data.model);
        setSystemPrompt(response.data.system_prompt);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to fetch settings.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchConfig();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const response = await axios.put('/api/users/me/config', {
        model,
        system_prompt: systemPrompt,
      });
      setSuccess('Settings updated successfully!');
      setModel(response.data.model);
      setSystemPrompt(response.data.system_prompt);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update settings.');
    }
  };

  if (isLoading) {
    return <p>Loading settings...</p>;
  }

  if (error && !model) { // Show only critical errors if the form can't load
      return <p style={{ color: 'red' }}>{error}</p>
  }

  return (
    <div>
      <h2>Your Settings</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="model">AI Model:</label>
          <input
            id="model"
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            required
            style={{ width: '100%', marginTop: '0.5rem' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="systemPrompt">System Prompt:</label>
          <textarea
            id="systemPrompt"
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            rows="5"
            required
            style={{ width: '100%', marginTop: '0.5rem' }}
          />
        </div>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        {success && <p style={{ color: 'green' }}>{success}</p>}
        <button type="submit">Save Settings</button>
      </form>
    </div>
  );
}

export default SettingsPage;