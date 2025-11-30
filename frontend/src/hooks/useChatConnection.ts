import { useEffect, useRef, useCallback } from 'react';
import { useChatStore } from '../store/useChatStore';

const WS_URL = 'ws://127.0.0.1:8000/ws';

export const useChatConnection = () => {
  const ws = useRef<WebSocket | null>(null);
  
  // We use selectors to avoid re-renders if possible, but here we just destructure actions which are stable
  const setStatus = useChatStore((state) => state.setStatus);
  const setStream = useChatStore((state) => state.setStream);
  const appendStreamToContent = useChatStore((state) => state.appendStreamToContent);
  const commitStreamToMessage = useChatStore((state) => state.commitStreamToMessage);
  const addMessageToCurrent = useChatStore((state) => state.addMessageToCurrent);
  const updateCurrentSessionTitle = useChatStore((state) => state.updateCurrentSessionTitle);
  const status = useChatStore((state) => state.status);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    ws.current = new WebSocket(WS_URL);

    ws.current.onopen = () => setStatus('connected');
    ws.current.onclose = () => {
      setStatus('disconnected');
      setTimeout(connect, 3000);
    };

    ws.current.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        switch (data.type) {
          case 'start':
            setStream('');
            break;
          case 'chunk':
            appendStreamToContent(data.content);
            break;
          case 'done':
            commitStreamToMessage();
            break;
          case 'insight':
            addMessageToCurrent({ role: 'assistant', content: data.content });
            break;
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
  }, [setStatus, setStream, appendStreamToContent, commitStreamToMessage, addMessageToCurrent]);

  useEffect(() => {
    connect();
    return () => {
      ws.current?.close();
    };
  }, [connect]);

  const sendMessage = (content: string) => {
    if (!content.trim() || status !== 'connected') return;

    // Get current state to check if first message
    const state = useChatStore.getState();
    const currentSession = state.sessions.find(s => s.id === state.currentSessionId);
    const isFirstMessage = currentSession && currentSession.messages.length === 0;

    // Optimistic update
    addMessageToCurrent({ role: 'user', content });

    // Send to WS
    ws.current?.send(JSON.stringify({ type: 'chat', message: content }));

    // Update title if first message
    if (isFirstMessage) {
      const title = content.slice(0, 30) + (content.length > 30 ? '...' : '');
      updateCurrentSessionTitle(title);
    }
  };

  return { sendMessage };
};

