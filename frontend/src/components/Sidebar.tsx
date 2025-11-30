import React from 'react';
import { MessageSquare, Trash2, Plus, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChatStore } from '../store/useChatStore';
import { useUIStore } from '../store/useUIStore';

export const Sidebar: React.FC = () => {
  const { 
    sessions, 
    currentSessionId, 
    selectSession, 
    createSession, 
    deleteSession 
  } = useChatStore();
  
  const { isSidebarOpen, setSidebarOpen } = useUIStore();

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteSession(id);
  };

  return (
    <AnimatePresence>
      {isSidebarOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={() => setSidebarOpen(false)}
            className="sidebar-backdrop"
          />
          
          {/* Sidebar */}
          <motion.div
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
            className="sidebar"
          >
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
                <div className="empty-history">
                  No history yet.
                </div>
              ) : (
                sessions.map(session => (
                  <div
                    key={session.id}
                    onClick={() => selectSession(session.id)}
                    className={`session-item ${session.id === currentSessionId ? 'active' : ''}`}
                  >
                    <MessageSquare size={16} className="session-icon" />
                    <span className="session-title">{session.title}</span>
                    <button
                      onClick={(e) => handleDelete(session.id, e)}
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
