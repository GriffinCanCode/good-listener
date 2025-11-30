import { useCallback, useEffect, useRef } from 'react';
import { useChatStore } from '../store/useChatStore';
import { startTrace } from '../trace';

const WS_URL = 'ws://127.0.0.1:8000/ws';
const BACKOFF_BASE_MS = 1000;
const BACKOFF_MAX_MS = 30000;
const JITTER_FACTOR = 0.5;
const SESSION_TITLE_MAX_LENGTH = 30;

// WebSocket message types
interface WsMessageStart {
  type: 'start';
}
interface WsMessageChunk {
  type: 'chunk';
  content: string;
}
interface WsMessageDone {
  type: 'done';
}
interface WsMessageInsight {
  type: 'insight';
  content: string;
}
interface WsMessageTranscript {
  type: 'transcript';
  text: string;
  source: string;
}
interface WsMessageAutoStart {
  type: 'auto_start';
  question: string;
}
interface WsMessageAutoChunk {
  type: 'auto_chunk';
  content: string;
}
interface WsMessageAutoDone {
  type: 'auto_done';
}

type WsMessage =
  | WsMessageStart
  | WsMessageChunk
  | WsMessageDone
  | WsMessageInsight
  | WsMessageTranscript
  | WsMessageAutoStart
  | WsMessageAutoChunk
  | WsMessageAutoDone;

const getBackoffDelay = (attempt: number): number => {
  const exponential = Math.min(BACKOFF_BASE_MS * 2 ** attempt, BACKOFF_MAX_MS);
  const jitter = exponential * JITTER_FACTOR * Math.random();
  return exponential + jitter;
};

export const useChatConnection = () => {
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);

  // We use selectors to avoid re-renders if possible, but here we just destructure actions which are stable
  const setStatus = useChatStore((state) => state.setStatus);
  const setStream = useChatStore((state) => state.setStream);
  const appendStreamToContent = useChatStore((state) => state.appendStreamToContent);
  const commitStreamToMessage = useChatStore((state) => state.commitStreamToMessage);
  const addMessageToCurrent = useChatStore((state) => state.addMessageToCurrent);
  const updateCurrentSessionTitle = useChatStore((state) => state.updateCurrentSessionTitle);
  const addTranscript = useChatStore((state) => state.addTranscript);
  const startAutoAnswer = useChatStore((state) => state.startAutoAnswer);
  const appendAutoAnswer = useChatStore((state) => state.appendAutoAnswer);
  const finishAutoAnswer = useChatStore((state) => state.finishAutoAnswer);
  const status = useChatStore((state) => state.status);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    ws.current = new WebSocket(WS_URL);

    ws.current.onopen = () => {
      reconnectAttempt.current = 0;
      setStatus('connected');
    };
    ws.current.onclose = () => {
      setStatus('disconnected');
      const delay = getBackoffDelay(reconnectAttempt.current);
      reconnectAttempt.current++;
      setTimeout(connect, delay);
    };

    ws.current.onmessage = (e: MessageEvent<string>) => {
      try {
        const data = JSON.parse(e.data) as WsMessage;
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
          case 'transcript':
            addTranscript(data.text, data.source);
            break;
          case 'auto_start':
            startAutoAnswer(data.question);
            break;
          case 'auto_chunk':
            appendAutoAnswer(data.content);
            break;
          case 'auto_done':
            finishAutoAnswer();
            break;
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
  }, [
    setStatus,
    setStream,
    appendStreamToContent,
    commitStreamToMessage,
    addMessageToCurrent,
    addTranscript,
    startAutoAnswer,
    appendAutoAnswer,
    finishAutoAnswer,
  ]);

  useEffect(() => {
    connect();
    return () => {
      ws.current?.close();
    };
  }, [connect]);

  const sendMessage = (content: string) => {
    if (!content.trim() || status !== 'connected') return;

    // Start trace for this chat request
    const { ctx, end } = startTrace('chat_request');

    // Get current state to check if first message
    const state = useChatStore.getState();
    const currentSession = state.sessions.find((s) => s.id === state.currentSessionId);
    const isFirstMessage = currentSession?.messages.length === 0;

    // Optimistic update
    addMessageToCurrent({ role: 'user', content });

    // Send to WS with trace context
    ws.current?.send(
      JSON.stringify({
        type: 'chat',
        message: content,
        trace_id: ctx.traceId,
      })
    );

    // End trace (ideally this would be called on 'done' message, but for now we call it here)
    end();

    // Update title if first message
    if (isFirstMessage) {
      const title =
        content.slice(0, SESSION_TITLE_MAX_LENGTH) +
        (content.length > SESSION_TITLE_MAX_LENGTH ? '...' : '');
      updateCurrentSessionTitle(title);
    }
  };

  return { sendMessage };
};
