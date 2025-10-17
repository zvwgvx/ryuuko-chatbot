import React, { useState, useEffect, useMemo, useRef } from 'react';
import { updateUserConfig, getAvailableModels } from '../apiClient';
import './Form.css';
import './UserSettings.css';

const PLAN_MAP = {
    3: "Owner",
    2: "Ultimate",
    1: "Advanced",
    0: "Basic",
};

const UserSettings = ({ user }) => {
  const [model, setModel] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const wrapperRef = useRef(null); // Ref for the dropdown wrapper

  // Fetch available models on mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await getAvailableModels();
        const sortedModels = response.data.sort((a, b) => {
          if (a.access_level !== b.access_level) return b.access_level - a.access_level;
          return a.model_name.localeCompare(b.model_name);
        });
        setAvailableModels(sortedModels);
      } catch (err) { setError("Could not load available models."); }
    };
    fetchModels();
  }, []);

  // Populate form with user data
  useEffect(() => {
    if (user) {
      setModel(user.model || '');
      setSystemPrompt(user.system_prompt || '');
    }
  }, [user]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [wrapperRef]);

  const groupedModels = useMemo(() => {
    return availableModels.reduce((acc, model) => {
      const planName = PLAN_MAP[model.access_level] || "Other";
      if (!acc[planName]) acc[planName] = [];
      acc[planName].push(model);
      return acc;
    }, {});
  }, [availableModels]);

  const handleSave = async () => {
    setError(null);
    setSuccessMessage(null);
    setIsLoading(true);
    try {
      await updateUserConfig({ model, system_prompt: systemPrompt });
      setSuccessMessage('Settings saved successfully!');
    } catch (err) {
      setError(err.response?.data?.detail || 'An unexpected error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOptionClick = (modelName) => {
    setModel(modelName);
    setIsDropdownOpen(false);
  }

  return (
    <div className="settings-container form-container">
      <h3>Model & Prompt Settings</h3>
      {error && <p className="form-error">{error}</p>}
      {successMessage && <p className="form-success">{successMessage}</p>}

      <div className="form-group-static">
        <label htmlFor="model-setting">AI Model Preference</label>
        <div className={`custom-select-wrapper ${isDropdownOpen ? 'open' : ''}`} ref={wrapperRef}>
          <div className="custom-select-trigger" onClick={() => setIsDropdownOpen(!isDropdownOpen)}>
            <span>{model || "-- Select a Model --"}</span>
            <div className="custom-select-arrow"></div>
          </div>
          {isDropdownOpen && (
            <ul className="custom-select-options">
              {Object.entries(groupedModels).map(([groupName, modelsInGroup]) => (
                <React.Fragment key={groupName}>
                  <li className="custom-option-group">{groupName}</li>
                  {modelsInGroup.map((m) => (
                    <li 
                      key={m.model_name} 
                      className={`custom-option ${model === m.model_name ? 'selected' : ''}`}
                      onClick={() => handleOptionClick(m.model_name)}
                    >
                      {m.model_name}
                    </li>
                  ))}
                </React.Fragment>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="form-group-static">
        <label htmlFor="prompt-setting">System Prompt</label>
        <textarea 
          id="prompt-setting"
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          rows={5}
          placeholder="e.g., You are a helpful and friendly assistant."
        />
      </div>

      <button onClick={handleSave} className="form-button" disabled={isLoading}>
        {isLoading ? <div className="spinner"></div> : 'Save Settings'}
      </button>
    </div>
  );
};

export default UserSettings;
