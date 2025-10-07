import React, { useState, useEffect } from 'react';
import axios from 'axios';

function LinkAccountPage() {
  const [code, setCode] = useState(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Check for auth token on component mount
  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setError('You must be logged in to link an account.');
    } else {
       axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
  }, []);

  const handleGenerateCode = async () => {
    setIsLoading(true);
    setError('');
    setCode(null);
    try {
      const response = await axios.post('/api/users/me/generate-link-code');
      setCode(response.data.code);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate a link code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <h2>Link Your Discord Account</h2>
      <p>
        To connect your Discord account, generate a link code below and then use the `/link` command in any server where Ryuuko is present.
      </p>

      <button onClick={handleGenerateCode} disabled={isLoading}>
        {isLoading ? 'Generating...' : 'Generate Link Code'}
      </button>

      {error && <p style={{ color: 'red', marginTop: '1rem' }}>{error}</p>}

      {code && (
        <div style={{ marginTop: '2rem', border: '1px solid #ccc', padding: '1rem' }}>
          <h3>Your Link Code:</h3>
          <p style={{ fontSize: '2rem', fontWeight: 'bold', letterSpacing: '0.2em' }}>{code}</p>
          <p>This code will expire in 5 minutes.</p>
          <hr />
          <h4>Next Steps:</h4>
          <ol>
            <li>Open Discord.</li>
            <li>Go to a server with the Ryuuko bot.</li>
            <li>Type the following command: <code>.link {code}</code></li>
          </ol>
        </div>
      )}
    </div>
  );
}

export default LinkAccountPage;