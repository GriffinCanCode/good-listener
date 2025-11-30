import gsap from 'gsap';
import { Mic, Volume2 } from 'lucide-react';
import React, { memo, useEffect, useRef, useState } from 'react';
import { useDebouncedCallback } from '../hooks/useDebounce';
import { breathe, duration, ease } from '../lib/animations';
import { useChatStore } from '../store/useChatStore';

const BAR_COUNT = 5;
const DECAY_MS = 150;

const AudioBar = memo<{
  probability: number;
  index: number;
  isActive: boolean;
  color: string;
}>(({ probability, index, isActive, color }) => {
  const ref = useRef<HTMLDivElement>(null);
  // Pithier calculation
  const offset = (index - Math.floor(BAR_COUNT / 2)) * 0.12;
  const adjusted = Math.max(0, Math.min(1, probability + offset * (probability > 0.3 ? 1 : 0)));
  const targetHeight = isActive ? adjusted : 0;

  useEffect(() => {
    if (!ref.current) return;
    gsap.to(ref.current, {
      scaleY: 0.3 + targetHeight * 0.7,
      opacity: 0.3 + targetHeight * 0.7,
      duration: 0.12,
      ease: 'power2.out',
    });
  }, [targetHeight]);

  return (
    <div
      ref={ref}
      className="vad-bar"
      style={{
        backgroundColor: color,
        boxShadow: isActive ? `0 0 8px ${color}40` : 'none',
        transformOrigin: 'center',
      }}
    />
  );
});
AudioBar.displayName = 'AudioBar';

const ChannelIndicator = memo<{
  source: 'user' | 'system';
  probability: number;
  isSpeech: boolean;
  label: string;
  icon: React.ReactNode;
}>(({ source, probability, isSpeech, label, icon }) => {
  const color = source === 'user' ? 'var(--accent-primary)' : 'var(--success)';
  const glowColor = source === 'user' ? 'var(--accent-glow)' : 'var(--success-glow)';
  const iconRef = useRef<HTMLDivElement>(null);
  const probRef = useRef<HTMLDivElement>(null);
  const breatheAnimRef = useRef<gsap.core.Tween | null>(null);

  useEffect(() => {
    if (isSpeech && iconRef.current) {
      breatheAnimRef.current = breathe(iconRef.current, { glowColor });
    } else {
      breatheAnimRef.current?.kill();
      if (iconRef.current) {
        gsap.to(iconRef.current, { scale: 1, filter: 'none', duration: 0.2, ease: ease.butter });
      }
    }
    return () => {
      breatheAnimRef.current?.kill();
    };
  }, [isSpeech, glowColor]);

  useEffect(() => {
    if (probRef.current) {
      gsap.to(probRef.current, {
        opacity: probability > 0 ? 1 : 0.4,
        duration: 0.15,
        ease: ease.silk,
      });
    }
  }, [probability]);

  return (
    <div className={`vad-channel ${source} ${isSpeech ? 'speaking' : ''}`}>
      <div className="vad-channel-header">
        <div ref={iconRef} className="vad-icon" style={{ color }}>
          {icon}
        </div>
        <span className="vad-label">{label}</span>
      </div>
      <div className="vad-bars">
        {Array.from({ length: BAR_COUNT }).map((_, i) => (
          <AudioBar key={i} index={i} probability={probability} isActive={isSpeech} color={color} />
        ))}
      </div>
      <div ref={probRef} className="vad-probability">
        {(probability * 100).toFixed(0)}%
      </div>
    </div>
  );
});
ChannelIndicator.displayName = 'ChannelIndicator';

export const VoiceActivityIndicator = memo(() => {
  const { vad, status } = useChatStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const isConnected = status === 'connected';

  const useVadDecay = (source: 'user' | 'system') => {
    const [prob, setProb] = useState(0);
    const [speech, setSpeech] = useState(false);
    const data = vad[source];

    const decay = useDebouncedCallback(() => {
      if (!data || Date.now() - data.timestamp > DECAY_MS) {
        setProb((p) => p * 0.85);
        if (!data?.isSpeech) setSpeech(false);
      }
    }, DECAY_MS);

    useEffect(() => {
      if (data) {
        setProb(data.probability);
        setSpeech(data.isSpeech);
      }
      decay();
      return () => decay.cancel();
    }, [data, decay]);

    return { prob, speech };
  };

  const user = useVadDecay('user');
  const system = useVadDecay('system');

  useEffect(() => {
    if (containerRef.current && !isConnected) {
      gsap.set(containerRef.current, { opacity: 0, y: -10 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const hideContainer = useDebouncedCallback(() => {
    if (containerRef.current) {
      gsap.to(containerRef.current, {
        opacity: 0,
        y: -10,
        duration: duration.fast,
        ease: ease.butter,
      });
    }
  }, 1000);

  useEffect(() => {
    if (!containerRef.current) return;

    if (isConnected) {
      hideContainer.cancel();
      gsap.to(containerRef.current, {
        opacity: 1,
        y: 0,
        duration: duration.normal,
        ease: ease.butter,
      });
    } else {
      hideContainer();
    }
  }, [isConnected, hideContainer]);

  return (
    <div ref={containerRef} className="vad-wrapper">
      <div className="vad-indicator">
        <ChannelIndicator
          source="user"
          probability={user.prob}
          isSpeech={user.speech}
          label="You"
          icon={<Mic size={14} />}
        />
        <div className="vad-divider" />
        <ChannelIndicator
          source="system"
          probability={system.prob}
          isSpeech={system.speech}
          label="System"
          icon={<Volume2 size={14} />}
        />
      </div>
    </div>
  );
});
VoiceActivityIndicator.displayName = 'VoiceActivityIndicator';
