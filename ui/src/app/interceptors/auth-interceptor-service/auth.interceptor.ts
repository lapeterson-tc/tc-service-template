import {
    HttpErrorResponse,
    HttpEvent,
    HttpHandler,
    HttpInterceptor,
    HttpRequest,
} from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AlertService } from '../../service/alert-service/alert.service';
import { AlertType } from '@tc-eng/component-library';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
    constructor(private alertService: AlertService) {}

    intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
        return next.handle(request).pipe(
            catchError((error: HttpErrorResponse) => {
                if (error.status === 401) {
                    this.alertService.addAlertMessage({
                        message: 'You have been logged out. To continue log back in.',
                        alertIcon: AlertType.Error,
                    });
                }

                return throwError(() => error);
            }),
        );
    }
}
