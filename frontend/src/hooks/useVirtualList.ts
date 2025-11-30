import { useVirtualizer, type VirtualizerOptions } from '@tanstack/react-virtual';
import { useRef } from 'react';

interface UseVirtualListProps<T, E extends Element> extends Partial<VirtualizerOptions<E, E>> {
  items: T[];
  estimateSize?: (index: number) => number;
  overscan?: number;
  scrollRef?: React.RefObject<E>;
}

export const useVirtualList = <T, E extends Element>({
  items,
  estimateSize = () => 50,
  overscan = 5,
  scrollRef,
  ...options
}: UseVirtualListProps<T, E>) => {
  const internalRef = useRef<E>(null);
  const parentRef = scrollRef ?? internalRef;

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize,
    overscan,
    ...options,
  });

  return { parentRef, virtualizer, items: virtualizer.getVirtualItems() };
};
