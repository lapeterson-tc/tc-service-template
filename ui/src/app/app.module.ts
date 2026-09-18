import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { RouterModule } from '@angular/router';

import { PendoModule, SvgIconModule } from '@tc-eng/component-library';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { SnackbarComponent } from './components/snackbar/snackbar.component';
import { errorHandlerProvider } from './error-handler/error-handler.provider';
import { httpInterceptorProviders } from './interceptors/http-interceptor-providers';
import { MarkdownPipe } from './pipes/markdown/markdown.pipe';
import { WIN_PROVIDERS } from './service/window-service/window.service';

// Everything is eager and declared here -- there is no lazy loading. Declare
// new components in BOTH this file and app-routing.module.ts.
@NgModule({
    declarations: [AppComponent, DashboardComponent, MarkdownPipe, SnackbarComponent],
    bootstrap: [AppComponent],
    imports: [
        AppRoutingModule,
        BrowserAnimationsModule,
        BrowserModule,
        FormsModule,
        RouterModule,
        PendoModule,
        SvgIconModule,
    ],
    providers: [
        WIN_PROVIDERS,
        errorHandlerProvider,
        httpInterceptorProviders,
        provideHttpClient(withInterceptorsFromDi()),
    ],
})
export class AppModule {}
