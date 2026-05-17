/**
 * Shared formatting helpers for the review-queue surface.
 */

export function formatAge(ageSeconds: number | null | undefined): string {
  if (ageSeconds === null || ageSeconds === undefined) return '—';
  const sec = Math.max(0, Math.floor(ageSeconds));
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m`;
  const hour = Math.floor(min / 60);
  if (hour < 48) return `${hour}h`;
  const day = Math.floor(hour / 24);
  return `${day}d`;
}

export function formatDecisionSeconds(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  if (value < 1) return `${Math.round(value * 1000)}ms`;
  if (value < 60) return `${value.toFixed(1)}s`;
  const min = Math.floor(value / 60);
  const sec = Math.round(value - min * 60);
  return `${min}m${sec.toString().padStart(2, '0')}s`;
}

export function ciGlyph(ci: {
  success: number;
  failure: number;
  pending: number;
  total: number;
}): { glyph: string; label: string; tone: 'ok' | 'warn' | 'fail' | 'neutral' } {
  if (ci.total === 0) return { glyph: '·', label: 'no checks', tone: 'neutral' };
  if (ci.failure > 0) {
    return { glyph: '✗', label: `${ci.failure} failing / ${ci.total}`, tone: 'fail' };
  }
  if (ci.pending > 0) {
    return { glyph: '⚠', label: `${ci.pending} pending / ${ci.total}`, tone: 'warn' };
  }
  return { glyph: '✓', label: `${ci.success}/${ci.total} green`, tone: 'ok' };
}

export function verdictGlyph(
  brief_present: boolean,
  verdict: string | null,
): { glyph: string; label: string; tone: 'ok' | 'warn' | 'fail' | 'neutral' } {
  if (!brief_present) return { glyph: '?', label: 'no brief', tone: 'neutral' };
  switch (verdict) {
    case 'approve_candidate':
      return { glyph: '✓', label: 'approve candidate', tone: 'ok' };
    case 'needs_human_attention':
      return { glyph: '⚠', label: 'needs attention', tone: 'warn' };
    case 'repair_first':
      return { glyph: '✗', label: 'repair first', tone: 'fail' };
    default:
      return { glyph: '?', label: verdict || 'unknown', tone: 'neutral' };
  }
}

export function toneColor(tone: 'ok' | 'warn' | 'fail' | 'neutral'): string {
  switch (tone) {
    case 'ok':
      return 'text-green-400';
    case 'warn':
      return 'text-yellow-400';
    case 'fail':
      return 'text-red-400';
    default:
      return 'text-slate-400';
  }
}

/**
 * Map a tier classification (per docs/REVIEW_AUTHORITY_PRINCIPLES.md, lines 26-38)
 * into a compact badge descriptor. Tier values are strings to match the JSON
 * receipt payload shape; we accept null/undefined and return null in that case
 * so callers can render `tierBadge(pr.tier) && <Badge ... />`.
 *
 * | Tier | Class | Settlement |
 * | --- | --- | --- |
 * | 0 | Docs/tests/status only | Admin squash allowed |
 * | 1 | Additive internal code | Admin squash allowed |
 * | 2 | Live CLI/automation/observability | Admin squash allowed |
 * | 3 | Semantic/persistence/security/public API | Human risk acceptance required |
 * | 4 | Secrets/deployment/policy/merge-gate | Human preapproval required |
 */
export function tierBadge(tier: string | number | null | undefined): {
  label: string;
  fullLabel: string;
  tone: 'ok' | 'warn' | 'fail' | 'neutral';
} | null {
  if (tier === null || tier === undefined) return null;
  const value = String(tier).trim();
  if (!value) return null;
  switch (value) {
    case '0':
      return { label: 'T0', fullLabel: 'Tier 0 — docs/tests', tone: 'ok' };
    case '1':
      return { label: 'T1', fullLabel: 'Tier 1 — additive code', tone: 'ok' };
    case '2':
      return { label: 'T2', fullLabel: 'Tier 2 — live CLI/automation', tone: 'warn' };
    case '3':
      return { label: 'T3', fullLabel: 'Tier 3 — needs human risk acceptance', tone: 'fail' };
    case '4':
      return { label: 'T4', fullLabel: 'Tier 4 — needs human preapproval', tone: 'fail' };
    default:
      return { label: `T${value}`, fullLabel: `Tier ${value}`, tone: 'neutral' };
  }
}
