import gsap from 'gsap';
import { Activity, Mic, User } from 'lucide-react';
import React, { memo, useEffect, useRef } from 'react';
import { useAutoScroll } from '../hooks/useAutoScroll';
import { useVirtualList } from '../hooks/useVirtualList';
import { duration, ease } from '../lib/animations';
import { useChatStore } from '../store/useChatStore';
import './LiveTranscript.css';
import { VoiceActivityIndicator } from './VoiceActivityIndicator';

interface TranscriptItemProps {
  source: 'user' | 'system';
  speaker: string;
  text: string;
  index: number;
  style?: React.CSSProperties;
  measureRef?: (node: HTMLDivElement | null) => void;
}

const TranscriptItem = memo(
  ({ source, speaker, text, index, style, measureRef }: TranscriptItemProps) => {
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
      if (!ref.current) return;
      if (measureRef) measureRef(ref.current);

      // Only animate if this is a new item (high index) or initial load
      // To avoid re-animating on scroll
      gsap.fromTo(
        ref.current,
        { opacity: 0, x: -4 },
        { opacity: 1, x: 0, duration: duration.fast, ease: ease.butter, delay: 0.05 }
      );
    }, [measureRef]);

    return (
      <div ref={ref} className={`transcript-item ${source}`} style={style} data-index={index}>
        <div className="transcript-icon">
          {source === 'user' ? <Mic size={12} /> : <User size={12} />}
        </div>
        <div className="transcript-content">
          <span className="transcript-source">{speaker}</span>
          <p>{text}</p>
        </div>
      </div>
    );
  }
);
TranscriptItem.displayName = 'TranscriptItem';

const TranscriptList = memo(() => {
  const transcripts = useChatStore((state) => state.liveTranscripts);
  const { containerRef } = useAutoScroll(transcripts);

  const { virtualizer, items } = useVirtualList({
    items: transcripts,
    scrollRef: containerRef,
    estimateSize: () => 80, // Estimate height of an item
    overscan: 5,
  });

  if (!transcripts.length) {
    return (
      <div className="live-transcript-container empty">
        <div className="empty-message">Waiting for audio...</div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="live-transcript-container">
      <div
        className="transcript-list-inner"
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {items.map((virtualItem) => {
          const t = transcripts[virtualItem.index];
          if (!t) return null;
          return (
            <TranscriptItem
              key={t.id}
              source={t.source}
              speaker={t.speaker}
              text={t.text}
              index={virtualItem.index}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualItem.start}px)`,
              }}
              measureRef={virtualizer.measureElement}
            />
          );
        })}
      </div>
    </div>
  );
});
TranscriptList.displayName = 'TranscriptList';

export const LiveTranscript = memo(
  React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>((props, ref) => {
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
  })
);
LiveTranscript.displayName = 'LiveTranscript';
