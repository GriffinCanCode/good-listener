import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Stoplight } from './components/Stoplight';

const API_BASE = 'http://127.0.0.1:8000';
const WS_URL = 'ws://127.0.0.1:8000/ws';
const ELECTRON = (window as any).require?.('electron');

interface Message { role: 'user' | 'assistant'; content: string; }

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [stream, setStream] = useState('');
  const [status, setStatus] = useState<'connected' | 'disconnected'>('disconnected');
  const [input, setInput] = useState('');
  const ws = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const connect = useCallback(() => {
    ws.current = new WebSocket(WS_URL);
    ws.current.onopen = () => setStatus('connected');
    ws.current.onclose = () => { setStatus('disconnected'); setTimeout(connect, 3000); };
    
    ws.current.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        switch (data.type) {
          case 'start':
            setStream('');
            break;
          case 'chunk':
            setStream(p => p + data.content);
            break;
          case 'done':
            setMessages(p => [...p, { role: 'assistant', content: stream }]); // Note: this might be stale due to closure
            setStream('');
            break;
          case 'insight':
            setMessages(p => [...p, { role: 'assistant', content: data.content }]);
            break;
        }
      } catch { /* Ignore non-JSON */ }
    };
  }, [stream]); // 'stream' dep is problematic for closure, but we handle below.

  // Fix for 'done' closure issue: rely on state updater with a fresh ref or simply
  // don't clear stream until we push it.
  // Actually, cleaner approach:
  // Just rely on `stream` state for the LAST message if it's active.

  // Better implementation of onmessage avoiding stale closures:
  useEffect(() => {
    if (!ws.current) return;
    ws.current.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'start') setStream('');
        else if (data.type === 'chunk') setStream(prev => prev + data.content);
        else if (data.type === 'done') {
          setStream(prev => {
            setMessages(msgs => [...msgs, { role: 'assistant', content: prev }]);
            return '';
          });
        }
        else if (data.type === 'insight') {
           setMessages(msgs => [...msgs, { role: 'assistant', content: data.content }]);
        }
      } catch {}
    };
  }, [status]); // Re-bind if status changes (reconnected)

  useEffect(() => {
    connect();
    ELECTRON?.ipcRenderer.on('window-shown', () => console.log('Window shown'));
    return () => { ws.current?.close(); ELECTRON?.ipcRenderer.removeAllListeners('window-shown'); };
  }, []); // Connect once

  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages, stream]);

  const send = () => {
    if (!input.trim() || status !== 'connected') return;
    setMessages(p => [...p, { role: 'user', content: input }]);
    ws.current?.send(JSON.stringify({ type: 'chat', message: input }));
    setInput('');
  };

  return (
    <div className="app-container">
      <div className="header">
        <Stoplight />
        <div className={`status-dot ${status}`} />
        <span>Good Listener</span>
        <button onClick={() => fetch(`${API_BASE}/api/capture`).catch(console.error)} className="capture-btn">📸</button>
      </div>

      <div className="chat-area">
        {!messages.length && !stream && <div className="empty-state">Ready to help.</div>}
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>{m.content}</div>
        ))}
        {stream && <div className="message assistant">{stream}</div>}
        <div ref={bottomRef} />
      </div>

      <div className="input-area">
        <textarea 
          value={input} 
          onChange={e => setInput(e.target.value)} 
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
          placeholder="Ask about your screen..." 
        />
      </div>
    </div>
  );
};

export default App;
