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
  timestamp: number;
}

export type ConnectionStatus = 'connected' | 'disconnected';
