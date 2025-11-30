import React, { useEffect, useRef } from 'react';
import { useChatStore } from '../store/useChatStore';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Monitor } from 'lucide-react';

export const LiveTranscript: React.FC = () => {
  const transcripts = useChatStore((state) => state.liveTranscripts);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts]);

  if (transcripts.length === 0) {
      return (
        <div className="live-transcript-container empty">
            <div className="empty-message">
                Waiting for audio...
            </div>
        </div>
      );
  }

  return (
    <div className="live-transcript-container">
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
                {t.source === 'user' ? <Mic size={14} /> : <Monitor size={14} />}
              </div>
              <div className="transcript-content">
                <span className="transcript-source">
                  {t.source === 'user' ? 'You' : 'System'}
                </span>
                <p>{t.text}</p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
