import { AnimatePresence, motion } from 'framer-motion';
import {
  Camera,
  FileText,
  Menu,
  MessageCircleQuestion,
  Send,
  Sparkles,
  X,
  Zap,
} from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { LiveTranscript } from './components/LiveTranscript';
import { Sidebar } from './components/Sidebar';
import { Stoplight } from './components/Stoplight';
import { useChatConnection } from './hooks/useChatConnection';
import { useChatStore } from './store/useChatStore';
import { useUIStore } from './store/useUIStore';

const API_BASE = 'http://127.0.0.1:8000';
const DEFAULT_WIDTH = 400;
const TRANSCRIPT_WIDTH = 320;
const DEFAULT_HEIGHT = 600;

const App: React.FC = () => {
  const [input, setInput] = useState('');
  const [showTranscript, setShowTranscript] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { stream, status, createSession, getCurrentSession, autoAnswer, dismissAutoAnswer } =
    useChatStore();

  const { isSidebarOpen, toggleSidebar } = useUIStore();
  const { sendMessage } = useChatConnection();

  const currentSession = getCurrentSession();
  const messages = currentSession?.messages ?? [];

  // Always start with a fresh conversation
  useEffect(() => {
    createSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally run only on mount
  }, []);

  // Electron listeners
  useEffect(() => {
    const cleanup = window.electron?.window.onShown(() => console.log('Window shown'));
    return () => cleanup?.();
  }, []);

  // Handle Window Resizing
  useEffect(() => {
    const targetWidth = showTranscript ? DEFAULT_WIDTH + TRANSCRIPT_WIDTH : DEFAULT_WIDTH;
    window.electron?.window.resize(targetWidth, DEFAULT_HEIGHT);
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

        <div className="chat-container">
          {/* Auto-Answer Card - Shows when question detected */}
          <AnimatePresence>
            {autoAnswer && (
              <motion.div
                initial={{ opacity: 0, y: -20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -10, scale: 0.95 }}
                transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
                className="auto-answer-card"
              >
                <div className="auto-answer-header">
                  <div className="auto-answer-badge">
                    <Zap size={14} />
                    <span>Question Detected</span>
                  </div>
                  <button onClick={dismissAutoAnswer} className="icon-btn auto-dismiss">
                    <X size={14} />
                  </button>
                </div>
                <div className="auto-answer-question">
                  <MessageCircleQuestion size={16} />
                  <span>"{autoAnswer.question}"</span>
                </div>
                <div className="auto-answer-content">
                  {autoAnswer.content ? (
                    <ReactMarkdown>{autoAnswer.content}</ReactMarkdown>
                  ) : (
                    <div className="auto-answer-loading">
                      <span className="pulse-dot" />
                      <span className="pulse-dot" />
                      <span className="pulse-dot" />
                    </div>
                  )}
                </div>
                {autoAnswer.isStreaming && autoAnswer.content && (
                  <div className="auto-answer-streaming">
                    <span className="streaming-indicator" />
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          <div className="chat-area">
            {messages.length === 0 && !stream ? (
              <div className="empty-state">
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2 }}
                  className="welcome-hero"
                >
                  <Sparkles size={48} className="hero-icon" />
                  <h1>Ready to Listen</h1>
                  <p>Ask me anything about what's on your screen.</p>
                </motion.div>
              </div>
            ) : (
              <>
                <div className="chat-spacer" />
                {messages.map((m, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.15, ease: 'easeOut' }}
                    className={`message ${m.role}`}
                  >
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                  </motion.div>
                ))}
                {stream && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.1 }}
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
                transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
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
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) =>
                e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())
              }
              placeholder="Type a message..."
              rows={1}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || status !== 'connected'}
              className="send-btn"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
