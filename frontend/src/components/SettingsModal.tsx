import { Save, X } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';
import { DEFAULT_SETTINGS, type LLMProvider, type Settings } from '../../electron/shared/settings';
import { type UIState, useUIStore } from '../store/useUIStore';

const API_BASE = 'http://127.0.0.1:8000';

const GEMINI_MODELS = [
  { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash (Recommended)' },
  { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
  { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
];

export const SettingsModal: React.FC = () => {
  const isSettingsOpen = useUIStore((state: UIState) => state.isSettingsOpen);
  const setSettingsOpen = useUIStore((state: UIState) => state.setSettingsOpen);
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isSettingsOpen) {
      // Load settings from electron-store
      window.electron?.settings.get().then(setSettings).catch(console.error);
    }
  }, [isSettingsOpen]);

  const handleSave = useCallback(async () => {
    setLoading(true);
    try {
      // Save to electron-store
      await window.electron?.settings.set(settings);

      // Update backend config
      await fetch(`${API_BASE}/api/config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider: settings.llm.provider,
          model: settings.llm.model,
          api_key: settings.llm.apiKey,
          ollama_host: settings.llm.ollamaHost,
        }),
      });

      setSettingsOpen(false);
    } catch (err) {
      console.error('Failed to save settings:', err);
    } finally {
      setLoading(false);
    }
  }, [settings, setSettingsOpen]);

  const updateLLM = (updates: Partial<Settings['llm']>) => {
    setSettings((prev) => ({
      ...prev,
      llm: { ...prev.llm, ...updates },
    }));
  };

  if (!isSettingsOpen) return null;

  return (
    <div className="settings-backdrop" onClick={() => setSettingsOpen(false)}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Settings</h2>
          <button onClick={() => setSettingsOpen(false)} className="icon-btn">
            <X size={20} />
          </button>
        </div>

        <div className="settings-content">
          <div className="settings-section">
            <h3>LLM Configuration</h3>

            <div className="form-group">
              <label>Provider</label>
              <select
                value={settings.llm.provider}
                onChange={(e) => updateLLM({ provider: e.target.value as LLMProvider })}
              >
                <option value="gemini">Google Gemini</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Model Name</label>
              {settings.llm.provider === 'gemini' ? (
                <select
                  value={settings.llm.model}
                  onChange={(e) => updateLLM({ model: e.target.value })}
                >
                  {GEMINI_MODELS.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                  <option value="custom">Custom...</option>
                </select>
              ) : null}

              {(settings.llm.provider !== 'gemini' ||
                !GEMINI_MODELS.some((m) => m.value === settings.llm.model)) && (
                <input
                  type="text"
                  value={settings.llm.model}
                  onChange={(e) => updateLLM({ model: e.target.value })}
                  placeholder={
                    settings.llm.provider === 'gemini' ? 'Enter custom model name...' : 'llama3'
                  }
                  style={{ marginTop: '8px' }}
                />
              )}
            </div>

            {settings.llm.provider === 'gemini' && (
              <div className="form-group">
                <label>API Key</label>
                <input
                  type="password"
                  value={settings.llm.apiKey ?? ''}
                  onChange={(e) => updateLLM({ apiKey: e.target.value })}
                  placeholder="AIza..."
                />
              </div>
            )}

            {settings.llm.provider === 'ollama' && (
              <div className="form-group">
                <label>Ollama Host</label>
                <input
                  type="text"
                  value={settings.llm.ollamaHost ?? ''}
                  onChange={(e) => updateLLM({ ollamaHost: e.target.value })}
                  placeholder="http://localhost:11434"
                />
              </div>
            )}
          </div>
        </div>

        <div className="settings-footer">
          <button onClick={handleSave} disabled={loading} className="save-btn">
            <Save size={16} />
            <span>{loading ? 'Saving...' : 'Save Changes'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
