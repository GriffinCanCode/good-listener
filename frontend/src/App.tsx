import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Stoplight } from './components/Stoplight';

const API_BASE = 'http://127.0.0.1:8000';
const WS_URL = 'ws://127.0.0.1:8000/ws';
const ELECTRON = (window as any).require?.('electron');

interface Message { role: 'user' | 'assistant'; content: string; }

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [status, setStatus] = useState<'connected' | 'disconnected'>('disconnected');
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
            setMessages(p => [...p, { role: 'assistant', content: '' }]);
            break;
          case 'chunk':
            setMessages(p => {
              const newMsgs = [...p];
              const last = newMsgs[newMsgs.length - 1];
              if (last?.role === 'assistant') {
                newMsgs[newMsgs.length - 1] = { ...last, content: last.content + data.content };
                return newMsgs;
              }
              return [...p, { role: 'assistant', content: data.content }];
            });
            break;
          case 'insight':
            setMessages(p => [...p, { role: 'assistant', content: data.content }]);
            break;
          default:
            break;
        }
      } catch {
        setMessages(p => [...p, { role: 'assistant', content: e.data }]);
      }
    };
  }, []);

  useEffect(() => {
    connect();
    ELECTRON?.ipcRenderer.on('window-shown', () => console.log('Window shown'));
    return () => { ws.current?.close(); ELECTRON?.ipcRenderer.removeAllListeners('window-shown'); };
  }, [connect]);

  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages]);

  const send = () => {
    if (!input.trim() || status !== 'connected') return;
    setMessages(p => [...p, { role: 'user', content: input }]);
    ws.current?.send(JSON.stringify({ type: 'chat', message: input }));
    setInput('');
  };

  const capture = async () => {
    try { await fetch(`${API_BASE}/api/capture`); } 
    catch (e) { console.error('Capture failed', e); }
  };

  return (
    <div className="app-container">
      <div className="header">
        <Stoplight />
        <div className={`status-dot ${status}`} />
        <span>Good Listener</span>
        <button onClick={capture} className="capture-btn" title="Force Capture">📸</button>
      </div>

      <div className="chat-area">
        {!messages.length && <div className="empty-state">Ready to help. Press Cmd+H to toggle.</div>}
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>{m.content}</div>
        ))}
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
