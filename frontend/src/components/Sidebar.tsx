import { MessageSquare, Plus, Trash2, X } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { duration, ease, fadeIn, fadeOut, slideIn, slideOut } from '../lib/animations';
import { useChatStore } from '../store/useChatStore';
import { useUIStore } from '../store/useUIStore';

export const Sidebar: React.FC = () => {
  const { sessions, currentSessionId, selectSession, createSession, deleteSession } =
    useChatStore();
  const { isSidebarOpen, setSidebarOpen } = useUIStore();

  const [shouldRender, setShouldRender] = useState(isSidebarOpen);
  const backdropRef = useRef<HTMLDivElement>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isSidebarOpen) {
      setShouldRender(true);
      requestAnimationFrame(() => {
        fadeIn(backdropRef.current, { duration: duration.fast, ease: ease.silk });
        slideIn(sidebarRef.current, 'left', { duration: duration.smooth, ease: ease.butter });
      });
    } else if (shouldRender) {
      const onComplete = () => setShouldRender(false);
      // Trigger both, one controls the completion
      fadeOut(backdropRef.current, { duration: duration.fast, ease: ease.silk });
      slideOut(sidebarRef.current, 'left', {
        duration: duration.fast,
        ease: ease.sharp,
        onComplete,
      });
    }
  }, [isSidebarOpen, shouldRender]);

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteSession(id);
  };

  if (!shouldRender) return null;

  return (
    <>
      <div
        ref={backdropRef}
        onClick={() => setSidebarOpen(false)}
        className="sidebar-backdrop"
        style={{ opacity: 0 }}
      />
      <div ref={sidebarRef} className="sidebar" style={{ transform: 'translateX(-100%)' }}>
        <div className="sidebar-header">
          <h2>History</h2>
          <button onClick={() => setSidebarOpen(false)} className="icon-btn">
            <X size={18} />
          </button>
        </div>

        <button onClick={createSession} className="new-chat-btn">
          <Plus size={16} />
          <span>New Chat</span>
        </button>

        <div className="session-list">
          {sessions.length === 0 ? (
            <div className="empty-history">No history yet.</div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => selectSession(session.id)}
                className={`session-item ${session.id === currentSessionId ? 'active' : ''}`}
              >
                <MessageSquare size={16} className="session-icon" />
                <span className="session-title">{session.title}</span>
                <button onClick={(e) => handleDelete(session.id, e)} className="delete-btn">
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
};
