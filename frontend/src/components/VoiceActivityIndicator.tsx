import { Mic, Volume2 } from 'lucide-react';
import React, { memo, useEffect, useState } from 'react';
import { useDebouncedCallback } from '../hooks/useDebounce';
import { useChatStore } from '../store/useChatStore';

const BAR_COUNT = 5;
const DECAY_MS = 150;

const AudioBar = memo<{ probability: number; index: number; isActive: boolean; color: string }>(
  ({ probability, index, isActive, color }) => {
    const offset = (index - Math.floor(BAR_COUNT / 2)) * 0.12;
    const scale =
      0.3 +
      (isActive
        ? Math.max(0, Math.min(1, probability + offset * (probability > 0.3 ? 1 : 0)))
        : 0) *
        0.7;

    return (
      <div
        className="vad-bar"
        style={{
          backgroundColor: color,
          boxShadow: isActive ? `0 0 8px ${color}40` : 'none',
          transformOrigin: 'center',
          transform: `scaleY(${scale})`,
          opacity: scale,
        }}
      />
    );
  }
);
AudioBar.displayName = 'AudioBar';

const ChannelIndicator = memo<{
  source: 'user' | 'system';
  probability: number;
  isSpeech: boolean;
  label: string;
  icon: React.ReactNode;
}>(({ source, probability, isSpeech, label, icon }) => {
  const color = source === 'user' ? 'var(--accent-primary)' : 'var(--success)';

  return (
    <div
      className={`vad-channel ${source} ${isSpeech ? 'speaking' : ''}`}
      style={
        {
          '--glow-color': source === 'user' ? 'var(--accent-glow)' : 'var(--success-glow)',
        } as React.CSSProperties
      }
    >
      <div className="vad-channel-header">
        <div className="vad-icon" style={{ color }}>
          {icon}
        </div>
        <span className="vad-label">{label}</span>
      </div>
      <div className="vad-bars">
        {Array.from({ length: BAR_COUNT }).map((_, i) => (
          <AudioBar key={i} index={i} probability={probability} isActive={isSpeech} color={color} />
        ))}
      </div>
      <div className="vad-probability" style={{ opacity: probability > 0 ? 1 : 0.4 }}>
        {(probability * 100).toFixed(0)}%
      </div>
    </div>
  );
});
ChannelIndicator.displayName = 'ChannelIndicator';

export const VoiceActivityIndicator = memo(() => {
  const { vad, status } = useChatStore();

  const useVadDecay = (source: 'user' | 'system') => {
    const [state, setState] = useState({ prob: 0, speech: false });
    const data = vad[source];

    const decay = useDebouncedCallback(() => {
      if (!data || Date.now() - data.timestamp > DECAY_MS) {
        setState((s) => ({ prob: s.prob * 0.85, speech: data?.isSpeech ? s.speech : false }));
      }
    }, DECAY_MS);

    useEffect(() => {
      if (data) setState({ prob: data.probability, speech: data.isSpeech });
      decay();
      return () => decay.cancel();
    }, [data, decay]);

    return state;
  };

  const user = useVadDecay('user');
  const system = useVadDecay('system');

  if (status !== 'connected') return null;

  return (
    <div className="vad-wrapper">
      <div className="vad-indicator">
        <ChannelIndicator
          source="user"
          probability={user.prob}
          isSpeech={user.speech}
          label="You"
          icon={<Mic size={12} />}
        />
        <div className="vad-divider" />
        <ChannelIndicator
          source="system"
          probability={system.prob}
          isSpeech={system.speech}
          label="System"
          icon={<Volume2 size={12} />}
        />
      </div>
    </div>
  );
});
VoiceActivityIndicator.displayName = 'VoiceActivityIndicator';
