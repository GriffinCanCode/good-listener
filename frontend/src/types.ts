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

export type ConnectionStatus = 'connected' | 'disconnected';

