import { buildBars, formatCount, MIN_VISIBLE_RATIO, niceMax } from './bar-scale';

describe('niceMax', () => {
    it('rounds up to 1, 2 or 5 times a power of ten', () => {
        expect(niceMax(7)).toBe(10);
        expect(niceMax(12)).toBe(20);
        expect(niceMax(37)).toBe(50);
        expect(niceMax(120)).toBe(200);
        expect(niceMax(1)).toBe(1);
    });

    it('never returns zero for empty or invalid input', () => {
        expect(niceMax(0)).toBe(1);
        expect(niceMax(-5)).toBe(1);
        expect(niceMax(NaN)).toBe(1);
    });
});

describe('buildBars', () => {
    it('sorts largest first and computes ratio against the axis max', () => {
        const bars = buildBars([
            { label: 'Host', value: 5 },
            { label: 'Address', value: 10 },
        ]);
        expect(bars.map((b) => b.label)).toEqual(['Address', 'Host']);
        // axis max rounds 10 up to 10, so the largest bar fills the track
        expect(bars[0].ratio).toBe(1);
        expect(bars[1].ratio).toBe(0.5);
    });

    it('breaks label ties deterministically', () => {
        const bars = buildBars([
            { label: 'Zebra', value: 3 },
            { label: 'Apple', value: 3 },
        ]);
        expect(bars.map((b) => b.label)).toEqual(['Apple', 'Zebra']);
    });

    it('keeps a tiny non-zero value visible', () => {
        const bars = buildBars([
            { label: 'Big', value: 50000 },
            { label: 'Tiny', value: 1 },
        ]);
        expect(bars[1].ratio).toBe(MIN_VISIBLE_RATIO);
    });

    it('draws nothing for a zero value', () => {
        const bars = buildBars([{ label: 'None', value: 0 }]);
        expect(bars[0].ratio).toBe(0);
    });

    it('folds the tail into a single Other row past the limit', () => {
        const data = Array.from({ length: 12 }, (_, i) => ({ label: `T${i}`, value: 12 - i }));
        const bars = buildBars(data, 5);
        expect(bars.length).toBe(5);
        expect(bars[4].label).toBe('Other (8)');
        // 12 rows, values 12..1; the last 8 are values 8..1 => 36
        expect(bars[4].value).toBe(36);
    });

    it('computes percent against the rendered total', () => {
        const bars = buildBars([
            { label: 'A', value: 3 },
            { label: 'B', value: 1 },
        ]);
        expect(bars[0].percent).toBe(75);
        expect(bars[1].percent).toBe(25);
    });

    it('treats negative and non-finite values as zero', () => {
        const bars = buildBars([
            { label: 'Neg', value: -4 },
            { label: 'NaN', value: NaN },
        ]);
        expect(bars.every((b) => b.value === 0)).toBe(true);
        expect(bars.every((b) => b.ratio === 0)).toBe(true);
    });

    it('survives empty input', () => {
        expect(buildBars([])).toEqual([]);
        expect(buildBars(null as never)).toEqual([]);
    });
});

describe('formatCount', () => {
    it('groups thousands and abbreviates large values', () => {
        expect(formatCount(1234)).toBe('1,234');
        expect(formatCount(12500)).toBe('12.5K');
        expect(formatCount(1_250_000)).toBe('1.3M');
    });

    it('renders an em dash for non-finite input', () => {
        expect(formatCount(Infinity)).toBe('—');
    });
});
