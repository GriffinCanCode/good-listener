export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface Session {
  id: string;
  title: string;
  date: string;
  messages: Message[];
}

export interface Transcript {
  id: string;
  text: string;
  source: 'user' | 'system';
  speaker: string;
  timestamp: number;
}

export interface AutoAnswer {
  id: string;
  question: string;
  content: string;
  isStreaming: boolean;
  timestamp: number;
}

export interface VADState {
  probability: number;
  isSpeech: boolean;
  source: 'user' | 'system';
  timestamp: number;
}

export type ConnectionStatus = 'connected' | 'disconnected';
