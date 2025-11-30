import { AnimatePresence, motion } from 'framer-motion';
import { Mic, User } from 'lucide-react';
import React from 'react';
import ScrollToBottom from 'react-scroll-to-bottom';
import { useChatStore } from '../store/useChatStore';

export const LiveTranscript: React.FC = () => {
  const transcripts = useChatStore((state) => state.liveTranscripts);

  if (!transcripts.length) {
    return (
      <div className="live-transcript-container empty">
        <div className="empty-message">Waiting for audio...</div>
      </div>
    );
  }

  return (
    <ScrollToBottom
      className="live-transcript-container"
      followButtonClassName="scroll-to-bottom-btn"
    >
      <div className="transcript-list">
        <AnimatePresence initial={false}>
          {transcripts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.12, ease: 'easeOut' }}
              className={`transcript-item ${t.source}`}
            >
              <div className="transcript-icon">
                {t.source === 'user' ? <Mic size={14} /> : <User size={14} />}
              </div>
              <div className="transcript-content">
                <span className="transcript-source">{t.speaker}</span>
                <p>{t.text}</p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ScrollToBottom>
  );
};
