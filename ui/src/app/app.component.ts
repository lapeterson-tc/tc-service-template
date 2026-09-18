import { Component, DestroyRef, inject, OnInit, Renderer2 } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs/operators';

import {
    alert,
    arrowDown,
    arrowUp,
    check,
    chevronLeft,
    chevronRight,
    download,
    helpCircle,
    IconRegistry,
    info,
    list,
    moreVertical,
    repeat,
    sparkles,
    trash,
    upload,
} from '@tc-eng/component-library';

import { AppService } from './service/app-service/app.service';
import { PendoService } from './service/pendo-service/pendo.service';
import { ThemeService } from './service/theme-service/theme.service';
import { navSectionForUrl, NavSection } from './util/nav';

/**
 * The application shell: header, section nav, theme, and the router outlet.
 *
 * Keep feature logic OUT of here. The shell's jobs are: load /api/tc/app-config
 * once, derive the theme, keep the nav tab in sync with the route, and host
 * the outlet.
 */
@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit {
    appConfig$ = this.appService.appConfigSubject.asObservable();

    /** Which header nav tab reads as active for the current route. */
    activeNav: NavSection = 'dashboard';

    appVersion?: string;
    logoImage: string = 'assets/images/TCLogo_LightTheme.svg';
    appTheme: 'light' | 'dark' = 'light';

    private destroyRef = inject(DestroyRef);

    constructor(
        private appService: AppService,
        private iconRegistry: IconRegistry,
        private pendoService: PendoService,
        private router: Router,
        private themeService: ThemeService,
        private renderer: Renderer2,
    ) {
        this.iconRegistry.registerIcons([
            alert,
            arrowDown,
            arrowUp,
            check,
            chevronLeft,
            chevronRight,
            download,
            helpCircle,
            info,
            list,
            moreVertical,
            repeat,
            sparkles,
            trash,
            upload,
        ]);
    }

    ngOnInit() {
        this.pendoService.initializePendo();
        this.appService.loadConfig();
        this.appService.appConfigSubject
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe((config) => (this.appVersion = config?.ui?.version));

        // Keep the nav tab in sync with the route. routerLinkActive can't do
        // this: the default tab links to '/', which non-exact-matches every
        // URL and exact-matches nothing under a child route.
        this.activeNav = navSectionForUrl(this.router.url);
        this.router.events
            .pipe(
                filter((e) => e instanceof NavigationEnd),
                takeUntilDestroyed(this.destroyRef),
            )
            .subscribe((e) => {
                this.activeNav = navSectionForUrl((e as NavigationEnd).urlAfterRedirects);
            });

        // ThreatConnect stores the signed-in user's theme preference in
        // localStorage; honour it so the app matches the platform chrome it is
        // embedded in. Absent (e.g. `ng serve`) means light.
        const permissions = localStorage.getItem('tc.permissions');
        if (permissions) {
            try {
                const userPermissions = JSON.parse(permissions);
                this.appTheme = userPermissions?.settingUser?.uiTheme === 'Dark' ? 'dark' : 'light';
            } catch {
                this.appTheme = 'light';
            }
            if (this.appTheme === 'dark') {
                this.themeService.setTheme(this.appTheme);
            }
        }
        this.applyTheme(this.appTheme);

        this.themeService.theme$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((theme) => {
            this.applyTheme(theme);
        });
    }

    generatePendoFeature() {
        return `Service Template (${this.appVersion})`;
    }

    toggleTheme(): void {
        this.themeService.setTheme(this.appTheme === 'light' ? 'dark' : 'light');
    }

    /**
     * Single writer for the body theme class.
     *
     * Every colour in the app resolves from a token that flips on `body.dark`
     * (assets/styles/*.css), so this class is the only thing that needs to
     * change — components should never carry their own dark-mode overrides.
     */
    private applyTheme(theme: 'light' | 'dark'): void {
        this.renderer.removeClass(document.body, 'light');
        this.renderer.removeClass(document.body, 'dark');
        this.renderer.addClass(document.body, theme);
        this.appTheme = theme;
        this.logoImage =
            theme === 'dark'
                ? 'assets/images/TCLogo_DarkTheme.svg'
                : 'assets/images/TCLogo_LightTheme.svg';
    }
}
