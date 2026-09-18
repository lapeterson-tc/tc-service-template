import { BehaviorSubject } from 'rxjs';

import { Injectable } from '@angular/core';

@Injectable({
    providedIn: 'root',
})
export class ThemeService {
    private _theme = new BehaviorSubject<'light' | 'dark'>('light');
    public theme$ = this._theme.asObservable();

    get currentTheme(): 'light' | 'dark' {
        return this._theme.value;
    }

    toggleTheme(): void {
        const next = this._theme.value === 'light' ? 'dark' : 'light';
        this.setTheme(next);
        // Sync body class so global CSS picks it up.
        document.body.classList.remove('light', 'dark');
        document.body.classList.add(next);
    }

    setTheme(theme: 'light' | 'dark') {
        this._theme.next(theme);
    }
}
