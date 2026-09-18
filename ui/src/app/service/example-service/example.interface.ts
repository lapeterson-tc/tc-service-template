export interface TypeCount {
    type: string;
    count: number;
}

export interface RecentIndicator {
    summary: string;
    type: string;
    ownerName: string;
    dateAdded: string;
    threatAssessScore: number | null;
}

export interface DashboardResponse {
    days: number;
    totalCount: number;
    byType: TypeCount[];
    recent: RecentIndicator[];
    /** 'live' when counts are exact; 'sample' when derived from the recent rows. */
    countSource: 'live' | 'sample';
    /** 'live' when the type list came from the instance; 'fallback' otherwise. */
    typeSource: 'live' | 'fallback';
    /**
     * Soft error. The backend never 500s, so a failed upstream call arrives as
     * HTTP 200 with this populated — always render it rather than assuming a
     * 200 means success.
     */
    error?: string | null;
}

export interface UserPreferences {
    days: number;
    sort: string;
    sortAsc: boolean;
    error?: string | null;
}

export interface AskAiResponse {
    summary: string | null;
    model: string | null;
    error?: string | null;
}
