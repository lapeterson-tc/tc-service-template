import { Observable } from 'rxjs';

import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { AskAiResponse, DashboardResponse, UserPreferences } from './example.interface';

/**
 * Data access for the example feature.
 *
 * URLs here are RELATIVE (`api/example/...`). HttpInterceptorService rewrites
 * them onto the app's own service root, which it derives from <base href> at
 * request time — the app is served under a per-instance path it cannot know at
 * build time, so there is no base-URL constant to configure.
 *
 * A URL starting with `//` means something different: see TcService — it is
 * the marker for "call the ThreatConnect platform API, not this app".
 */
@Injectable({
    providedIn: 'root',
})
export class ExampleService {
    apiUrl: string = 'api/example';

    constructor(private http: HttpClient) {}

    getDashboard(days: number): Observable<DashboardResponse> {
        return this.http.get<DashboardResponse>(`${this.apiUrl}/dashboard`, {
            params: { days: String(days) },
        });
    }

    getPreferences(): Observable<UserPreferences> {
        return this.http.get<UserPreferences>(`${this.apiUrl}/preferences`);
    }

    savePreferences(prefs: UserPreferences): Observable<UserPreferences> {
        return this.http.put<UserPreferences>(`${this.apiUrl}/preferences`, prefs);
    }

    askAi(question: string, context: Record<string, unknown>): Observable<AskAiResponse> {
        return this.http.post<AskAiResponse>(`${this.apiUrl}/ask-ai`, { question, context });
    }
}
