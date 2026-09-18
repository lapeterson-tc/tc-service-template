/**
 * Top-level sections in the app header nav.
 *
 * Add a member here for every top-level route, then add a matching case to
 * `navSectionForUrl`, a tab to app.component.html, and the route's first
 * segment to `App.spa_route_prefixes` in app.py.
 */
export type NavSection = 'dashboard' | '';

/**
 * Resolve which header nav tab should read as active for a router URL.
 *
 * This exists instead of `routerLinkActive` because the default tab links to
 * '/', which non-exact-matches every URL and exact-matches nothing under a
 * child route — so a detail page would either light up every tab or none.
 * Matching is segment-aware so a future `/dashboards-archive` route can't
 * light up the `/dashboard` tab.
 */
export function navSectionForUrl(url: string): NavSection {
    const path = (url || '').split('?')[0].split('#')[0];

    if (path === '' || path === '/') return 'dashboard';
    if (isUnder(path, '/dashboard')) return 'dashboard';
    return '';
}

function isUnder(path: string, prefix: string): boolean {
    return path === prefix || path.startsWith(`${prefix}/`);
}

/**
 * The app's own absolute location, without hash or query.
 *
 * The service is reached through ThreatConnect's proxy under a per-instance
 * path and has no way to know its own external URL, so the client reports it.
 * If you ever send this to the server to build a link (a notification, an
 * email), the SERVER must validate it against a known host before trusting
 * it — an unvalidated client-supplied URL in a message users trust is a
 * phishing primitive.
 */
export function uiBaseUrl(loc: { origin: string; pathname: string } = window.location): string {
    return `${loc.origin}${loc.pathname}`;
}
