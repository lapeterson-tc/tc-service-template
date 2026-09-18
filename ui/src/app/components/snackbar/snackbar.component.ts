import {
    ChangeDetectorRef,
    Component,
    DestroyRef,
    ElementRef,
    HostListener,
    inject,
    Inject,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import {
    alertCircle,
    alertTriangle,
    AlertType,
    checkCircle,
    copy,
    IconRegistry,
    info,
} from '@tc-eng/component-library';

import { IAlertMessage } from '../../models/alerts/alert-message.model';
import { AlertService } from '../../service/alert-service/alert.service';
import { ClonerService } from '../../service/cloner-service/cloner.service';
import { THE_WINDOW } from '../../service/window-service/window.service';

interface IAlertMessageWithAlertIcon extends IAlertMessage {
    alertIconName?: string;
}

@Component({
    selector: 'app-snackbar',
    templateUrl: './snackbar.component.html',
    styleUrls: ['./snackbar.component.scss'],
})
export class SnackbarComponent {
    alertMessage: IAlertMessageWithAlertIcon;
    alerts: IAlertMessageWithAlertIcon[] = [];
    displayAlert: boolean = false;
    opened: boolean = false;

    private checkMessageTimer: number;
    private destroyRef = inject(DestroyRef);

    constructor(
        private changeDetect: ChangeDetectorRef,
        private iconRegistry: IconRegistry,
        @Inject(THE_WINDOW) private window: Window,
        private clonerService: ClonerService,
        private alertService: AlertService,
        public ref: ElementRef,
    ) {
        this.iconRegistry.registerIcons([alertCircle, alertTriangle, checkCircle, info, copy]);
        this.alertService.snackAlerts$
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe((iAlertMessage) => {
                if (iAlertMessage) {
                    this.setAlertMessage(iAlertMessage);
                }
            });
    }

    @HostListener('document:click', ['$event'])
    dismissOnClick(event): void {
        const target = event.target;
        if (
            !this.ref.nativeElement.contains(target) &&
            document.body.contains(target) &&
            event.target.id !== 'tc-test-error-handler' //TOBE: condition to be removed after testing phase
        ) {
            this.hideAlert();
        }
    }

    displayNextMessage(): void {
        if (this.alerts.length > 0) {
            this.displayAlert = true;
            this.alertMessage = this.alerts.shift();
            this.changeDetect.detectChanges();
        }
        this.setupNextCheck();
    }

    hideAlert(): void {
        this.changeDetect.detectChanges();
        this.window.setTimeout(() => this.unsetAlertMessage(), 600);
    }

    setAlertMessage(iAlertMessage: IAlertMessage): void {
        const addAlert = this.clonerService.deepClone(iAlertMessage);
        let displayAlertImmediately = false;
        if (this.alerts.length === 0) {
            displayAlertImmediately = true;
        }
        if (addAlert.alertIcon) {
            switch (addAlert.alertIcon) {
                case AlertType.Error:
                    addAlert['alertIconName'] = 'alert-circle';
                    break;
                case AlertType.Success:
                    addAlert['alertIconName'] = 'check-circle';
                    break;
                case AlertType.Warning:
                    addAlert['alertIconName'] = 'alert-triangle';
                    break;
                default:
                    addAlert['alertIconName'] = 'info';
            }
        }
        this.alerts.push(addAlert);
        if (displayAlertImmediately) {
            setTimeout(() => {
                this.displayNextMessage();
            }, 3000);
        }
    }

    setupNextCheck(): void {
        this.checkMessageTimer = this.window.setTimeout(() => this.checkForNextMessage(), 6000);
    }

    checkForNextMessage(): void {
        if (this.displayAlert) {
            this.hideAlert();
        } else if (this.alerts.length > 0) {
            this.window.setTimeout(() => this.displayNextMessage(), 1000);
        }
    }

    unsetAlertMessage(): void {
        this.alertMessage = undefined;
        this.displayAlert = false;
        this.checkForNextMessage();
        this.changeDetect.detectChanges();
    }
}
