import gsap from 'gsap';
import { Mic, User } from 'lucide-react';
import React, { useEffect, useRef } from 'react';
import { useAutoScroll } from '../hooks/useAutoScroll';
import { duration, ease } from '../lib/animations';
import { useChatStore } from '../store/useChatStore';

// ═══════════════════════════════════════════════════════════════════════════
// Transcript Item - Individual transcript entry with enter animation
// ═══════════════════════════════════════════════════════════════════════════

interface TranscriptItemProps {
  id: string;
  source: 'user' | 'system';
  speaker: string;
  text: string;
  index: number;
}

const TranscriptItem: React.FC<TranscriptItemProps> = ({ source, speaker, text, index }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      gsap.fromTo(
        ref.current,
        { opacity: 0, x: -8 },
        { opacity: 1, x: 0, duration: duration.fast, ease: ease.butter, delay: index * 0.02 }
      );
    }
  }, [index]);

  return (
    <div ref={ref} className={`transcript-item ${source}`}>
      <div className="transcript-icon">
        {source === 'user' ? <Mic size={14} /> : <User size={14} />}
      </div>
      <div className="transcript-content">
        <span className="transcript-source">{speaker}</span>
        <p>{text}</p>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Live Transcript Container
// ═══════════════════════════════════════════════════════════════════════════

export const LiveTranscript: React.FC = () => {
  const transcripts = useChatStore((state) => state.liveTranscripts);
  const { containerRef } = useAutoScroll(transcripts);

  if (!transcripts.length) {
    return (
      <div className="live-transcript-container empty">
        <div className="empty-message">Waiting for audio...</div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="live-transcript-container">
      <div className="transcript-list">
        {transcripts.map((t, i) => (
          <TranscriptItem
            key={t.id}
            id={t.id}
            source={t.source}
            speaker={t.speaker}
            text={t.text}
            index={i}
          />
        ))}
      </div>
    </div>
  );
};
