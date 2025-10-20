import React, { useState, useEffect, useMemo, useRef } from 'react';
import { updateUserProfile, getAvailableModels } from '../apiClient';
import './Form.css';
import './UserSettings.css';

const PLAN_MAP = {
    3: "Owner",
    2: "Ultimate",
    1: "Advanced",
    0: "Basic",
};

const UserSettings = ({ user, onProfileUpdate }) => {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    model: '',
    system_prompt: '',
  });

  const [availableModels, setAvailableModels] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const wrapperRef = useRef(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await getAvailableModels();
        // ROBUSTNESS FIX: Ensure response.data is an array before sorting
        if (Array.isArray(response?.data)) {
          const sortedModels = [...response.data].sort((a, b) => {
            if (a.access_level !== b.access_level) return b.access_level - a.access_level;
            return a.model_name.localeCompare(b.model_name);
          });
          setAvailableModels(sortedModels);
        } else {
          setAvailableModels([]); // Always set to an array
        }
      } catch (err) {
        setError("Could not load available AI models.");
        setAvailableModels([]); // Ensure it's always an array on error
      }
    };
    fetchModels();
  }, []);

  useEffect(() => {
    if (user) {
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
        model: user.model || '',
        system_prompt: user.system_prompt || '',
      });
    }
  }, [user]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [wrapperRef]);

  const groupedModels = useMemo(() => {
    // ROBUSTNESS FIX: Ensure availableModels is an array before reducing
    if (!Array.isArray(availableModels)) return {};
    return availableModels.reduce((acc, model) => {
      const planName = PLAN_MAP[model.access_level] || "Other";
      if (!acc[planName]) acc[planName] = [];
      acc[planName].push(model);
      return acc;
    }, {});
  }, [availableModels]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleModelSelect = (modelName) => {
    setFormData(prev => ({ ...prev, model: modelName }));
    setIsDropdownOpen(false);
  };

  const handleSave = async () => {
    setError(null);
    setSuccessMessage(null);
    setIsLoading(true);

    try {
      await updateUserProfile(formData);
      setSuccessMessage('Profile updated successfully!');
      if (onProfileUpdate) {
        onProfileUpdate();
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'An unexpected error occurred.');
    } finally {
      setIsLoading(false);
      setTimeout(() => setSuccessMessage(null), 3000);
    }
  };

  return (
    <div className="settings-container">
      {error && <p className="form-error">{error}</p>}
      {successMessage && <p className="form-success">{successMessage}</p>}

      <div className="settings-card">
        <div className="settings-section">
          <div className="section-header">
            <h4>Personal Information</h4>
            <p className="section-description">Update your profile details</p>
          </div>

          <div className="name-grid">
            <div className="setting-item">
              <label htmlFor="first_name">First Name</label>
              <input id="first_name" name="first_name" type="text" value={formData.first_name} onChange={handleChange} placeholder="Your first name" />
            </div>
            <div className="setting-item">
              <label htmlFor="last_name">Last Name</label>
              <input id="last_name" name="last_name" type="text" value={formData.last_name} onChange={handleChange} placeholder="Your last name" />
            </div>
          </div>

          <div className="setting-item">
            <label htmlFor="email">Email Address</label>
            <input id="email" name="email" type="email" value={formData.email} onChange={handleChange} placeholder="your.email@example.com" />
          </div>
        </div>

        <div className="settings-section">
          <div className="section-header">
            <h4>AI Configuration</h4>
            <p className="section-description">Customize your AI assistant behavior</p>
          </div>

          <div className="setting-item">
            <label htmlFor="model">Preferred Model</label>
            <div className={`custom-select-wrapper ${isDropdownOpen ? 'open' : ''}`} ref={wrapperRef}>
              <div className="custom-select-trigger" onClick={() => setIsDropdownOpen(!isDropdownOpen)}>
                <span>{formData.model || "-- Select a Model --"}</span>
                <div className="custom-select-arrow"></div>
              </div>
              {isDropdownOpen && (
                <ul className="custom-select-options">
                  {Object.entries(groupedModels).map(([groupName, modelsInGroup]) => (
                    <React.Fragment key={groupName}>
                      <li className="custom-option-group">{groupName}</li>
                      {modelsInGroup.map((m) => (
                        <li key={m.model_name} className={`custom-option ${formData.model === m.model_name ? 'selected' : ''}`} onClick={() => handleModelSelect(m.model_name)}>
                          {m.model_name}
                        </li>
                      ))}
                    </React.Fragment>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="setting-item">
            <label htmlFor="system_prompt">System Prompt</label>
            <p className="field-hint">Define how the AI should behave and respond</p>
            <textarea id="system_prompt" name="system_prompt" value={formData.system_prompt} onChange={handleChange} rows={6} placeholder="e.g., You are a helpful and friendly assistant." />
          </div>
        </div>

        <div className="settings-footer">
          <button onClick={handleSave} className="form-button save-button" disabled={isLoading}>
            {isLoading ? <div className="spinner"></div> : 'Save All Settings'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserSettings;
