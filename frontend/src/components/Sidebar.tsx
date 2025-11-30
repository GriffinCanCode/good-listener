import { MessageSquare, Plus, Trash2, X } from 'lucide-react';
import React, { memo, useCallback, useEffect, useRef, useState } from 'react';
import { duration, ease, fadeIn, fadeOut, slideIn, slideOut } from '../lib/animations';
import { useChatStore } from '../store/useChatStore';
import { useUIStore } from '../store/useUIStore';

interface SessionItemProps {
  id: string;
  title: string;
  isActive: boolean;
  onSelect: (id: string) => void;
  onDelete: (id: string, e: React.MouseEvent) => void;
}

const SessionItem = memo(({ id, title, isActive, onSelect, onDelete }: SessionItemProps) => (
  <div onClick={() => onSelect(id)} className={`session-item ${isActive ? 'active' : ''}`}>
    <MessageSquare size={16} className="session-icon" />
    <span className="session-title">{title}</span>
    <button onClick={(e) => onDelete(id, e)} className="delete-btn">
      <Trash2 size={14} />
    </button>
  </div>
));
SessionItem.displayName = 'SessionItem';

export const Sidebar = memo(() => {
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
      fadeOut(backdropRef.current, { duration: duration.fast, ease: ease.silk });
      slideOut(sidebarRef.current, 'left', {
        duration: duration.fast,
        ease: ease.sharp,
        onComplete,
      });
    }
  }, [isSidebarOpen, shouldRender]);

  const handleDelete = useCallback(
    (id: string, e: React.MouseEvent) => {
      e.stopPropagation();
      deleteSession(id);
    },
    [deleteSession]
  );

  const handleClose = useCallback(() => setSidebarOpen(false), [setSidebarOpen]);

  if (!shouldRender) return null;

  return (
    <>
      <div
        ref={backdropRef}
        onClick={handleClose}
        className="sidebar-backdrop"
        style={{ opacity: 0 }}
      />
      <div ref={sidebarRef} className="sidebar" style={{ transform: 'translateX(-100%)' }}>
        <div className="sidebar-header">
          <h2>History</h2>
          <button onClick={handleClose} className="icon-btn">
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
              <SessionItem
                key={session.id}
                id={session.id}
                title={session.title}
                isActive={session.id === currentSessionId}
                onSelect={selectSession}
                onDelete={handleDelete}
              />
            ))
          )}
        </div>
      </div>
    </>
  );
});
Sidebar.displayName = 'Sidebar';
