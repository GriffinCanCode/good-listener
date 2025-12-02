export type LLMProvider = 'gemini' | 'ollama';

export interface LLMSettings {
  provider: LLMProvider;
  model: string;
  apiKey?: string; // For Gemini
  ollamaHost?: string; // For Ollama
}

export interface Settings {
  llm: LLMSettings;
}

export const DEFAULT_SETTINGS: Settings = {
  llm: {
    provider: 'gemini',
    model: 'gemini-2.0-flash',
    ollamaHost: 'http://localhost:11434',
  },
};

export const SETTINGS_CHANNELS = {
  GET_SETTINGS: 'settings:get',
  SET_SETTINGS: 'settings:set',
} as const;
