/**
 * Lightweight distributed tracing for the frontend.
 * Generates W3C-compatible trace IDs for request correlation.
 */

/** Generate cryptographically secure random hex string */
const randomHex = (bytes: number): string => {
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);
  return Array.from(arr, (b) => b.toString(16).padStart(2, '0')).join('');
};

/** Generate 128-bit trace ID (W3C standard) */
export const generateTraceId = (): string => randomHex(16);

/** Generate 64-bit span ID (W3C standard) */
export const generateSpanId = (): string => randomHex(8);

/** Trace context for a single operation */
export interface TraceContext {
  traceId: string;
  spanId: string;
  parentSpanId?: string;
}

/** Create a new trace context */
export const createTrace = (): TraceContext => ({
  traceId: generateTraceId(),
  spanId: generateSpanId(),
});

/** Create a child span within existing trace */
export const childSpan = (parent: TraceContext): TraceContext => ({
  traceId: parent.traceId,
  spanId: generateSpanId(),
  parentSpanId: parent.spanId,
});

/**
 * Console logging with trace context.
 * In production, this could be extended to send to a backend collector.
 */
export const traceLog = (
  level: 'debug' | 'info' | 'warn' | 'error',
  message: string,
  ctx?: TraceContext,
  extra?: Record<string, unknown>
): void => {
  const logFn = console[level];
  const prefix = ctx ? `[${ctx.traceId.slice(0, 8)}]` : '';
  logFn(`${prefix} ${message}`, extra ?? '');
};

/**
 * Create a traced operation wrapper.
 * Returns the trace context for inclusion in outgoing requests.
 */
export const startTrace = (name: string): { ctx: TraceContext; end: () => void } => {
  const ctx = createTrace();
  const start = performance.now();

  if (import.meta.env.DEV) {
    traceLog('debug', `→ ${name}`, ctx);
  }

  return {
    ctx,
    end: () => {
      const duration = performance.now() - start;
      if (import.meta.env.DEV) {
        traceLog('debug', `← ${name} (${duration.toFixed(1)}ms)`, ctx);
      }
    },
  };
};
