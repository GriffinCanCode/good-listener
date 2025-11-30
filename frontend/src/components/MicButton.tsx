import gsap from 'gsap';
import { Mic, MicOff } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { ease } from '../lib/animations';
import { useChatStore } from '../store/useChatStore';

export const MicButton = () => {
  const micEnabled = useChatStore((s) => s.micEnabled);
  const setMicEnabled = useChatStore((s) => s.setMicEnabled);
  const status = useChatStore((s) => s.status);

  const isConnecting = micEnabled && status === 'disconnected';
  const isActive = micEnabled && status === 'connected';

  const buttonRef = useRef<HTMLButtonElement>(null);
  const pulseRef = useRef<HTMLSpanElement>(null);
  const pulseAnimRef = useRef<gsap.core.Tween | null>(null);

  // Pulse ring animation for connecting state
  useEffect(() => {
    if (isConnecting && pulseRef.current) {
      pulseAnimRef.current = gsap.fromTo(
        pulseRef.current,
        { scale: 0.8, opacity: 0.6 },
        { scale: 1.8, opacity: 0, duration: 1.2, ease: ease.silk, repeat: -1 }
      );
    } else {
      pulseAnimRef.current?.kill();
    }
    return () => {
      pulseAnimRef.current?.kill();
    };
  }, [isConnecting]);

  const handlePress = () => {
    if (buttonRef.current) {
      gsap.to(buttonRef.current, { scale: 0.92, duration: 0.1, ease: ease.snap });
    }
  };

  const handleRelease = () => {
    if (buttonRef.current) {
      gsap.to(buttonRef.current, { scale: 1, duration: 0.2, ease: ease.bounce });
    }
  };

  return (
    <button
      ref={buttonRef}
      onClick={() => setMicEnabled(!micEnabled)}
      onMouseDown={handlePress}
      onMouseUp={handleRelease}
      onMouseLeave={handleRelease}
      className={`mic-btn ${isActive ? 'active' : ''} ${isConnecting ? 'connecting' : ''}`}
      title={micEnabled ? 'Mute microphone' : 'Unmute microphone'}
    >
      {isConnecting && <span ref={pulseRef} className="mic-pulse-ring" />}
      {micEnabled ? <Mic size={18} /> : <MicOff size={18} />}
    </button>
  );
};
