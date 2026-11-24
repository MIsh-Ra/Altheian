import { ThinkingOrb } from 'thinking-orbs';
import { useTheme } from '../ThemeContext';

/**
 * Maps Alethian pipeline stages or document statuses to thinking-orbs animation states:
 * - ingesting / pending   -> 'shaping' (morphing geometry representing parsing/structuring)
 * - indexing              -> 'connecting' (constellation wiring into vector archive)
 * - similarity / analyzing-> 'solving' (bands quarter-turning, mathematical alignment)
 * - web_dragnet           -> 'searching' (meridian sweep across globe)
 * - ai_detection          -> 'working' (orbital particles for GPU neural compute)
 * - report_generation     -> 'composing' (undulating sash for report synthesis)
 * - default / ambient     -> 'breathing' (slow morphing ring)
 */
export const STAGE_TO_ORB_STATE = {
  pending: 'shaping',
  ingesting: 'shaping',
  indexing: 'connecting',
  similarity: 'solving',
  analyzing: 'solving',
  web_dragnet: 'searching',
  ai_detection: 'working',
  ai_escalation: 'working',
  processing: 'working',
  report_generation: 'composing',
  complete: 'breathing',
  idle: 'breathing',
};

/**
 * Normalize input size to one of thinking-orbs tuned presets: 20, 32, or 64.
 */
export function normalizeOrbSize(size) {
  if (size === 20 || size === 32 || size === 64) return size;
  const num = Number(size);
  if (isNaN(num)) return 64;
  if (num <= 26) return 20;
  if (num <= 48) return 32;
  return 64;
}

export default function AgentOrb({
  stage,
  state,
  size = 64,
  speed = 1,
  paused = false,
  className = '',
  color,
  tint,
  ...props
}) {
  let themeMode = 'auto';
  try {
    const themeContext = useTheme();
    themeMode = themeContext?.theme || 'auto';
  } catch {
    themeMode = 'auto';
  }

  // Determine the active orb state
  const activeState = state || STAGE_TO_ORB_STATE[stage] || 'working';
  const resolvedSize = normalizeOrbSize(size);
  const resolvedColor = color || tint;

  return (
    <div
      className={`inline-flex items-center justify-center select-none ${className}`}
      data-testid="agent-orb"
    >
      <ThinkingOrb
        state={activeState}
        size={resolvedSize}
        theme={themeMode}
        speed={speed}
        paused={paused}
        color={resolvedColor}
        {...props}
      />
    </div>
  );
}
