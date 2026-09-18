/**
 * Pure math for the dashboard's bar chart.
 *
 * This lives in util/ rather than in the component on purpose: it is the only
 * part of the chart with logic worth testing, and a pure module can be spec'd
 * without TestBed, a DOM, or a fixture. Put new logic here and keep components
 * to wiring — see bar-scale.spec.ts for the payoff.
 */

export interface BarDatum {
    label: string;
    value: number;
}

export interface Bar extends BarDatum {
    /** Width as a fraction of the axis max, 0..1. */
    ratio: number;
    /** Share of the total, 0..100, for the value label. */
    percent: number;
}

/**
 * A bar this short is invisible, so any non-zero value is drawn at least this
 * wide. Without it, a 1-of-50,000 row renders as nothing and reads as "no
 * data" rather than "very small" — a real difference to an analyst.
 */
export const MIN_VISIBLE_RATIO = 0.015;

/** Round `max` up to a readable axis maximum (1, 2, or 5 x a power of ten). */
export function niceMax(max: number): number {
    if (!isFinite(max) || max <= 0) return 1;
    const magnitude = Math.pow(10, Math.floor(Math.log10(max)));
    const normalized = max / magnitude;
    let step: number;
    if (normalized <= 1) step = 1;
    else if (normalized <= 2) step = 2;
    else if (normalized <= 5) step = 5;
    else step = 10;
    return step * magnitude;
}

/**
 * Turn raw `{label, value}` rows into drawable bars, largest first.
 *
 * `limit` caps the number of bars; anything beyond it is folded into a single
 * "Other (n)" row so the chart stays readable without hiding the tail's
 * existence. Negative and non-finite values are treated as zero.
 */
export function buildBars(data: BarDatum[], limit = 10): Bar[] {
    const clean = (data || [])
        .filter((d) => d && typeof d.label === 'string')
        .map((d) => ({
            label: d.label,
            value: isFinite(d.value) && d.value > 0 ? d.value : 0,
        }))
        .sort((a, b) => b.value - a.value || a.label.localeCompare(b.label));

    let rows = clean;
    if (limit > 0 && clean.length > limit) {
        const head = clean.slice(0, limit - 1);
        const tail = clean.slice(limit - 1);
        const tailTotal = tail.reduce((sum, d) => sum + d.value, 0);
        rows = [...head, { label: `Other (${tail.length})`, value: tailTotal }];
    }

    const total = rows.reduce((sum, d) => sum + d.value, 0);
    const axisMax = niceMax(Math.max(...rows.map((d) => d.value), 0));

    return rows.map((d) => ({
        ...d,
        ratio: d.value === 0 ? 0 : Math.max(MIN_VISIBLE_RATIO, d.value / axisMax),
        percent: total === 0 ? 0 : (d.value / total) * 100,
    }));
}

/** Format a count compactly: 1234 -> "1,234", 1_250_000 -> "1.3M". */
export function formatCount(value: number): string {
    if (!isFinite(value)) return '—';
    const abs = Math.abs(value);
    if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (abs >= 10_000) return `${(value / 1_000).toFixed(1)}K`;
    return value.toLocaleString('en-US');
}
