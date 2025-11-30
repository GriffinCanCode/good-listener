import React, { useEffect, useRef, useState } from 'react';
import { Stoplight } from './components/Stoplight';
import { Sidebar } from './components/Sidebar';
import ReactMarkdown from 'react-markdown';
import { Menu, Send, Camera, Sparkles, FileText, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChatStore } from './store/useChatStore';
import { useUIStore } from './store/useUIStore';
import { useChatConnection } from './hooks/useChatConnection';
import { LiveTranscript } from './components/LiveTranscript';

const API_BASE = 'http://127.0.0.1:8000';
const DEFAULT_WIDTH = 400;
const TRANSCRIPT_WIDTH = 320;
const DEFAULT_HEIGHT = 600;

const App: React.FC = () => {
  const [input, setInput] = useState('');
  const [showTranscript, setShowTranscript] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  
  const { 
    sessions, 
    stream, 
    status, 
    createSession, 
    getCurrentSession 
  } = useChatStore();
  
  const { isSidebarOpen, toggleSidebar } = useUIStore();
  const { sendMessage } = useChatConnection();
  
  const currentSession = getCurrentSession();
  const messages = currentSession?.messages || [];

  // Ensure a session exists on mount
  useEffect(() => {
    if (sessions.length === 0) {
      createSession();
    }
  }, [sessions.length, createSession]);

  // Scroll to bottom on messages/stream change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, stream]);

  // Electron listeners
  useEffect(() => {
    const onWindowShown = () => console.log('Window shown');
    window.electronAPI?.onWindowShown(onWindowShown);
    return () => {
      window.electronAPI?.removeAllWindowShownListeners();
    };
  }, []);

  // Handle Window Resizing
  useEffect(() => {
    if (window.electronAPI) {
      const targetWidth = showTranscript ? DEFAULT_WIDTH + TRANSCRIPT_WIDTH : DEFAULT_WIDTH;
      window.electronAPI.resize(targetWidth, DEFAULT_HEIGHT);
    }
  }, [showTranscript]);

  const handleSend = () => {
    if (!input.trim() || status !== 'connected') return;
    sendMessage(input);
    setInput('');
  };

  return (
    <div className="app-container">
      <Sidebar />

      <div className={`main-content ${isSidebarOpen ? 'pushed' : ''}`}>
        <div className="header draggable">
          <div className="header-left">
             <button onClick={toggleSidebar} className="icon-btn menu-btn no-drag">
              <Menu size={20} />
            </button>
            <Stoplight />
          </div>
          <div className="header-title">
            <span className={`status-dot ${status}`} />
            <span>Good Listener</span>
          </div>
          <div className="header-right no-drag" style={{ display: 'flex', gap: '8px' }}>
            <button 
                onClick={() => setShowTranscript(!showTranscript)} 
                className={`icon-btn ${showTranscript ? 'active' : ''}`}
                title="Toggle Live Transcript"
            >
                <FileText size={20} />
            </button>
            <button 
                onClick={() => fetch(`${API_BASE}/api/capture`).catch(console.error)} 
                className="icon-btn capture-btn"
                title="Capture Screen"
            >
                <Camera size={20} />
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>
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

            <AnimatePresence>
                {showTranscript && (
                    <motion.div 
                        initial={{ x: 20, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        exit={{ x: 20, opacity: 0 }}
                        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                        className="live-transcript-wrapper"
                        style={{ position: 'relative', width: 320, flexShrink: 0 }} 
                    >
                        <div className="transcript-header">
                            <h3>Live Transcript</h3>
                            <button onClick={() => setShowTranscript(false)} className="icon-btn">
                                <X size={16} />
                            </button>
                        </div>
                        <LiveTranscript />
                    </motion.div>
                )}
            </AnimatePresence>
        </div>

        <div className="input-area">
          <div className="input-wrapper">
            <textarea 
              value={input} 
              onChange={e => setInput(e.target.value)} 
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
              placeholder="Type a message..."
              rows={1}
            />
            <button onClick={handleSend} disabled={!input.trim() || status !== 'connected'} className="send-btn">
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
