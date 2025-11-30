/**
 * Presence - GSAP-powered AnimatePresence replacement
 * Handles smooth enter/exit animations for conditional renders
 */

import gsap from 'gsap';
import React, { Children, cloneElement, isValidElement, useEffect, useRef, useState } from 'react';
import { duration, ease, presenceAnimations, type PresenceAnimation } from '../lib/animations';

type AnimationPreset = keyof typeof presenceAnimations;

interface PresenceProps {
  children: React.ReactNode;
  animation?: AnimationPreset | PresenceAnimation;
}

interface ChildState {
  key: string;
  element: React.ReactElement;
  isExiting: boolean;
}

const getChildKey = (child: React.ReactElement): string => {
  const k = child.key as string | number | null;
  if (typeof k === 'string') return k;
  if (typeof k === 'number') return k.toString();
  return 'single';
};

/** Declarative presence wrapper - handles enter/exit animations automatically */
export const Presence: React.FC<PresenceProps> = ({ children, animation = 'fade' }) => {
  const [childStates, setChildStates] = useState<ChildState[]>([]);
  const refs = useRef<Map<string, HTMLElement>>(new Map());
  const anim = typeof animation === 'string' ? presenceAnimations[animation] : animation;

  useEffect(() => {
    const newChildren = Children.toArray(children).filter(isValidElement) as React.ReactElement[];
    const newKeys = new Set(newChildren.map(getChildKey));
    const currentKeys = new Set(childStates.filter((s) => !s.isExiting).map((s) => s.key));

    setChildStates((prev) => {
      const result: ChildState[] = [];

      // Mark exiting children
      prev.forEach((state) => {
        if (!newKeys.has(state.key) && !state.isExiting) {
          result.push({ ...state, isExiting: true });
          const el = refs.current.get(state.key);
          if (el) {
            anim.exit(el, () => {
              setChildStates((p) => p.filter((s) => s.key !== state.key));
            });
          }
        } else if (!state.isExiting && newKeys.has(state.key)) {
          // Update existing element
          const updated = newChildren.find((c) => getChildKey(c) === state.key);
          result.push({ ...state, element: updated ?? state.element });
        } else if (state.isExiting) {
          result.push(state);
        }
      });

      // Add new children
      newChildren.forEach((child) => {
        const key = getChildKey(child);
        if (!currentKeys.has(key) && !prev.some((s) => s.key === key)) {
          result.push({ key, element: child, isExiting: false });
        }
      });

      return result;
    });
  }, [children, anim, childStates]);

  // Animate entering elements
  useEffect(() => {
    childStates.forEach((state) => {
      if (!state.isExiting) {
        const el = refs.current.get(state.key);
        if (el?.style.opacity === '0') {
          anim.enter(el);
        }
      }
    });
  }, [childStates, anim]);

  return (
    <>
      {childStates.map((state) =>
        cloneElement(state.element, {
          ref: (el: HTMLElement | null) => {
            if (el) {
              refs.current.set(state.key, el);
              gsap.set(el, { opacity: 0 });
            } else {
              refs.current.delete(state.key);
            }
          },
          key: state.key,
          style: {
            ...((state.element.props as Record<string, unknown>)['style'] as
              | React.CSSProperties
              | undefined),
            pointerEvents: state.isExiting ? 'none' : undefined,
          },
        })
      )}
    </>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// AnimatedDiv - Pre-animated div with built-in enter/exit
// ═══════════════════════════════════════════════════════════════════════════

interface AnimatedDivProps extends React.HTMLAttributes<HTMLDivElement> {
  enter?: { opacity?: number; y?: number; x?: number; scale?: number };
  animate?: { opacity?: number; y?: number; x?: number; scale?: number };
  animDuration?: number;
  easing?: string;
}

export const AnimatedDiv = React.forwardRef<HTMLDivElement, AnimatedDivProps>(
  (
    { enter, animate, animDuration = duration.normal, easing = ease.butter, children, ...props },
    forwardedRef
  ) => {
    const innerRef = useRef<HTMLDivElement>(null);
    const ref = forwardedRef ? (forwardedRef as React.RefObject<HTMLDivElement>) : innerRef;

    useEffect(() => {
      const el = ref.current;
      if (!el) return;

      if (enter) {
        gsap.set(el, enter);
        gsap.to(el, { ...animate, duration: animDuration, ease: easing });
      } else if (animate) {
        gsap.to(el, { ...animate, duration: animDuration, ease: easing });
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps -- only animate on mount
    }, []);

    return (
      <div ref={ref} {...props}>
        {children}
      </div>
    );
  }
);

AnimatedDiv.displayName = 'AnimatedDiv';

// ═══════════════════════════════════════════════════════════════════════════
// AnimatedButton - Button with built-in press animation
// ═══════════════════════════════════════════════════════════════════════════

interface AnimatedButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  scale?: number;
}

export const AnimatedButton = React.forwardRef<HTMLButtonElement, AnimatedButtonProps>(
  ({ scale = 0.92, children, onMouseDown, onMouseUp, onMouseLeave, ...props }, forwardedRef) => {
    const innerRef = useRef<HTMLButtonElement>(null);
    const ref = forwardedRef ? (forwardedRef as React.RefObject<HTMLButtonElement>) : innerRef;

    const handleMouseDown = (e: React.MouseEvent<HTMLButtonElement>) => {
      const el = ref.current;
      if (el) gsap.to(el, { scale, duration: 0.1, ease: ease.snap });
      onMouseDown?.(e);
    };

    const handleMouseUp = (e: React.MouseEvent<HTMLButtonElement>) => {
      const el = ref.current;
      if (el) gsap.to(el, { scale: 1, duration: 0.2, ease: ease.bounce });
      onMouseUp?.(e);
    };

    const handleMouseLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
      const el = ref.current;
      if (el) gsap.to(el, { scale: 1, duration: 0.15, ease: ease.butter });
      onMouseLeave?.(e);
    };

    return (
      <button
        ref={ref}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        {...props}
      >
        {children}
      </button>
    );
  }
);

AnimatedButton.displayName = 'AnimatedButton';
