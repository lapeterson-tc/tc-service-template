import { HttpErrorResponse } from '@angular/common/http';
import { ErrorHandler, Injectable } from '@angular/core';
import { AlertService } from '../service/alert-service/alert.service';
import { AlertType } from '@tc-eng/component-library';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
    constructor(private alertService: AlertService) {}

    handleError(error) {
        /**
         * Benign error ignore.
         */
        if (error.message === 'elementStates is undefined') {
            return;
        }
        if (error instanceof HttpErrorResponse) {
            if (!navigator.onLine) {
                this.alertService.addAlertMessage({
                    message: 'No internet connection.',
                    alertIcon: AlertType.Error,
                });
            } else {
                let errMsg: string;
                if (error.error) {
                    if (error.error.errorMsg) {
                        errMsg = error.error.errorMsg;
                    } else if (error.error.message) {
                        errMsg = error.error.message;
                    } else if (error.status !== undefined) {
                        errMsg = getUserFriendlyErrorForStatus(error.status);
                    } else {
                        errMsg =
                            'There was an error on the server. If the problem persists, contact technical support.';
                    }
                }
                if (
                    error.status === 500 &&
                    errMsg ===
                        'An unknown error has occurred while processing your request. Please review your request and try again. If the problem persists, contact technical support.'
                ) {
                    errMsg = getUserFriendlyErrorForStatus(500);
                }
                this.alertService.addAlertMessage({
                    message: errMsg,
                    alertIcon: AlertType.Error,
                });
            }
        } else {
            let errorMessage: string;
            if (error.message) {
                errorMessage = error.message;
            } else if (error instanceof Event) {
                if (error.target instanceof WebSocket) {
                    errorMessage = `Error connecting to the following websocket: ${error.target.url}`;
                } else if (error.srcElement) {
                    errorMessage = error.srcElement.toString();
                } else if (error.currentTarget) {
                    errorMessage = error.currentTarget.toString();
                } else if (error.target) {
                    errorMessage = error.target.toString();
                }
            }
            this.alertService.addAlertMessage({
                message:
                    errorMessage ??
                    'An unknown error has occurred.  Please make sure logged into main application',
                alertIcon: AlertType.Error,
            });
        }

        console.error('UNCAUGHT ERROR!!', error);
    }
}

const getUserFriendlyErrorForStatus = (statusCode: number): string => {
    // These HTTP Status Error Messages could probably be improved.
    switch (statusCode) {
        case 0:
            return `Communication with the server was cancelled. Please try again. If the problem persists, contact technical support.`;
        case 400:
            return `There was an error communicating with the server. Please try again. If the problem persists, contact technical support.`;
        case 401:
            return `You can't take that action without being logged in.`;
        case 403:
            return `You don't have the right permissions to take that action.`;
        case 404:
            return `That action was not able to be found. Please try again. If the problem persists, contact technical support.`;
        case 405:
            return `The application tried to send an unsupported action to the server. If the problem persists, contact technical support.`;
        case 408:
            return `It took too long to communicate with the server. Please try again. If the problem persists, contact technical support.`;
        case 409:
            return `Could not process action. There was a conflict between the local data and the data on the server. If the problem persists, contact technical support.`;
        case 410:
            return `The requested resource is no longer available. If the problem persists, contact technical support.`;
        case 413:
            return `There is not enough space configured in your organization to upload this file. Contact technical support.`;
        case 414:
            return `The URL used is too long to work, please report this error to your server admin. If the problem persists, contact technical support.`;
        case 415:
            return `The file type uploaded is not supported. Please upload a supported file type. If the problem persists, contact technical support.`;
        case 429:
            return `There are too many connections between the application and the server. Please try again later. If the problem persists, contact technical support.`;
        case 500:
            return `There was an error on the server. If the problem persists, contact technical support.`;
        default:
            return 'There was an error on the server. If the problem persists, contact technical support.';
    }
};
