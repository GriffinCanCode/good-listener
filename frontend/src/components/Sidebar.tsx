import React from 'react';
import { MessageSquare, Trash2, Plus, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Session {
  id: string;
  title: string;
  date: string;
}

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  sessions: Session[];
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string, e: React.MouseEvent) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  sessions,
  currentSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="sidebar-backdrop"
          />
          
          {/* Sidebar */}
          <motion.div
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="sidebar"
          >
            <div className="sidebar-header">
              <h2>History</h2>
              <button onClick={onClose} className="icon-btn">
                <X size={18} />
              </button>
            </div>

            <button onClick={onNewSession} className="new-chat-btn">
              <Plus size={16} />
              <span>New Chat</span>
            </button>

            <div className="session-list">
              {sessions.length === 0 ? (
                <div className="empty-history">
                  No history yet.
                </div>
              ) : (
                sessions.map(session => (
                  <div
                    key={session.id}
                    onClick={() => onSelectSession(session.id)}
                    className={`session-item ${session.id === currentSessionId ? 'active' : ''}`}
                  >
                    <MessageSquare size={16} className="session-icon" />
                    <span className="session-title">{session.title}</span>
                    <button
                      onClick={(e) => onDeleteSession(session.id, e)}
                      className="delete-btn"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

