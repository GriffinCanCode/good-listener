/**
 * GSAP Presence Hook
 * Succinct replacement for AnimatePresence logic.
 */

import gsap from 'gsap';
import { useCallback, useEffect, useRef, useState } from 'react';
import { duration, ease, presenceAnimations, type PresenceAnimation } from '../lib/animations';

interface UseGsapPresenceOptions {
  animation?: keyof typeof presenceAnimations | PresenceAnimation;
  onExitComplete?: () => void;
}

export const useGsapPresence = (
  isVisible: boolean,
  { animation = 'fade', onExitComplete }: UseGsapPresenceOptions = {}
) => {
  const [shouldRender, setShouldRender] = useState(isVisible);
  const ref = useRef<HTMLDivElement>(null);
  const firstRender = useRef(true);
  const anim = typeof animation === 'string' ? presenceAnimations[animation] : animation;

  useEffect(() => {
    const el = ref.current;
    if (!el || !anim) return;

    if (isVisible) {
      setShouldRender(true);
      gsap.set(el, { opacity: 0 }); // Ensure hidden initially
      requestAnimationFrame(() => {
        anim.enter(el);
      });
    } else if (!firstRender.current) {
      anim.exit(el, () => {
        setShouldRender(false);
        onExitComplete?.();
      });
    }
    firstRender.current = false;
  }, [isVisible, anim, onExitComplete]);

  // Initial mount animation check
  useEffect(() => {
    if (isVisible && ref.current && anim) anim.enter(ref.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { ref, shouldRender };
};

interface UseGsapListPresenceOptions<T> {
  getKey: (item: T) => string | number;
  enterAnimation?: (el: Element, index: number) => gsap.core.Tween | gsap.core.Timeline;
  exitAnimation?: (el: Element, onComplete: () => void) => gsap.core.Tween | gsap.core.Timeline;
  staggerDelay?: number;
}

export const useGsapListPresence = <T>(
  items: T[],
  { getKey, enterAnimation, exitAnimation, staggerDelay = 0.05 }: UseGsapListPresenceOptions<T>
) => {
  const [renderedItems, setRenderedItems] = useState<T[]>(items);
  const itemRefs = useRef<Map<string | number, Element>>(new Map());
  const exitingRefs = useRef<Set<string | number>>(new Set());

  const enter = useCallback(
    (el: Element, i: number) => {
      if (enterAnimation) return enterAnimation(el, i);
      return gsap.fromTo(
        el,
        { opacity: 0, y: 12 },
        { opacity: 1, y: 0, duration: duration.normal, ease: ease.butter, delay: i * staggerDelay }
      );
    },
    [enterAnimation, staggerDelay]
  );

  const exit = useCallback(
    (el: Element, done: () => void) => {
      if (exitAnimation) return exitAnimation(el, done);
      return gsap.to(el, {
        opacity: 0,
        x: -6,
        duration: duration.fast,
        ease: ease.sharp,
        onComplete: done,
      });
    },
    [exitAnimation]
  );

  useEffect(() => {
    const currentKeys = new Set(items.map(getKey));
    const renderedKeys = new Set(renderedItems.map(getKey));

    const added = items.filter((i) => !renderedKeys.has(getKey(i)));
    const removed = renderedItems.filter((i) => !currentKeys.has(getKey(i)));

    // Handle removals
    if (removed.length) {
      let completed = 0;
      removed.forEach((item) => {
        const key = getKey(item);
        const el = itemRefs.current.get(key);
        if (el) {
          exitingRefs.current.add(key);
          exit(el, () => {
            completed++;
            exitingRefs.current.delete(key);
            if (completed === removed.length) setRenderedItems(items);
          });
        }
      });
    } else {
      setRenderedItems(items);
    }

    // Handle additions
    if (added.length) {
      requestAnimationFrame(() => {
        added.forEach((item, i) => {
          const el = itemRefs.current.get(getKey(item));
          if (el) {
            gsap.set(el, { opacity: 0 });
            enter(el, i);
          }
        });
      });
    }
  }, [items, getKey, enter, exit, renderedItems]);

  const setRef = useCallback(
    (key: string | number) => (el: Element | null) => {
      if (el) {
        itemRefs.current.set(key, el);
      } else {
        itemRefs.current.delete(key);
      }
    },
    []
  );

  return {
    renderedItems,
    setRef,
    isExiting: (key: string | number) => exitingRefs.current.has(key),
  };
};

export const useGsapAnimation = <T extends HTMLElement>({
  animation,
}: { animation?: (el: Element) => gsap.core.Tween | gsap.core.Timeline } = {}) => {
  const ref = useRef<T>(null);
  useEffect(() => {
    if (ref.current)
      (
        animation ??
        ((el) =>
          gsap.fromTo(
            el,
            { opacity: 0, y: 8 },
            { opacity: 1, y: 0, duration: duration.normal, ease: ease.butter }
          ))
      )(ref.current);
  }, [animation]);
  return ref;
};

export const useButtonPress = <T extends HTMLElement>() => {
  const ref = useRef<T>(null);
  return {
    ref,
    handlers: {
      onMouseDown: () => {
        if (ref.current) gsap.to(ref.current, { scale: 0.92, duration: 0.1, ease: ease.snap });
      },
      onMouseUp: () => {
        if (ref.current) gsap.to(ref.current, { scale: 1, duration: 0.2, ease: ease.bounce });
      },
      onMouseLeave: () => {
        if (ref.current) gsap.to(ref.current, { scale: 1, duration: 0.2, ease: ease.butter });
      },
    },
  };
};
