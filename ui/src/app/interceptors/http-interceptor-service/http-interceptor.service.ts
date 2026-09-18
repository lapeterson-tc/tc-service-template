import { Observable } from 'rxjs';

import { HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({
    providedIn: 'root',
})
export class HttpInterceptorService implements HttpInterceptor {
    intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
        let apiRequest: HttpRequest<any>;
        let baseUrl: string;
        let updatedUrl: string;
        if (request.url.startsWith('//')) {
            const updated_request_url = request.url.replace(/\/\//, '');

            // support local development
            if (window.location.hostname === 'localhost') {
                // how would you know if TC is running on localhost?

                // construct the URL to hit local API "/api/tc-proxy-local"
                // set original path as a header ???
                updatedUrl = `${window.location.origin}/api/tc/proxy-local`;
                apiRequest = request.clone({
                    url: updatedUrl,
                    setHeaders: {
                        // ...request.headers,
                        'X-Original-Path': updated_request_url,
                    },
                });
            } else {
                // support making direct API calls to the TC instance
                updatedUrl = `${window.location.origin}/${updated_request_url}`;
                apiRequest = request.clone({ url: updatedUrl });
            }
        } else {
            // Resolve the service root from the base href.
            // Strip any SPA route segments (e.g. /intel/...) by trimming
            // back to the last path component that ends with /v1/ (the TC
            // service prefix), or falling back to removing trailing /ui/...
            baseUrl = document
                .getElementsByTagName('base')[0]
                .href.replace(/ui\/.*/, '')
                .replace(/(\/v\d+\/).*/, '$1');
            updatedUrl = `${baseUrl}${request.url}`;
            apiRequest = request.clone({ url: updatedUrl });
        }
        return next.handle(apiRequest);
    }
}
