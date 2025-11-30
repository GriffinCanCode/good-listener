import { motion, useSpring, useTransform } from 'framer-motion';
import { Mic, Volume2 } from 'lucide-react';
import React, { useEffect, useMemo } from 'react';
import { useChatStore } from '../store/useChatStore';

const BAR_COUNT = 5;
const DECAY_MS = 150;

interface AudioBarProps {
  probability: number;
  index: number;
  isActive: boolean;
  color: string;
}

const AudioBar: React.FC<AudioBarProps> = ({ probability, index, isActive, color }) => {
  // Each bar has slightly different response curve for organic feel
  const offset = (index - Math.floor(BAR_COUNT / 2)) * 0.12;
  const adjusted = Math.max(0, Math.min(1, probability + offset * (probability > 0.3 ? 1 : 0)));

  const springConfig = { damping: 15, stiffness: 300, mass: 0.5 };
  const height = useSpring(isActive ? adjusted : 0, springConfig);
  const scale = useTransform(height, [0, 1], [0.3, 1]);
  const opacity = useTransform(height, [0, 0.3, 1], [0.3, 0.6, 1]);

  return (
    <motion.div
      className="vad-bar"
      style={{
        scaleY: scale,
        opacity,
        backgroundColor: color,
        boxShadow: isActive ? `0 0 8px ${color}40` : 'none',
      }}
    />
  );
};

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

  // Generate bar heights with some randomization for organic look
  const barHeights = useMemo(() => Array.from({ length: BAR_COUNT }, (_, i) => i), []);

  return (
    <div className={`vad-channel ${source} ${isSpeech ? 'speaking' : ''}`}>
      <div className="vad-channel-header">
        <motion.div
          className="vad-icon"
          animate={{
            scale: isSpeech ? [1, 1.15, 1] : 1,
            filter: isSpeech ? `drop-shadow(0 0 6px ${glowColor})` : 'none',
          }}
          transition={{ duration: 0.3, repeat: isSpeech ? Infinity : 0, repeatType: 'reverse' }}
          style={{ color }}
        >
          {icon}
        </motion.div>
        <span className="vad-label">{label}</span>
      </div>
      <div className="vad-bars">
        {barHeights.map((i) => (
          <AudioBar key={i} index={i} probability={probability} isActive={isSpeech} color={color} />
        ))}
      </div>
      <motion.div className="vad-probability" animate={{ opacity: probability > 0 ? 1 : 0.4 }}>
        {(probability * 100).toFixed(0)}%
      </motion.div>
    </div>
  );
};

export const VoiceActivityIndicator: React.FC = () => {
  const vad = useChatStore((s) => s.vad);
  const status = useChatStore((s) => s.status);

  // Decay old values if no new data
  const [userProb, setUserProb] = React.useState(0);
  const [systemProb, setSystemProb] = React.useState(0);
  const [userSpeech, setUserSpeech] = React.useState(false);
  const [systemSpeech, setSystemSpeech] = React.useState(false);

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

  if (status !== 'connected') return null;

  return (
    <motion.div
      className="vad-indicator"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
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
    </motion.div>
  );
};
