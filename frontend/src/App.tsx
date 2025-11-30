import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Stoplight } from './components/Stoplight';
import { Sidebar } from './components/Sidebar';
import ReactMarkdown from 'react-markdown';
import { Menu, Send, Camera, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

const API_BASE = 'http://127.0.0.1:8000';
const WS_URL = 'ws://127.0.0.1:8000/ws';
const ELECTRON = (window as any).require?.('electron');

interface Message { role: 'user' | 'assistant'; content: string; }
interface Session { id: string; title: string; date: string; messages: Message[]; }

const App: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [stream, setStream] = useState('');
  const [status, setStatus] = useState<'connected' | 'disconnected'>('disconnected');
  const [input, setInput] = useState('');
  const ws = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load sessions on mount
  useEffect(() => {
    const saved = localStorage.getItem('chat_sessions');
    if (saved) {
      const parsed = JSON.parse(saved);
      setSessions(parsed);
      if (parsed.length > 0) {
        setCurrentSessionId(parsed[0].id);
        setMessages(parsed[0].messages);
      }
    } else {
      createNewSession();
    }
  }, []);

  // Save sessions when updated
  useEffect(() => {
    if (sessions.length > 0) {
      localStorage.setItem('chat_sessions', JSON.stringify(sessions));
    }
  }, [sessions]);

  // Update current session messages
  useEffect(() => {
    if (!currentSessionId) return;
    setSessions(prev => prev.map(s => 
      s.id === currentSessionId 
        ? { ...s, messages: [...messages, ...(stream ? [{ role: 'assistant', content: stream } as Message] : [])] }
        : s
    ));
  }, [messages, stream, currentSessionId]);

  const createNewSession = () => {
    const newSession: Session = {
      id: Date.now().toString(),
      title: 'New Chat',
      date: new Date().toISOString(),
      messages: []
    };
    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
    setMessages([]);
    setStream('');
    if (window.innerWidth < 768) setSidebarOpen(false);
  };

  const deleteSession = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const newSessions = sessions.filter(s => s.id !== id);
    setSessions(newSessions);
    if (currentSessionId === id) {
      if (newSessions.length > 0) {
        setCurrentSessionId(newSessions[0].id);
        setMessages(newSessions[0].messages);
      } else {
        createNewSession();
      }
    }
  };

  const selectSession = (id: string) => {
    const session = sessions.find(s => s.id === id);
    if (session) {
      setCurrentSessionId(id);
      setMessages(session.messages);
      setStream('');
      if (window.innerWidth < 768) setSidebarOpen(false);
    }
  };

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;
    ws.current = new WebSocket(WS_URL);
    ws.current.onopen = () => setStatus('connected');
    ws.current.onclose = () => { setStatus('disconnected'); setTimeout(connect, 3000); };
    
    ws.current.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        switch (data.type) {
          case 'start': setStream(''); break;
          case 'chunk': setStream(p => p + data.content); break;
          case 'done':
            setStream(finalStream => {
              setMessages(prev => [...prev, { role: 'assistant', content: finalStream }]);
              return '';
            });
            break;
          case 'insight':
            setMessages(prev => [...prev, { role: 'assistant', content: data.content }]);
            break;
        }
      } catch {}
    };
  }, []);

  useEffect(() => {
    connect();
    ELECTRON?.ipcRenderer.on('window-shown', () => console.log('Window shown'));
    return () => { ws.current?.close(); ELECTRON?.ipcRenderer.removeAllListeners('window-shown'); };
  }, [connect]);

  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages, stream]);

  const send = () => {
    if (!input.trim() || status !== 'connected') return;
    const userMsg: Message = { role: 'user', content: input };
    setMessages(p => [...p, userMsg]);
    ws.current?.send(JSON.stringify({ type: 'chat', message: input }));
    setInput('');
    
    // Update session title if it's the first message
    if (messages.length === 0 && currentSessionId) {
      setSessions(prev => prev.map(s => 
        s.id === currentSessionId 
          ? { ...s, title: input.slice(0, 30) + (input.length > 30 ? '...' : '') }
          : s
      ));
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        sessions={sessions.map(s => ({ id: s.id, title: s.title, date: s.date }))}
        currentSessionId={currentSessionId}
        onSelectSession={selectSession}
        onNewSession={createNewSession}
        onDeleteSession={deleteSession}
      />

      <div className={`main-content ${sidebarOpen ? 'pushed' : ''}`}>
        <div className="header draggable">
          <div className="header-left">
             <button onClick={() => setSidebarOpen(!sidebarOpen)} className="icon-btn menu-btn no-drag">
              <Menu size={20} />
            </button>
            <Stoplight />
          </div>
          <div className="header-title">
            <span className={`status-dot ${status}`} />
            <span>Good Listener</span>
          </div>
          <button 
            onClick={() => fetch(`${API_BASE}/api/capture`).catch(console.error)} 
            className="icon-btn capture-btn no-drag"
            title="Capture Screen"
          >
            <Camera size={20} />
          </button>
        </div>

        <div className="chat-area">
          {messages.length === 0 && !stream ? (
            <div className="empty-state">
              <motion.div 
                initial={{ scale: 0.9, opacity: 0 }} 
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.5 }}
                className="welcome-hero"
              >
                <Sparkles size={48} className="hero-icon" />
                <h1>Ready to Listen</h1>
                <p>Ask me anything about what's on your screen.</p>
              </motion.div>
            </div>
          ) : (
            <>
              {messages.map((m, i) => (
                <motion.div 
                  key={i} 
                  initial={{ opacity: 0, y: 10 }} 
                  animate={{ opacity: 1, y: 0 }}
                  className={`message ${m.role}`}
                >
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </motion.div>
              ))}
              {stream && (
                <motion.div 
                  initial={{ opacity: 0 }} 
                  animate={{ opacity: 1 }}
                  className="message assistant"
                >
                  <ReactMarkdown>{stream}</ReactMarkdown>
                </motion.div>
              )}
            </>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="input-area">
          <div className="input-wrapper">
            <textarea 
              value={input} 
              onChange={e => setInput(e.target.value)} 
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
              placeholder="Type a message..."
              rows={1}
            />
            <button onClick={send} disabled={!input.trim() || status !== 'connected'} className="send-btn">
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
