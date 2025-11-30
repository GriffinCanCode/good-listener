/**
 * GSAP Animation Utilities
 * Custom easing curves and animation presets for bespoke, smooth transitions.
 */

import gsap from 'gsap';

// ═══════════════════════════════════════════════════════════════════════════
// Custom Easing Curves - Bespoke and Smooth
// ═══════════════════════════════════════════════════════════════════════════

export const ease = {
  silk: 'cubic-bezier(0.22, 1, 0.36, 1)', // Smooth, elegant deceleration
  butter: 'cubic-bezier(0.16, 1, 0.3, 1)', // Organic, slight springy feel
  glide: 'cubic-bezier(0.65, 0, 0.35, 1)', // Gentle entrance/exit
  snap: 'cubic-bezier(0.11, 0, 0.5, 0)', // Quick, responsive
  float: 'sine.inOut', // Floating ambient
  bounce: 'back.out(1.7)', // Playful
  sharp: 'cubic-bezier(0.11, 0, 0.5, 0)', // Sharp exit
} as const;

// ═══════════════════════════════════════════════════════════════════════════
// Duration Presets
// ═══════════════════════════════════════════════════════════════════════════

export const duration = {
  instant: 0.1,
  fast: 0.2,
  normal: 0.35,
  smooth: 0.5,
  slow: 0.7,
  ambient: 1.2,
} as const;

// ═══════════════════════════════════════════════════════════════════════════
// Animation Primitives & Helpers
// ═══════════════════════════════════════════════════════════════════════════

export interface AnimConfig {
  duration?: number;
  ease?: string;
  delay?: number;
  onComplete?: gsap.Callback;
}

const animate = (el: Element | null, from: gsap.TweenVars, to: gsap.TweenVars) =>
  el ? gsap.fromTo(el, from, to) : null;

export const fadeIn = (
  el: Element | null,
  {
    y = 0,
    scale = 1,
    duration: d = duration.normal,
    ease: e = ease.butter,
    delay = 0,
    ...config
  }: AnimConfig & { y?: number; scale?: number } = {}
) =>
  animate(
    el,
    { opacity: 0, y, scale },
    { opacity: 1, y: 0, scale: 1, duration: d, ease: e, delay, ...config }
  );

export const fadeOut = (
  el: Element | null,
  {
    y = 0,
    scale = 1,
    duration: d = duration.fast,
    ease: e = ease.sharp,
    delay = 0,
    ...config
  }: AnimConfig & { y?: number; scale?: number } = {}
) => (el ? gsap.to(el, { opacity: 0, y, scale, duration: d, ease: e, delay, ...config }) : null);

export const slideIn = (
  el: Element | null,
  from: 'left' | 'right' | 'top' | 'bottom',
  config: AnimConfig = {}
) => {
  const offsets = {
    left: { x: '-100%' },
    right: { x: '100%' },
    top: { y: '-100%' },
    bottom: { y: '100%' },
  };
  return animate(
    el,
    { ...offsets[from], opacity: 0 },
    { x: 0, y: 0, opacity: 1, duration: duration.smooth, ease: ease.butter, ...config }
  );
};

export const slideOut = (
  el: Element | null,
  to: 'left' | 'right' | 'top' | 'bottom',
  config: AnimConfig = {}
) => {
  const offsets = {
    left: { x: '-100%' },
    right: { x: '100%' },
    top: { y: '-100%' },
    bottom: { y: '100%' },
  };
  return el
    ? gsap.to(el, {
        ...offsets[to],
        opacity: 0,
        duration: duration.fast,
        ease: ease.sharp,
        ...config,
      })
    : null;
};

export const scaleIn = (
  el: Element | null,
  {
    from = 0.95,
    y = 0,
    duration: d = duration.normal,
    ease: e = ease.bounce,
    ...rest
  }: AnimConfig & { from?: number; y?: number } = {}
) =>
  animate(
    el,
    { opacity: 0, scale: from, y },
    { opacity: 1, scale: 1, y: 0, duration: d, ease: e, ...rest }
  );

export const scaleOut = (
  el: Element | null,
  {
    to = 0.95,
    duration: d = duration.fast,
    ease: e = ease.sharp,
    ...rest
  }: AnimConfig & { to?: number } = {}
) => (el ? gsap.to(el, { opacity: 0, scale: to, duration: d, ease: e, ...rest }) : null);

export const staggerIn = (
  elements: Element[] | NodeListOf<Element>,
  {
    stagger = 0.05,
    y = 12,
    duration: d = duration.normal,
    ease: e = ease.butter,
    delay = 0,
    ...config
  }: AnimConfig & { stagger?: number; y?: number } = {}
) =>
  gsap.fromTo(
    elements,
    { opacity: 0, y },
    { opacity: 1, y: 0, duration: d, ease: e, stagger, delay, ...config }
  );

// ═══════════════════════════════════════════════════════════════════════════
// Interaction Effects
// ═══════════════════════════════════════════════════════════════════════════

export const press = (el: Element | null) =>
  el && gsap.to(el, { scale: 0.96, duration: 0.1, ease: 'power1.out' });
export const release = (el: Element | null) =>
  el && gsap.to(el, { scale: 1, duration: 0.3, ease: 'back.out(1.7)' });

export const breathe = (
  el: Element | null,
  {
    scale = 1.15,
    duration: d = 0.3,
    glowColor,
  }: { scale?: number; duration?: number; glowColor?: string } = {}
) =>
  el
    ? gsap.to(el, {
        scale,
        ...(glowColor ? { filter: `drop-shadow(0 0 6px ${glowColor})` } : {}),
        duration: d,
        ease: ease.float,
        repeat: -1,
        yoyo: true,
      })
    : null;

// ═══════════════════════════════════════════════════════════════════════════
// Presence Config
// ═══════════════════════════════════════════════════════════════════════════

export interface PresenceAnimation {
  enter: (el: Element) => gsap.core.Tween | gsap.core.Timeline | null;
  exit: (el: Element, onComplete: () => void) => gsap.core.Tween | gsap.core.Timeline | null;
}

export const presenceAnimations: Record<string, PresenceAnimation> = {
  fade: {
    enter: (el) => fadeIn(el, { duration: duration.normal }),
    exit: (el, onComplete) => fadeOut(el, { onComplete }),
  },
  slideUp: {
    enter: (el) => fadeIn(el, { y: 20, duration: duration.normal }),
    exit: (el, onComplete) => fadeOut(el, { y: -10, onComplete }),
  },
  slideDown: {
    enter: (el) => fadeIn(el, { y: -20, duration: duration.normal }),
    exit: (el, onComplete) => fadeOut(el, { y: 10, onComplete }),
  },
  slideLeft: {
    enter: (el) => slideIn(el, 'left'),
    exit: (el, onComplete) => slideOut(el, 'left', { onComplete }),
  },
  slideRight: {
    enter: (el) => slideIn(el, 'right'),
    exit: (el, onComplete) => slideOut(el, 'right', { onComplete }),
  },
  scale: {
    enter: (el) => scaleIn(el, { from: 0.95 }),
    exit: (el, onComplete) => scaleOut(el, { to: 0.95, onComplete }),
  },
  scaleUp: {
    enter: (el) =>
      gsap.fromTo(
        el,
        { scale: 0.95, y: -20, opacity: 0 },
        { scale: 1, y: 0, opacity: 1, duration: duration.normal, ease: ease.bounce }
      ),
    exit: (el, onComplete) =>
      gsap.to(el, {
        scale: 0.95,
        y: -10,
        opacity: 0,
        duration: duration.fast,
        ease: ease.sharp,
        onComplete,
      }),
  },
  sidebar: {
    enter: (el) =>
      gsap.fromTo(el, { x: '-100%' }, { x: 0, duration: duration.smooth, ease: ease.butter }),
    exit: (el, onComplete) =>
      gsap.to(el, { x: '-100%', duration: duration.fast, ease: ease.sharp, onComplete }),
  },
  backdrop: {
    enter: (el) =>
      gsap.fromTo(el, { opacity: 0 }, { opacity: 1, duration: duration.fast, ease: ease.silk }),
    exit: (el, onComplete) =>
      gsap.to(el, { opacity: 0, duration: duration.fast, ease: ease.silk, onComplete }),
  },
};

// Legacy Spring Config (kept for compatibility if needed, though SpringValue class removed)
export interface SpringConfig {
  stiffness?: number;
  damping?: number;
  mass?: number;
}
