import { tap } from 'rxjs';

import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { BehaviorSubject } from 'rxjs/internal/BehaviorSubject';

import { AppConfig } from './app.interface';

@Injectable({
    providedIn: 'root',
})
export class AppService {
    apiUrl: string = 'api/tc';

    public appConfigSubject = new BehaviorSubject<AppConfig>(null);

    constructor(private http: HttpClient) {}

    public loadConfig() {
        this.http
            .get<AppConfig>(`${this.apiUrl}/app-config`)
            .pipe(tap((config) => this.appConfigSubject.next(config)))
            .subscribe();
    }
}
