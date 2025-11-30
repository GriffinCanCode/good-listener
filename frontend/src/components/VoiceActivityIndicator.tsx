import gsap from 'gsap';
import { Mic, Volume2 } from 'lucide-react';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { duration, ease } from '../lib/animations';
import { useChatStore } from '../store/useChatStore';

const BAR_COUNT = 5;
const DECAY_MS = 150;

// ═══════════════════════════════════════════════════════════════════════════
// Audio Bar - Individual bar with spring-like animation
// ═══════════════════════════════════════════════════════════════════════════

interface AudioBarProps {
  probability: number;
  index: number;
  isActive: boolean;
  color: string;
}

const AudioBar: React.FC<AudioBarProps> = ({ probability, index, isActive, color }) => {
  const ref = useRef<HTMLDivElement>(null);
  const offset = (index - Math.floor(BAR_COUNT / 2)) * 0.12;
  const adjusted = Math.max(0, Math.min(1, probability + offset * (probability > 0.3 ? 1 : 0)));
  const targetHeight = isActive ? adjusted : 0;

  useEffect(() => {
    if (ref.current) {
      const scaleY = 0.3 + targetHeight * 0.7;
      const opacity = 0.3 + targetHeight * 0.7;
      gsap.to(ref.current, {
        scaleY,
        opacity,
        duration: 0.12,
        ease: 'power2.out',
      });
    }
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
};

// ═══════════════════════════════════════════════════════════════════════════
// Channel Indicator - User or System audio channel
// ═══════════════════════════════════════════════════════════════════════════

interface ChannelIndicatorProps {
  source: 'user' | 'system';
  probability: number;
  isSpeech: boolean;
  label: string;
  icon: React.ReactNode;
}

const ChannelIndicator: React.FC<ChannelIndicatorProps> = ({
  source,
  probability,
  isSpeech,
  label,
  icon,
}) => {
  const color = source === 'user' ? 'var(--accent-primary)' : 'var(--success)';
  const glowColor = source === 'user' ? 'var(--accent-glow)' : 'var(--success-glow)';

  const iconRef = useRef<HTMLDivElement>(null);
  const probRef = useRef<HTMLDivElement>(null);
  const breatheAnimRef = useRef<gsap.core.Tween | null>(null);
  const barHeights = useMemo(() => Array.from({ length: BAR_COUNT }, (_, i) => i), []);

  // Breathing icon animation when speaking
  useEffect(() => {
    if (isSpeech && iconRef.current) {
      breatheAnimRef.current = gsap.to(iconRef.current, {
        scale: 1.15,
        filter: `drop-shadow(0 0 6px ${glowColor})`,
        duration: 0.3,
        ease: ease.float,
        repeat: -1,
        yoyo: true,
      });
    } else {
      breatheAnimRef.current?.kill();
      if (iconRef.current) {
        gsap.to(iconRef.current, {
          scale: 1,
          filter: 'none',
          duration: 0.2,
          ease: ease.butter,
        });
      }
    }
    return () => {
      breatheAnimRef.current?.kill();
    };
  }, [isSpeech, glowColor]);

  // Probability display opacity
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
        {barHeights.map((i) => (
          <AudioBar key={i} index={i} probability={probability} isActive={isSpeech} color={color} />
        ))}
      </div>
      <div ref={probRef} className="vad-probability">
        {(probability * 100).toFixed(0)}%
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Voice Activity Indicator - Main component
// ═══════════════════════════════════════════════════════════════════════════

export const VoiceActivityIndicator: React.FC = () => {
  const vad = useChatStore((s) => s.vad);
  const status = useChatStore((s) => s.status);
  const ref = useRef<HTMLDivElement>(null);

  // Decay old values if no new data
  const [userProb, setUserProb] = useState(0);
  const [systemProb, setSystemProb] = useState(0);
  const [userSpeech, setUserSpeech] = useState(false);
  const [systemSpeech, setSystemSpeech] = useState(false);

  useEffect(() => {
    if (vad.user) {
      setUserProb(vad.user.probability);
      setUserSpeech(vad.user.isSpeech);
    }
    const decay = setTimeout(() => {
      if (!vad.user || Date.now() - vad.user.timestamp > DECAY_MS) {
        setUserProb((p) => p * 0.85);
        if (!vad.user?.isSpeech) setUserSpeech(false);
      }
    }, DECAY_MS);
    return () => clearTimeout(decay);
  }, [vad.user]);

  useEffect(() => {
    if (vad.system) {
      setSystemProb(vad.system.probability);
      setSystemSpeech(vad.system.isSpeech);
    }
    const decay = setTimeout(() => {
      if (!vad.system || Date.now() - vad.system.timestamp > DECAY_MS) {
        setSystemProb((p) => p * 0.85);
        if (!vad.system?.isSpeech) setSystemSpeech(false);
      }
    }, DECAY_MS);
    return () => clearTimeout(decay);
  }, [vad.system]);

  // Enter animation
  useEffect(() => {
    if (ref.current && status === 'connected') {
      gsap.fromTo(
        ref.current,
        { opacity: 0, y: 10 },
        { opacity: 1, y: 0, duration: duration.normal, ease: ease.butter }
      );
    }
  }, [status]);

  if (status !== 'connected') return null;

  return (
    <div ref={ref} className="vad-indicator">
      <ChannelIndicator
        source="user"
        probability={userProb}
        isSpeech={userSpeech}
        label="You"
        icon={<Mic size={14} />}
      />
      <div className="vad-divider" />
      <ChannelIndicator
        source="system"
        probability={systemProb}
        isSpeech={systemSpeech}
        label="System"
        icon={<Volume2 size={14} />}
      />
    </div>
  );
};
