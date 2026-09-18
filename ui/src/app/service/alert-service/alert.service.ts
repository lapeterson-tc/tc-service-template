import { BehaviorSubject } from 'rxjs';

import { Injectable } from '@angular/core';

import { IAlertMessage } from '../../models/alerts/alert-message.model';

@Injectable({
    providedIn: 'root',
})
export class AlertService {
    private _snackAlerts = new BehaviorSubject<IAlertMessage>(null);
    public snackAlerts$ = this._snackAlerts.asObservable();

    addAlertMessage(newMessage: IAlertMessage) {
        this._snackAlerts.next(newMessage);
    }
}
