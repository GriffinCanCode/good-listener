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
  speaker: string;
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
interface WsMessageVAD {
  type: 'vad';
  probability: number;
  is_speech: boolean;
  source: 'user' | 'system';
}

type WsMessage =
  | WsMessageStart
  | WsMessageChunk
  | WsMessageDone
  | WsMessageInsight
  | WsMessageTranscript
  | WsMessageAutoStart
  | WsMessageAutoChunk
  | WsMessageAutoDone
  | WsMessageVAD;

const getBackoffDelay = (attempt: number): number => {
  const exponential = Math.min(BACKOFF_BASE_MS * 2 ** attempt, BACKOFF_MAX_MS);
  return exponential + exponential * JITTER_FACTOR * Math.random();
};

export const useChatConnection = () => {
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const setStatus = useChatStore((s) => s.setStatus);
  const setStream = useChatStore((s) => s.setStream);
  const appendStreamToContent = useChatStore((s) => s.appendStreamToContent);
  const commitStreamToMessage = useChatStore((s) => s.commitStreamToMessage);
  const addMessageToCurrent = useChatStore((s) => s.addMessageToCurrent);
  const updateCurrentSessionTitle = useChatStore((s) => s.updateCurrentSessionTitle);
  const addTranscript = useChatStore((s) => s.addTranscript);
  const startAutoAnswer = useChatStore((s) => s.startAutoAnswer);
  const appendAutoAnswer = useChatStore((s) => s.appendAutoAnswer);
  const finishAutoAnswer = useChatStore((s) => s.finishAutoAnswer);
  const updateVAD = useChatStore((s) => s.updateVAD);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    // Only skip if there's an active connection
    if (
      ws.current &&
      (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)
    )
      return;

    // Clear any stale reference
    ws.current = null;

    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => {
      if (!mountedRef.current) return;
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }
      reconnectAttempt.current = 0;
      setStatus('connected');
    };

    socket.onerror = () => {
      /* onclose handles reconnection */
    };

    socket.onclose = () => {
      if (!mountedRef.current) return;
      ws.current = null;
      setStatus('disconnected');
      reconnectTimeout.current = setTimeout(connect, getBackoffDelay(reconnectAttempt.current++));
    };

    socket.onmessage = (e: MessageEvent<string>) => {
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
            addTranscript(data.text, data.source, data.speaker);
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
          case 'vad':
            updateVAD(data.probability, data.is_speech, data.source);
            break;
        }
      } catch {
        /* ignore parse errors */
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
    updateVAD,
  ]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }
      if (ws.current) {
        // Detach handlers to prevent callbacks after unmount
        ws.current.onopen = null;
        ws.current.onclose = null;
        ws.current.onerror = null;
        ws.current.onmessage = null;
        // Only close if actually open (closing CONNECTING state logs console errors)
        if (ws.current.readyState === WebSocket.OPEN) {
          ws.current.close(1000);
        }
        ws.current = null;
      }
    };
  }, [connect]);

  const sendMessage = useCallback(
    (content: string) => {
      if (!content.trim()) return;

      // Check current connection status and WebSocket state
      const { status } = useChatStore.getState();
      if (status !== 'connected' || !ws.current || ws.current.readyState !== WebSocket.OPEN) return;

      const { ctx, end } = startTrace('chat_request');
      const state = useChatStore.getState();
      const currentSession = state.sessions.find((s) => s.id === state.currentSessionId);
      const isFirstMessage = currentSession?.messages.length === 0;

      addMessageToCurrent({ role: 'user', content });
      ws.current.send(JSON.stringify({ type: 'chat', message: content, trace_id: ctx.traceId }));
      end();

      if (isFirstMessage) {
        const title =
          content.length > SESSION_TITLE_MAX_LENGTH
            ? content.slice(0, SESSION_TITLE_MAX_LENGTH) + '...'
            : content;
        updateCurrentSessionTitle(title);
      }
    },
    [addMessageToCurrent, updateCurrentSessionTitle]
  );

  return { sendMessage };
};
