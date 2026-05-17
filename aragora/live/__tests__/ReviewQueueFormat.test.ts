/**
 * Tests for the review-queue shared formatting helpers.
 */

import {
  ciGlyph,
  formatAge,
  formatDecisionSeconds,
  tierBadge,
  toneColor,
  verdictGlyph,
} from '../src/components/review-queue/format';

describe('formatAge', () => {
  it('returns dash for null/undefined', () => {
    expect(formatAge(null)).toBe('—');
    expect(formatAge(undefined)).toBe('—');
  });

  it('formats seconds, minutes, hours and days', () => {
    expect(formatAge(12)).toBe('12s');
    expect(formatAge(90)).toBe('1m');
    expect(formatAge(60 * 60 * 3)).toBe('3h');
    expect(formatAge(60 * 60 * 72)).toBe('3d');
  });
});

describe('formatDecisionSeconds', () => {
  it('handles null', () => {
    expect(formatDecisionSeconds(null)).toBe('—');
  });

  it('handles sub-second, seconds, and minutes', () => {
    expect(formatDecisionSeconds(0.25)).toBe('250ms');
    expect(formatDecisionSeconds(12)).toBe('12.0s');
    expect(formatDecisionSeconds(125)).toBe('2m05s');
  });
});

describe('ciGlyph', () => {
  it('neutral on no checks', () => {
    expect(ciGlyph({ success: 0, failure: 0, pending: 0, total: 0 })).toMatchObject({
      tone: 'neutral',
      glyph: '·',
    });
  });

  it('fail wins over pending and ok', () => {
    expect(
      ciGlyph({ success: 3, failure: 1, pending: 2, total: 6 }),
    ).toMatchObject({ tone: 'fail' });
  });

  it('warn when only pending', () => {
    expect(
      ciGlyph({ success: 1, failure: 0, pending: 2, total: 3 }),
    ).toMatchObject({ tone: 'warn' });
  });

  it('ok when all green', () => {
    expect(
      ciGlyph({ success: 4, failure: 0, pending: 0, total: 4 }),
    ).toMatchObject({ tone: 'ok' });
  });
});

describe('verdictGlyph', () => {
  it('neutral when no brief', () => {
    expect(verdictGlyph(false, null)).toMatchObject({ tone: 'neutral' });
  });

  it('matches known verdicts', () => {
    expect(verdictGlyph(true, 'approve_candidate').tone).toBe('ok');
    expect(verdictGlyph(true, 'needs_human_attention').tone).toBe('warn');
    expect(verdictGlyph(true, 'repair_first').tone).toBe('fail');
  });

  it('falls back to neutral on unknown verdicts', () => {
    expect(verdictGlyph(true, 'something-else').tone).toBe('neutral');
  });
});

describe('toneColor', () => {
  it('maps every tone', () => {
    expect(toneColor('ok')).toContain('green');
    expect(toneColor('warn')).toContain('yellow');
    expect(toneColor('fail')).toContain('red');
    expect(toneColor('neutral')).toContain('slate');
  });
});

describe('tierBadge', () => {
  it('returns null when no tier provided', () => {
    expect(tierBadge(null)).toBeNull();
    expect(tierBadge(undefined)).toBeNull();
    expect(tierBadge('')).toBeNull();
    expect(tierBadge('   ')).toBeNull();
  });

  it('maps each known tier to the documented tone', () => {
    expect(tierBadge('0')?.tone).toBe('ok');
    expect(tierBadge('1')?.tone).toBe('ok');
    expect(tierBadge('2')?.tone).toBe('warn');
    expect(tierBadge('3')?.tone).toBe('fail');
    expect(tierBadge('4')?.tone).toBe('fail');
  });

  it('emits a compact label and a descriptive fullLabel for each known tier', () => {
    expect(tierBadge('0')).toMatchObject({
      label: 'T0',
      fullLabel: expect.stringContaining('docs'),
    });
    expect(tierBadge('1')).toMatchObject({
      label: 'T1',
      fullLabel: expect.stringContaining('additive'),
    });
    expect(tierBadge('2')).toMatchObject({
      label: 'T2',
      fullLabel: expect.stringContaining('automation'),
    });
    expect(tierBadge('3')).toMatchObject({
      label: 'T3',
      fullLabel: expect.stringContaining('risk acceptance'),
    });
    expect(tierBadge('4')).toMatchObject({
      label: 'T4',
      fullLabel: expect.stringContaining('preapproval'),
    });
  });

  it('accepts numeric tier values (settlement-packet receipts emit ints)', () => {
    expect(tierBadge(0)?.label).toBe('T0');
    expect(tierBadge(2)?.label).toBe('T2');
    expect(tierBadge(4)?.label).toBe('T4');
  });

  it('falls back to a neutral badge for unknown tier strings', () => {
    const badge = tierBadge('99');
    expect(badge).not.toBeNull();
    expect(badge?.label).toBe('T99');
    expect(badge?.tone).toBe('neutral');
  });
});
