import { useCallback, useEffect, useRef } from 'react';

interface UseAutoScrollOptions {
  /** Distance from bottom (px) to consider "at bottom" - default 100 */
  threshold?: number;
  /** Smooth scroll or instant - default true */
  smooth?: boolean;
}

/**
 * Hook for robust auto-scrolling that respects user scroll position.
 * Only auto-scrolls when user is near the bottom; if they scroll up to read, stays put.
 */
export const useAutoScroll = (deps: unknown[], options: UseAutoScrollOptions = {}) => {
  const { threshold = 100, smooth = true } = options;
  const containerRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);
  const isUserScrollingRef = useRef(false);
  const scrollTimeoutRef = useRef<number>();

  const checkIfAtBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return true;
    const { scrollTop, scrollHeight, clientHeight } = el;
    return scrollHeight - scrollTop - clientHeight <= threshold;
  }, [threshold]);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTo({
      top: el.scrollHeight,
      behavior: smooth ? 'smooth' : 'instant',
    });
  }, [smooth]);

  // Track user scroll to determine if they've scrolled away
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handleScroll = () => {
      // Debounce to let programmatic scrolls settle
      if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);
      isUserScrollingRef.current = true;

      scrollTimeoutRef.current = window.setTimeout(() => {
        isUserScrollingRef.current = false;
        isAtBottomRef.current = checkIfAtBottom();
      }, 50);
    };

    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      el.removeEventListener('scroll', handleScroll);
      if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);
    };
  }, [checkIfAtBottom]);

  // Auto-scroll when deps change, but only if at bottom
  useEffect(() => {
    if (isAtBottomRef.current && !isUserScrollingRef.current) {
      // Small delay to ensure DOM has updated
      requestAnimationFrame(scrollToBottom);
    }
  }, [deps, scrollToBottom]);

  // Force scroll to bottom (for manual triggers)
  const forceScrollToBottom = useCallback(() => {
    isAtBottomRef.current = true;
    scrollToBottom();
  }, [scrollToBottom]);

  return {
    containerRef,
    scrollToBottom: forceScrollToBottom,
    isAtBottom: () => isAtBottomRef.current,
  };
};
