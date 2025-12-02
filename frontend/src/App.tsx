import { Camera, FileText, Menu, Send, Sparkles, X, Zap } from 'lucide-react';
import React, { memo, useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { LiveTranscript } from './components/LiveTranscript';
import { MicButton } from './components/MicButton';
import { SettingsModal } from './components/SettingsModal';
import { Sidebar } from './components/Sidebar';
import { Stoplight } from './components/Stoplight';
import { useAutoScroll } from './hooks/useAutoScroll';
import { useChatConnection } from './hooks/useChatConnection';
import { duration, ease, fadeIn, scaleIn } from './lib/animations';
import { useChatStore } from './store/useChatStore';
import { useUIStore } from './store/useUIStore';

const API_BASE = 'http://127.0.0.1:8000';
const DEFAULT_WIDTH = 400;
const TRANSCRIPT_WIDTH = 360;
const DEFAULT_HEIGHT = 600;

interface AutoAnswerCardProps {
  autoAnswer: { question: string; content: string; isStreaming: boolean };
  onDismiss: () => void;
}

const AutoAnswerCard = memo(
  React.forwardRef<HTMLDivElement, AutoAnswerCardProps>(({ autoAnswer, onDismiss }, ref) => {
    useEffect(() => {
      const timer = setTimeout(onDismiss, 2500);
      return () => clearTimeout(timer);
    }, [onDismiss]);

    return (
      <div ref={ref} className="auto-answer-toast">
        <div className="toast-icon">
          <Zap size={16} />
        </div>
        <div className="toast-content">
          <div className="toast-title">Question Detected</div>
          <div className="toast-message">"{autoAnswer.question}"</div>
        </div>
        <button onClick={onDismiss} className="icon-btn toast-close">
          <X size={14} />
        </button>
      </div>
    );
  })
);
AutoAnswerCard.displayName = 'AutoAnswerCard';

const Message = memo<{ content: string; role: 'user' | 'assistant'; index: number }>(
  ({ content, role, index }) => {
    const ref = useRef<HTMLDivElement>(null);
    useEffect(() => {
      fadeIn(ref.current, {
        y: 12,
        delay: index * 0.02,
        duration: duration.normal,
        ease: ease.butter,
      });
    }, [index]);
    return (
      <div ref={ref} className={`message ${role}`}>
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    );
  }
);
Message.displayName = 'Message';

const StreamMessage = memo<{ content: string }>(({ content }) => {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    fadeIn(ref.current, { duration: duration.fast, ease: ease.silk });
  }, []);
  return (
    <div ref={ref} className="message assistant">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
});
StreamMessage.displayName = 'StreamMessage';

const WelcomeHero = memo(() => {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scaleIn(ref.current, { from: 0.98, y: 16, duration: duration.smooth, ease: ease.butter });
  }, []);
  return (
    <div ref={ref} className="welcome-hero">
      <Sparkles size={48} className="hero-icon" />
      <h1>Ready to Listen</h1>
      <p>Ask me anything about what's on your screen.</p>
    </div>
  );
});
WelcomeHero.displayName = 'WelcomeHero';

const App: React.FC = () => {
  const [input, setInput] = useState('');
  const [showTranscript, setShowTranscript] = useState(false);
  const { stream, status, createSession, getCurrentSession, autoAnswer, dismissAutoAnswer } =
    useChatStore();
  const { isSidebarOpen, toggleSidebar } = useUIStore();
  const { sendMessage } = useChatConnection();
  const messages = getCurrentSession()?.messages ?? [];
  const { containerRef } = useAutoScroll([messages, stream]);

  // Sync settings on startup
  useEffect(() => {
    void window.electron?.settings
      .get()
      .then((settings) => {
        void fetch(`${API_BASE}/api/config`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            provider: settings.llm.provider,
            model: settings.llm.model,
            api_key: settings.llm.apiKey,
            ollama_host: settings.llm.ollamaHost,
          }),
        }).catch(console.error);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    createSession();
  }, [createSession]);

  useEffect(() => {
    return window.electron?.window.onShown(() => console.log('Window shown'));
  }, []);

  useEffect(() => {
    window.electron?.window.resize(
      showTranscript ? DEFAULT_WIDTH + TRANSCRIPT_WIDTH : DEFAULT_WIDTH,
      DEFAULT_HEIGHT
    );
  }, [showTranscript]);

  const handleSend = useCallback(() => {
    if (!input.trim() || status !== 'connected') return;
    sendMessage(input);
    setInput('');
  }, [input, status, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const toggleTranscript = useCallback(() => setShowTranscript((prev) => !prev), []);
  const captureScreen = useCallback(
    () => fetch(`${API_BASE}/api/capture`).catch(console.error),
    []
  );

  const handleRemember = useCallback(() => {
    if (status === 'connected') {
      sendMessage('Please remember this context.');
    }
  }, [status, sendMessage]);

  return (
    <div className="app-container">
      <Sidebar />
      <SettingsModal />
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
              onClick={toggleTranscript}
              className={`icon-btn ${showTranscript ? 'active' : ''}`}
              title="Toggle Live Transcript"
            >
              <FileText size={20} />
            </button>
            <button onClick={captureScreen} className="icon-btn capture-btn" title="Capture Screen">
              <Camera size={20} />
            </button>
          </div>
        </div>

        <div className="chat-container">
          {autoAnswer && (
            <AutoAnswerCard
              key="auto-answer"
              autoAnswer={autoAnswer}
              onDismiss={dismissAutoAnswer}
            />
          )}

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

          {showTranscript && <LiveTranscript onRemember={handleRemember} />}
        </div>

        <div className="input-area">
          <div className="input-wrapper">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
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
