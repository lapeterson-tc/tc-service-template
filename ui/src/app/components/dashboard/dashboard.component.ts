import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { AlertType } from '@tc-eng/component-library';

import { AlertService } from '../../service/alert-service/alert.service';
import { AppService } from '../../service/app-service/app.service';
import {
    DashboardResponse,
    RecentIndicator,
} from '../../service/example-service/example.interface';
import { ExampleService } from '../../service/example-service/example.service';
import { Bar, buildBars, formatCount } from '../../util/bar-scale';

type SortKey = 'dateAdded' | 'summary' | 'type' | 'ownerName' | 'threatAssessScore';

/**
 * EXAMPLE PAGE -- replace this with your own feature.
 *
 * It exists to demonstrate the shape of a routed page in this template:
 *
 * - The page owns its scroll (`:host { overflow-y: auto }`). The shell is
 *   pinned to the viewport and the document never scrolls, so a page that
 *   forgets this silently clips everything past the fold.
 * - It renders a soft `error` from a 200 response instead of assuming success.
 * - It has real empty / loading / error states; "no data" is information, not
 *   a blank screen.
 * - Chart math lives in `util/bar-scale.ts` so it can be unit-tested; this
 *   class is wiring.
 * - Derived view state (`bars`, `sortedRecent`) is recomputed into FIELDS, not
 *   exposed as getters. A getter that builds a fresh array runs on every
 *   change-detection pass and rebuilds every row.
 */
@Component({
    selector: 'app-dashboard',
    templateUrl: './dashboard.component.html',
    styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit {
    readonly dayOptions = [7, 30, 90, 365];
    readonly formatCount = formatCount;

    days = 30;
    loading = true;
    /** Soft error from the backend, or a transport failure message. */
    error: string | null = null;
    data: DashboardResponse | null = null;

    bars: Bar[] = [];
    sortedRecent: RecentIndicator[] = [];
    sortKey: SortKey = 'dateAdded';
    sortAsc = false;

    /** True once app-config confirms Bedrock is available. */
    aiEnabled = false;
    aiLoading = false;
    aiSummary: string | null = null;
    aiError: string | null = null;

    private destroyRef = inject(DestroyRef);

    constructor(
        private alertService: AlertService,
        private appService: AppService,
        private exampleService: ExampleService,
    ) {}

    ngOnInit(): void {
        this.appService.appConfigSubject
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe((config) => (this.aiEnabled = config?.bedrock === true));

        // Saved preferences decide the initial window; a failure here must not
        // stop the page loading, so fall through to the defaults either way.
        this.exampleService
            .getPreferences()
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe({
                next: (prefs) => {
                    this.days = prefs?.days ?? this.days;
                    this.sortKey = (prefs?.sort as SortKey) ?? this.sortKey;
                    this.sortAsc = prefs?.sortAsc ?? this.sortAsc;
                    this.load();
                },
                error: () => this.load(),
            });
    }

    load(): void {
        this.loading = true;
        this.error = null;
        this.aiSummary = null;
        this.aiError = null;
        this.exampleService
            .getDashboard(this.days)
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe({
                next: (data) => {
                    this.loading = false;
                    this.data = data;
                    this.error = data?.error ?? null;
                    this.bars = buildBars(
                        (data?.byType ?? []).map((d) => ({ label: d.type, value: d.count })),
                    );
                    this.applySort();
                },
                error: (err) => {
                    this.loading = false;
                    this.data = null;
                    this.bars = [];
                    this.sortedRecent = [];
                    this.error = err?.message || 'Could not load the dashboard.';
                },
            });
    }

    onDaysChange(days: number): void {
        this.days = Number(days) || 30;
        this.savePrefs();
        this.load();
    }

    sortBy(key: SortKey): void {
        if (this.sortKey === key) {
            this.sortAsc = !this.sortAsc;
        } else {
            this.sortKey = key;
            // Dates and scores read best newest/highest first; text reads A-Z.
            this.sortAsc = key !== 'dateAdded' && key !== 'threatAssessScore';
        }
        this.applySort();
        this.savePrefs();
    }

    /** Distinct types present in the current window. */
    get typeCount(): number {
        return this.data?.byType?.length ?? 0;
    }

    trackByLabel(_index: number, bar: Bar): string {
        return bar.label;
    }

    trackByRow(_index: number, row: RecentIndicator): string {
        return `${row.type}|${row.summary}|${row.ownerName}`;
    }

    /** Severity band for a 0-1000 ThreatAssess score; drives the score pill. */
    scoreBand(score: number | null): string {
        if (score == null) return 'none';
        if (score <= 200) return 'low';
        if (score <= 500) return 'med';
        if (score <= 800) return 'high';
        return 'crit';
    }

    summarizeWithAi(): void {
        if (!this.aiEnabled || !this.data) return;
        this.aiLoading = true;
        this.aiError = null;
        this.exampleService
            .askAi('Summarize this indicator activity for a threat analyst.', {
                windowDays: this.data.days,
                totalIndicators: this.data.totalCount,
                countsByType: this.data.byType.map((d) => `${d.type}: ${d.count}`),
                mostRecent: this.data.recent
                    .slice(0, 20)
                    .map((r) => `${r.type} ${r.summary} (${r.ownerName})`),
            })
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe({
                next: (res) => {
                    this.aiLoading = false;
                    this.aiSummary = res?.summary ?? null;
                    this.aiError = res?.error ?? null;
                },
                error: (err) => {
                    this.aiLoading = false;
                    this.aiError = err?.message || 'The AI summary could not be generated.';
                },
            });
    }

    private applySort(): void {
        const rows = [...(this.data?.recent ?? [])];
        const key = this.sortKey;
        const dir = this.sortAsc ? 1 : -1;
        rows.sort((a, b) => {
            const av = a[key];
            const bv = b[key];
            if (av == null && bv == null) return 0;
            // Missing values sort last in either direction: an absent score is
            // not a low score.
            if (av == null) return 1;
            if (bv == null) return -1;
            if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
            return String(av).localeCompare(String(bv)) * dir;
        });
        this.sortedRecent = rows;
    }

    private savePrefs(): void {
        this.exampleService
            .savePreferences({ days: this.days, sort: this.sortKey, sortAsc: this.sortAsc })
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe({
                // A failed save must be visible -- silently losing a setting is
                // worse than an unsaved one the user knows about.
                error: () =>
                    this.alertService.addAlertMessage({
                        message: 'Your view settings could not be saved.',
                        alertIcon: AlertType.Warning,
                    }),
            });
    }
}
