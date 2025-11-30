/**
 * GSAP Presence Hook - Handles mount/unmount animations
 * Replaces framer-motion's AnimatePresence with GSAP-powered transitions
 */

import gsap from 'gsap';
import { useCallback, useEffect, useRef, useState } from 'react';
import { duration, ease, type PresenceAnimation, presenceAnimations } from '../lib/animations';

// ═══════════════════════════════════════════════════════════════════════════
// useGsapPresence - For single conditional elements
// ═══════════════════════════════════════════════════════════════════════════

interface UseGsapPresenceOptions {
  animation?: keyof typeof presenceAnimations | PresenceAnimation;
  onExitComplete?: () => void;
}

export const useGsapPresence = (isVisible: boolean, options: UseGsapPresenceOptions = {}) => {
  const { animation = 'fade', onExitComplete } = options;
  const [shouldRender, setShouldRender] = useState(isVisible);
  const ref = useRef<HTMLDivElement>(null);
  const isFirstRender = useRef(true);

  const anim = typeof animation === 'string' ? presenceAnimations[animation] : animation;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (isVisible) {
      setShouldRender(true);
      requestAnimationFrame(() => {
        if (ref.current) {
          gsap.set(ref.current, { opacity: 0 });
          anim.enter(ref.current);
        }
      });
    } else if (!isFirstRender.current) {
      anim.exit(el, () => {
        setShouldRender(false);
        onExitComplete?.();
      });
    }

    isFirstRender.current = false;
  }, [isVisible, anim, onExitComplete]);

  // Initial state setup
  useEffect(() => {
    if (ref.current && isVisible) {
      anim.enter(ref.current);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only run on mount
  }, []);

  return { ref, shouldRender };
};

// ═══════════════════════════════════════════════════════════════════════════
// useGsapListPresence - For animated lists with staggered items
// ═══════════════════════════════════════════════════════════════════════════

interface UseGsapListPresenceOptions<T> {
  getKey: (item: T) => string | number;
  enterAnimation?: (el: Element, index: number) => gsap.core.Tween | gsap.core.Timeline;
  exitAnimation?: (el: Element, onComplete: () => void) => gsap.core.Tween | gsap.core.Timeline;
  staggerDelay?: number;
}

export const useGsapListPresence = <T>(items: T[], options: UseGsapListPresenceOptions<T>) => {
  const { getKey, staggerDelay = 0.05 } = options;
  const [renderedItems, setRenderedItems] = useState<T[]>(items);
  const exitingRefs = useRef<Map<string | number, Element>>(new Map());
  const itemRefs = useRef<Map<string | number, Element>>(new Map());

  const enterAnimation =
    options.enterAnimation ??
    ((el: Element, index: number) =>
      gsap.fromTo(
        el,
        { opacity: 0, y: 12 },
        {
          opacity: 1,
          y: 0,
          duration: duration.normal,
          ease: ease.butter,
          delay: index * staggerDelay,
        }
      ));

  const exitAnimation =
    options.exitAnimation ??
    ((el: Element, onComplete: () => void) =>
      gsap.to(el, { opacity: 0, x: -6, duration: duration.fast, ease: ease.sharp, onComplete }));

  useEffect(() => {
    const currentKeys = new Set(items.map(getKey));
    const renderedKeys = new Set(renderedItems.map(getKey));

    // Find items to add
    const newItems = items.filter((item) => !renderedKeys.has(getKey(item)));

    // Find items to remove
    const removingItems = renderedItems.filter((item) => !currentKeys.has(getKey(item)));

    if (removingItems.length > 0) {
      let completed = 0;
      removingItems.forEach((item) => {
        const key = getKey(item);
        const el = itemRefs.current.get(key);
        if (el) {
          exitingRefs.current.set(key, el);
          exitAnimation(el, () => {
            completed++;
            exitingRefs.current.delete(key);
            if (completed === removingItems.length) {
              setRenderedItems(items);
            }
          });
        }
      });
    } else {
      setRenderedItems(items);
    }

    // Animate in new items after a frame
    if (newItems.length > 0) {
      requestAnimationFrame(() => {
        newItems.forEach((item, i) => {
          const el = itemRefs.current.get(getKey(item));
          if (el) {
            gsap.set(el, { opacity: 0 });
            enterAnimation(el, i);
          }
        });
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- we want to control when this updates
  }, [items, getKey, enterAnimation, exitAnimation]);

  const setRef = useCallback(
    (key: string | number) => (el: Element | null) => {
      if (el) itemRefs.current.set(key, el);
      else itemRefs.current.delete(key);
    },
    []
  );

  return {
    renderedItems,
    setRef,
    isExiting: (key: string | number) => exitingRefs.current.has(key),
  };
};

// ═══════════════════════════════════════════════════════════════════════════
// useGsapAnimation - For simple enter animations on mount
// ═══════════════════════════════════════════════════════════════════════════

interface UseGsapAnimationOptions {
  animation?: (el: Element) => gsap.core.Tween | gsap.core.Timeline;
}

export const useGsapAnimation = <T extends HTMLElement>(options: UseGsapAnimationOptions = {}) => {
  const ref = useRef<T>(null);
  const { animation } = options;

  const defaultAnimation = useCallback(
    (el: Element) =>
      gsap.fromTo(
        el,
        { opacity: 0, y: 8 },
        { opacity: 1, y: 0, duration: duration.normal, ease: ease.butter }
      ),
    []
  );

  useEffect(() => {
    if (ref.current) {
      (animation ?? defaultAnimation)(ref.current);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only run on mount
  }, []);

  return ref;
};

// ═══════════════════════════════════════════════════════════════════════════
// useGsapSpring - GSAP spring-like value
// ═══════════════════════════════════════════════════════════════════════════

interface SpringConfig {
  stiffness?: number;
  damping?: number;
}

export const useGsapSpring = (targetValue: number, config: SpringConfig = {}) => {
  const { stiffness = 300, damping = 15 } = config;
  const [value, setValue] = useState(targetValue);
  const tweenRef = useRef<gsap.core.Tween | null>(null);
  const valueRef = useRef({ v: targetValue });

  useEffect(() => {
    if (tweenRef.current) tweenRef.current.kill();

    // Convert spring physics to duration (approximation)
    const springDuration = Math.sqrt(1 / stiffness) * damping * 0.08;

    tweenRef.current = gsap.to(valueRef.current, {
      v: targetValue,
      duration: springDuration,
      ease: 'power2.out',
      onUpdate: () => setValue(valueRef.current.v),
    });

    return () => {
      tweenRef.current?.kill();
    };
  }, [targetValue, stiffness, damping]);

  return value;
};

// ═══════════════════════════════════════════════════════════════════════════
// useButtonPress - Press/release animations for buttons
// ═══════════════════════════════════════════════════════════════════════════

export const useButtonPress = <T extends HTMLElement>() => {
  const ref = useRef<T>(null);

  const handlers = {
    onMouseDown: () => {
      if (ref.current) {
        gsap.to(ref.current, { scale: 0.92, duration: 0.1, ease: ease.snap });
      }
    },
    onMouseUp: () => {
      if (ref.current) {
        gsap.to(ref.current, { scale: 1, duration: 0.2, ease: ease.bounce });
      }
    },
    onMouseLeave: () => {
      if (ref.current) {
        gsap.to(ref.current, { scale: 1, duration: 0.2, ease: ease.butter });
      }
    },
  };

  return { ref, handlers };
};
