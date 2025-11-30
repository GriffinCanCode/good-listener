/**
 * Presence Component
 * Declarative wrapper for GSAP animations.
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

const getChildKey = (child: React.ReactElement): string =>
  child.key != null ? String(child.key as React.Key) : 'single';

export const Presence: React.FC<PresenceProps> = ({ children, animation = 'fade' }) => {
  const [childStates, setChildStates] = useState<ChildState[]>([]);
  const refs = useRef<Map<string, HTMLElement>>(new Map());
  const anim = typeof animation === 'string' ? presenceAnimations[animation] : animation;

  useEffect(() => {
    const newChildren = Children.toArray(children).filter(isValidElement) as React.ReactElement[];
    const newKeys = new Set(newChildren.map(getChildKey));

    setChildStates((prev) => {
      const next: ChildState[] = [];
      const currentKeys = new Set(prev.filter((s) => !s.isExiting).map((s) => s.key));

      // Handle Exits
      prev.forEach((state) => {
        if (!newKeys.has(state.key) && !state.isExiting) {
          const el = refs.current.get(state.key);
          if (el && anim)
            anim.exit(el, () => setChildStates((p) => p.filter((s) => s.key !== state.key)));
          next.push({ ...state, isExiting: true });
        } else if (newKeys.has(state.key) && !state.isExiting) {
          // Update existing
          const updated = newChildren.find((c) => getChildKey(c) === state.key);
          next.push({ ...state, element: updated ?? state.element });
        } else if (state.isExiting) {
          next.push(state);
        }
      });

      // Handle Entries
      newChildren.forEach((child) => {
        const key = getChildKey(child);
        if (!currentKeys.has(key) && !prev.some((s) => s.key === key)) {
          next.push({ key, element: child, isExiting: false });
        }
      });

      return next;
    });
  }, [children, anim]);

  // Animate Entries
  useEffect(() => {
    childStates
      .filter((s) => !s.isExiting)
      .forEach((state) => {
        const el = refs.current.get(state.key);
        // Only animate if opacity is 0 (set by ref callback)
        if (el && anim && gsap.getProperty(el, 'opacity') === 0) anim.enter(el);
      });
  }, [childStates, anim]);

  return (
    <>
      {childStates.map(({ key, element, isExiting }) =>
        cloneElement(element, {
          key,
          ref: (el: HTMLElement | null) => {
            if (el) {
              refs.current.set(key, el);
              if (!isExiting) gsap.set(el, { opacity: 0 });
            } else {
              refs.current.delete(key);
            }
          },
          style: {
            ...(element.props as React.HTMLAttributes<HTMLElement>).style,
            pointerEvents: isExiting ? 'none' : undefined,
          },
        })
      )}
    </>
  );
};

interface AnimatedDivProps extends React.HTMLAttributes<HTMLDivElement> {
  enter?: gsap.TweenVars;
  animate?: gsap.TweenVars;
  animDuration?: number;
  easing?: string;
}

export const AnimatedDiv = React.forwardRef<HTMLDivElement, AnimatedDivProps>(
  (
    { enter, animate, animDuration = duration.normal, easing = ease.butter, children, ...props },
    ref
  ) => {
    const localRef = useRef<HTMLDivElement>(null);
    const resolvedRef = (ref ?? localRef) as React.RefObject<HTMLDivElement>;

    useEffect(() => {
      if (!resolvedRef.current) return;
      if (enter) gsap.set(resolvedRef.current, enter);
      if (animate || enter)
        gsap.to(resolvedRef.current, { ...animate, duration: animDuration, ease: easing });
    }, [enter, animate, animDuration, easing, resolvedRef]);

    return (
      <div ref={resolvedRef} {...props}>
        {children}
      </div>
    );
  }
);
AnimatedDiv.displayName = 'AnimatedDiv';

interface AnimatedButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  scale?: number;
}

export const AnimatedButton = React.forwardRef<HTMLButtonElement, AnimatedButtonProps>(
  ({ scale = 0.92, children, onMouseDown, onMouseUp, onMouseLeave, ...props }, ref) => {
    const localRef = useRef<HTMLButtonElement>(null);
    const resolvedRef = (ref ?? localRef) as React.RefObject<HTMLButtonElement>;

    const animateBtn = (s: number, d: number, e: string) =>
      resolvedRef.current && gsap.to(resolvedRef.current, { scale: s, duration: d, ease: e });

    return (
      <button
        ref={resolvedRef}
        onMouseDown={(e) => {
          animateBtn(scale, 0.1, ease.snap);
          onMouseDown?.(e);
        }}
        onMouseUp={(e) => {
          animateBtn(1, 0.2, ease.bounce);
          onMouseUp?.(e);
        }}
        onMouseLeave={(e) => {
          animateBtn(1, 0.15, ease.butter);
          onMouseLeave?.(e);
        }}
        {...props}
      >
        {children}
      </button>
    );
  }
);
AnimatedButton.displayName = 'AnimatedButton';
