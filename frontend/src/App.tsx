import gsap from 'gsap';
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
import { MicButton } from './components/MicButton';
import { Presence } from './components/Presence';
import { Sidebar } from './components/Sidebar';
import { Stoplight } from './components/Stoplight';
import { VoiceActivityIndicator } from './components/VoiceActivityIndicator';
import { useAutoScroll } from './hooks/useAutoScroll';
import { useChatConnection } from './hooks/useChatConnection';
import { duration, ease } from './lib/animations';
import { useChatStore } from './store/useChatStore';
import { useUIStore } from './store/useUIStore';

const API_BASE = 'http://127.0.0.1:8000';
const DEFAULT_WIDTH = 400;
const TRANSCRIPT_WIDTH = 320;
const DEFAULT_HEIGHT = 600;

// ═══════════════════════════════════════════════════════════════════════════
// Auto Answer Card - With smooth GSAP animations
// ═══════════════════════════════════════════════════════════════════════════

interface AutoAnswerCardProps {
  autoAnswer: { question: string; content: string; isStreaming: boolean };
  onDismiss: () => void;
}

const AutoAnswerCard: React.FC<AutoAnswerCardProps> = ({ autoAnswer, onDismiss }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      gsap.fromTo(
        ref.current,
        { opacity: 0, y: -20, scale: 0.95 },
        { opacity: 1, y: 0, scale: 1, duration: duration.smooth, ease: ease.bounce }
      );
    }
  }, []);

  return (
    <div ref={ref} className="auto-answer-card">
      <div className="auto-answer-header">
        <div className="auto-answer-badge">
          <Zap size={14} />
          <span>Question Detected</span>
        </div>
        <button onClick={onDismiss} className="icon-btn auto-dismiss">
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
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Message Component - Individual chat message with enter animation
// ═══════════════════════════════════════════════════════════════════════════

interface MessageProps {
  content: string;
  role: 'user' | 'assistant';
  index: number;
}

const Message: React.FC<MessageProps> = ({ content, role, index }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      gsap.fromTo(
        ref.current,
        { opacity: 0, y: 12 },
        { opacity: 1, y: 0, duration: duration.normal, ease: ease.butter, delay: index * 0.02 }
      );
    }
  }, [index]);

  return (
    <div ref={ref} className={`message ${role}`}>
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Stream Message - Currently streaming message
// ═══════════════════════════════════════════════════════════════════════════

const StreamMessage: React.FC<{ content: string }> = ({ content }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      gsap.fromTo(
        ref.current,
        { opacity: 0 },
        { opacity: 1, duration: duration.fast, ease: ease.silk }
      );
    }
  }, []);

  return (
    <div ref={ref} className="message assistant">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Welcome Hero - Empty state
// ═══════════════════════════════════════════════════════════════════════════

const WelcomeHero: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      gsap.fromTo(
        ref.current,
        { opacity: 0, y: 16, scale: 0.98 },
        { opacity: 1, y: 0, scale: 1, duration: duration.smooth, ease: ease.butter }
      );
    }
  }, []);

  return (
    <div ref={ref} className="welcome-hero">
      <Sparkles size={48} className="hero-icon" />
      <h1>Ready to Listen</h1>
      <p>Ask me anything about what's on your screen.</p>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Transcript Panel - Slide-in panel with GSAP
// ═══════════════════════════════════════════════════════════════════════════

const TranscriptPanel: React.FC = () => (
  <div className="live-transcript-wrapper">
    <div className="transcript-header">
      <h3>Live Transcript</h3>
    </div>
    <VoiceActivityIndicator />
    <LiveTranscript />
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════
// Main App Component
// ═══════════════════════════════════════════════════════════════════════════

const App: React.FC = () => {
  const [input, setInput] = useState('');
  const [showTranscript, setShowTranscript] = useState(false);

  const { stream, status, createSession, getCurrentSession, autoAnswer, dismissAutoAnswer } =
    useChatStore();

  const { isSidebarOpen, toggleSidebar } = useUIStore();
  const { sendMessage } = useChatConnection();

  const currentSession = getCurrentSession();
  const messages = currentSession?.messages ?? [];
  const { containerRef } = useAutoScroll([messages, stream]);

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
            <MicButton />
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
          <Presence animation="scaleUp">
            {autoAnswer && (
              <AutoAnswerCard
                key="auto-answer"
                autoAnswer={autoAnswer}
                onDismiss={dismissAutoAnswer}
              />
            )}
          </Presence>

          <div ref={containerRef} className="chat-area">
            {messages.length === 0 && !stream ? (
              <div className="empty-state">
                <WelcomeHero />
              </div>
            ) : (
              <>
                <div className="chat-spacer" />
                {messages.map((m, i) => (
                  <Message key={i} content={m.content} role={m.role} index={i} />
                ))}
                {stream && <StreamMessage content={stream} />}
              </>
            )}
          </div>

          <Presence animation="slideLeft">
            {showTranscript && <TranscriptPanel key="transcript" />}
          </Presence>
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
