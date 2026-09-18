import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { DashboardComponent } from './components/dashboard/dashboard.component';

/**
 * Every top-level path here must also appear in `App.spa_route_prefixes`
 * (app.py) so a bookmarked or reloaded path-style link redirects to the hash
 * form instead of white-paging.
 */
const routes: Routes = [
    { path: '', component: DashboardComponent },
    { path: 'dashboard', component: DashboardComponent },
    { path: '**', redirectTo: '' },
];

@NgModule({
    imports: [
        RouterModule.forRoot(routes, {
            onSameUrlNavigation: 'reload',
            bindToComponentInputs: true,
            // Hash routing is NOT optional here. The app is served under a
            // per-instance service prefix (/api/services/{userPath}/v1/) with
            // <base href="./">, so path-based routes break deep links and
            // reloads: the server's index.html fallback answers asset requests
            // resolved against /v1/dashboard/ with HTML and the app never
            // boots (white page). With the route in the fragment the document
            // URL always stays at the service root.
            useHash: true,
        }),
    ],
    exports: [RouterModule],
})
export class AppRoutingModule {}
