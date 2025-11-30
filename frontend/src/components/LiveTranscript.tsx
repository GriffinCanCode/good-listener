import gsap from 'gsap';
import { Activity, Mic, User } from 'lucide-react';
import React, { useEffect, useRef } from 'react';
import { useAutoScroll } from '../hooks/useAutoScroll';
import { duration, ease } from '../lib/animations';
import { useChatStore } from '../store/useChatStore';
import './LiveTranscript.css';
import { VoiceActivityIndicator } from './VoiceActivityIndicator';

interface TranscriptItemProps {
  source: 'user' | 'system';
  speaker: string;
  text: string;
  index: number;
}

const TranscriptItem = ({ source, speaker, text, index }: TranscriptItemProps) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    gsap.fromTo(
      ref.current,
      { opacity: 0, x: -4 },
      { opacity: 1, x: 0, duration: duration.fast, ease: ease.butter, delay: index * 0.02 }
    );
  }, [index]);

  return (
    <div ref={ref} className={`transcript-item ${source}`}>
      <div className="transcript-icon">
        {source === 'user' ? <Mic size={12} /> : <User size={12} />}
      </div>
      <div className="transcript-content">
        <span className="transcript-source">{speaker}</span>
        <p>{text}</p>
      </div>
    </div>
  );
};

const TranscriptList = () => {
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

export const LiveTranscript = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>((props, ref) => {
  return (
    <div ref={ref} className="live-transcript-wrapper" {...props}>
      <div className="transcript-header">
        <span>Live Transcript</span>
        <Activity size={14} style={{ opacity: 0.5 }} />
      </div>
      <VoiceActivityIndicator />
      <TranscriptList />
    </div>
  );
});

LiveTranscript.displayName = 'LiveTranscript';
