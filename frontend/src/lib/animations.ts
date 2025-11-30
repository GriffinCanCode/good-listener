/**
 * GSAP Animation Utilities - Bespoke smooth transitions
 * Custom easing curves and animation presets for silky interactions
 */

import gsap from 'gsap';

// ═══════════════════════════════════════════════════════════════════════════
// Custom Easing Curves - Buttery smooth, natural motion
// ═══════════════════════════════════════════════════════════════════════════

export const ease = {
  // Silk - smooth deceleration with gentle overshoot
  silk: 'power2.out',
  // Butter - ultra-smooth with subtle spring feel
  butter: 'power3.out',
  // Glide - natural ease for entrances
  glide: 'power2.inOut',
  // Snap - quick, responsive micro-interactions
  snap: 'power4.out',
  // Float - dreamy, slow ease for ambient elements
  float: 'sine.inOut',
  // Bounce - playful with dampened spring
  bounce: 'back.out(1.2)',
  // Sharp - crisp exits
  sharp: 'power3.in',
} as const;

// ═══════════════════════════════════════════════════════════════════════════
// Duration Presets (in seconds)
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
// Animation Presets - Ready-to-use animations
// ═══════════════════════════════════════════════════════════════════════════

export interface AnimationConfig {
  duration?: number;
  ease?: string;
  delay?: number;
  onComplete?: () => void;
}

/** Fade in with optional vertical slide */
export const fadeIn = (
  el: Element | null,
  config: AnimationConfig & { y?: number; scale?: number } = {}
) => {
  if (!el) return null;
  const {
    y = 0,
    scale = 1,
    duration: d = duration.normal,
    ease: e = ease.butter,
    delay = 0,
    onComplete,
  } = config;

  const tweenVars: gsap.TweenVars = { opacity: 1, y: 0, scale: 1, duration: d, ease: e, delay };
  if (onComplete) tweenVars.onComplete = onComplete;

  return gsap.fromTo(el, { opacity: 0, y, scale }, tweenVars);
};

/** Fade out with optional vertical slide */
export const fadeOut = (
  el: Element | null,
  config: AnimationConfig & { y?: number; scale?: number } = {}
) => {
  if (!el) return null;
  const {
    y = 0,
    scale = 1,
    duration: d = duration.fast,
    ease: e = ease.sharp,
    delay = 0,
    onComplete,
  } = config;

  const tweenVars: gsap.TweenVars = { opacity: 0, y, scale, duration: d, ease: e, delay };
  if (onComplete) tweenVars.onComplete = onComplete;

  return gsap.to(el, tweenVars);
};

/** Slide in from direction */
export const slideIn = (
  el: Element | null,
  from: 'left' | 'right' | 'top' | 'bottom',
  config: AnimationConfig = {}
) => {
  if (!el) return null;
  const { duration: d = duration.smooth, ease: e = ease.butter, delay = 0, onComplete } = config;

  const offsets = {
    left: { x: '-100%', y: 0 },
    right: { x: '100%', y: 0 },
    top: { x: 0, y: '-100%' },
    bottom: { x: 0, y: '100%' },
  };

  const tweenVars: gsap.TweenVars = { x: 0, y: 0, opacity: 1, duration: d, ease: e, delay };
  if (onComplete) tweenVars.onComplete = onComplete;

  return gsap.fromTo(el, { ...offsets[from], opacity: 0 }, tweenVars);
};

/** Slide out to direction */
export const slideOut = (
  el: Element | null,
  to: 'left' | 'right' | 'top' | 'bottom',
  config: AnimationConfig = {}
) => {
  if (!el) return null;
  const { duration: d = duration.fast, ease: e = ease.sharp, delay = 0, onComplete } = config;

  const offsets = {
    left: { x: '-100%', y: 0 },
    right: { x: '100%', y: 0 },
    top: { x: 0, y: '-100%' },
    bottom: { x: 0, y: '100%' },
  };

  const tweenVars: gsap.TweenVars = { ...offsets[to], opacity: 0, duration: d, ease: e, delay };
  if (onComplete) tweenVars.onComplete = onComplete;

  return gsap.to(el, tweenVars);
};

/** Scale with fade - perfect for cards/modals */
export const scaleIn = (el: Element | null, config: AnimationConfig & { from?: number } = {}) => {
  if (!el) return null;
  const {
    from = 0.95,
    duration: d = duration.normal,
    ease: e = ease.bounce,
    delay = 0,
    onComplete,
  } = config;

  const tweenVars: gsap.TweenVars = { opacity: 1, scale: 1, duration: d, ease: e, delay };
  if (onComplete) tweenVars.onComplete = onComplete;

  return gsap.fromTo(el, { opacity: 0, scale: from }, tweenVars);
};

/** Scale out with fade */
export const scaleOut = (el: Element | null, config: AnimationConfig & { to?: number } = {}) => {
  if (!el) return null;
  const {
    to = 0.95,
    duration: d = duration.fast,
    ease: e = ease.sharp,
    delay = 0,
    onComplete,
  } = config;

  const tweenVars: gsap.TweenVars = { opacity: 0, scale: to, duration: d, ease: e, delay };
  if (onComplete) tweenVars.onComplete = onComplete;

  return gsap.to(el, tweenVars);
};

/** Pulse effect - subtle attention grabber */
export const pulse = (el: Element | null, config: { scale?: number; count?: number } = {}) => {
  if (!el) return null;
  const { scale = 1.05, count = 2 } = config;

  return gsap.to(el, {
    scale,
    duration: 0.15,
    ease: ease.snap,
    repeat: count * 2 - 1,
    yoyo: true,
  });
};

/** Press effect for buttons */
export const press = (el: Element | null) => {
  if (!el) return null;
  return gsap.to(el, { scale: 0.92, duration: duration.instant, ease: ease.snap });
};

/** Release effect for buttons */
export const release = (el: Element | null) => {
  if (!el) return null;
  return gsap.to(el, { scale: 1, duration: duration.fast, ease: ease.bounce });
};

// ═══════════════════════════════════════════════════════════════════════════
// Spring Animation - Custom spring physics
// ═══════════════════════════════════════════════════════════════════════════

export interface SpringConfig {
  stiffness?: number;
  damping?: number;
  mass?: number;
}

/** Animated spring value controller */
export class SpringValue {
  private value: number;
  private target: number;
  private velocity = 0;
  private stiffness: number;
  private damping: number;
  private mass: number;
  private raf: number | null = null;
  private onChange: (value: number) => void;

  constructor(initialValue: number, onChange: (value: number) => void, config: SpringConfig = {}) {
    this.value = initialValue;
    this.target = initialValue;
    this.onChange = onChange;
    this.stiffness = config.stiffness ?? 300;
    this.damping = config.damping ?? 15;
    this.mass = config.mass ?? 0.5;
  }

  set(newTarget: number) {
    this.target = newTarget;
    if (!this.raf) this.tick();
  }

  private tick = () => {
    const dt = 1 / 60;
    const spring = (this.target - this.value) * this.stiffness;
    const damper = -this.velocity * this.damping;
    const acceleration = (spring + damper) / this.mass;

    this.velocity += acceleration * dt;
    this.value += this.velocity * dt;

    this.onChange(this.value);

    // Continue if not settled
    if (Math.abs(this.velocity) > 0.001 || Math.abs(this.target - this.value) > 0.001) {
      this.raf = requestAnimationFrame(this.tick);
    } else {
      this.value = this.target;
      this.onChange(this.value);
      this.raf = null;
    }
  };

  destroy() {
    if (this.raf) cancelAnimationFrame(this.raf);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Stagger Animations - For lists and groups
// ═══════════════════════════════════════════════════════════════════════════

/** Staggered fade in for lists */
export const staggerIn = (
  elements: Element[] | NodeListOf<Element>,
  config: AnimationConfig & { stagger?: number; y?: number } = {}
) => {
  const {
    stagger = 0.05,
    y = 12,
    duration: d = duration.normal,
    ease: e = ease.butter,
    delay = 0,
  } = config;

  return gsap.fromTo(
    elements,
    { opacity: 0, y },
    { opacity: 1, y: 0, duration: d, ease: e, stagger, delay }
  );
};

/** Staggered fade out */
export const staggerOut = (
  elements: Element[] | NodeListOf<Element>,
  config: AnimationConfig & { stagger?: number; y?: number } = {}
) => {
  const {
    stagger = 0.03,
    y = -8,
    duration: d = duration.fast,
    ease: e = ease.sharp,
    delay = 0,
  } = config;

  return gsap.to(elements, { opacity: 0, y, duration: d, ease: e, stagger, delay });
};

// ═══════════════════════════════════════════════════════════════════════════
// Presence Animation Manager - Handles mount/unmount animations
// ═══════════════════════════════════════════════════════════════════════════

export interface PresenceAnimation {
  enter: (el: Element) => gsap.core.Tween | gsap.core.Timeline;
  exit: (el: Element, onComplete: () => void) => gsap.core.Tween | gsap.core.Timeline;
}

/** Pre-built presence animation presets */
export const presenceAnimations = {
  fade: {
    enter: (el: Element) =>
      fadeIn(el, { duration: duration.normal }) ?? gsap.set(el, { opacity: 1 }),
    exit: (el: Element, onComplete: () => void) =>
      fadeOut(el, { onComplete }) ?? gsap.set(el, { opacity: 0 }),
  },

  slideUp: {
    enter: (el: Element) =>
      fadeIn(el, { y: 20, duration: duration.normal }) ?? gsap.set(el, { opacity: 1 }),
    exit: (el: Element, onComplete: () => void) =>
      fadeOut(el, { y: -10, onComplete }) ?? gsap.set(el, { opacity: 0 }),
  },

  slideDown: {
    enter: (el: Element) =>
      fadeIn(el, { y: -20, duration: duration.normal }) ?? gsap.set(el, { opacity: 1 }),
    exit: (el: Element, onComplete: () => void) =>
      fadeOut(el, { y: 10, onComplete }) ?? gsap.set(el, { opacity: 0 }),
  },

  slideLeft: {
    enter: (el: Element) =>
      gsap.fromTo(
        el,
        { x: 20, opacity: 0 },
        { x: 0, opacity: 1, duration: duration.smooth, ease: ease.butter }
      ),
    exit: (el: Element, onComplete: () => void) =>
      gsap.to(el, { x: 20, opacity: 0, duration: duration.fast, ease: ease.sharp, onComplete }),
  },

  slideRight: {
    enter: (el: Element) =>
      gsap.fromTo(
        el,
        { x: -20, opacity: 0 },
        { x: 0, opacity: 1, duration: duration.smooth, ease: ease.butter }
      ),
    exit: (el: Element, onComplete: () => void) =>
      gsap.to(el, { x: -20, opacity: 0, duration: duration.fast, ease: ease.sharp, onComplete }),
  },

  scale: {
    enter: (el: Element) =>
      scaleIn(el, { from: 0.95, duration: duration.normal }) ?? gsap.set(el, { opacity: 1 }),
    exit: (el: Element, onComplete: () => void) =>
      scaleOut(el, { to: 0.95, onComplete }) ?? gsap.set(el, { opacity: 0 }),
  },

  scaleUp: {
    enter: (el: Element) =>
      gsap.fromTo(
        el,
        { scale: 0.95, y: -20, opacity: 0 },
        { scale: 1, y: 0, opacity: 1, duration: duration.normal, ease: ease.bounce }
      ),
    exit: (el: Element, onComplete: () => void) =>
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
    enter: (el: Element) =>
      gsap.fromTo(el, { x: '-100%' }, { x: 0, duration: duration.smooth, ease: ease.butter }),
    exit: (el: Element, onComplete: () => void) =>
      gsap.to(el, { x: '-100%', duration: duration.fast, ease: ease.sharp, onComplete }),
  },

  backdrop: {
    enter: (el: Element) =>
      gsap.fromTo(el, { opacity: 0 }, { opacity: 1, duration: duration.fast, ease: ease.silk }),
    exit: (el: Element, onComplete: () => void) =>
      gsap.to(el, { opacity: 0, duration: duration.fast, ease: ease.silk, onComplete }),
  },
} as const;

// ═══════════════════════════════════════════════════════════════════════════
// Continuous Animations - Loops and ambient effects
// ═══════════════════════════════════════════════════════════════════════════

/** Pulsing ring animation (like mic connecting) */
export const pulseRing = (el: Element | null) => {
  if (!el) return null;
  return gsap.fromTo(
    el,
    { scale: 0.8, opacity: 0.6 },
    { scale: 1.8, opacity: 0, duration: 1.2, ease: ease.silk, repeat: -1 }
  );
};

/** Icon breathing/pulsing effect */
export const breathe = (el: Element | null, config: { scale?: number; duration?: number } = {}) => {
  if (!el) return null;
  const { scale = 1.15, duration: d = 0.3 } = config;

  return gsap.to(el, {
    scale,
    duration: d,
    ease: ease.float,
    repeat: -1,
    yoyo: true,
  });
};

/** Audio bar animation */
export const audioBar = (el: Element | null, targetHeight: number, config: SpringConfig = {}) => {
  if (!el) return null;
  const { stiffness = 300, damping = 15 } = config;

  // Convert spring physics to GSAP timing
  const springDuration = Math.sqrt(1 / stiffness) * damping * 0.1;

  return gsap.to(el, {
    scaleY: targetHeight,
    duration: springDuration,
    ease: 'power2.out',
  });
};

// ═══════════════════════════════════════════════════════════════════════════
// Utility Functions
// ═══════════════════════════════════════════════════════════════════════════

/** Kill all animations on an element */
export const killAnimations = (el: Element | null) => {
  if (el) gsap.killTweensOf(el);
};

/** Set element to specific state (no animation) */
export const set = (el: Element | null, props: gsap.TweenVars) => {
  if (el) gsap.set(el, props);
};

/** Create a timeline for complex sequences */
export const timeline = (config?: gsap.TimelineVars) => gsap.timeline(config);
