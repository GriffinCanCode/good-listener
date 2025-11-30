import { useEffect, useMemo, useRef, useState } from 'react';

/**
 * Debounces a value.
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Returns a memoized function that will only call the passed function when it hasn't been called for the wait period.
 * The returned function is stable and won't change on re-renders, even if the callback does.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
) {
  const callbackRef = useRef(callback);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  // Keep callback ref up to date
  useEffect(() => {
    callbackRef.current = callback;
  });

  // Cleanup on unmount
  useEffect(
    () => () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    },
    []
  );

  return useMemo(() => {
    const func = (...args: Parameters<T>) => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => {
        callbackRef.current(...args);
      }, delay);
    };

    func.cancel = () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };

    return func;
  }, [delay]);
}
