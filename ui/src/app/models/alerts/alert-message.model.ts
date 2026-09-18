import { AlertType } from '@tc-eng/component-library';

export interface IAlertMessage {
    alertIcon?: AlertType;
    dismissible?: boolean;
    errorDetails?: any;
    message: string;
    styleClass?: string;
    title?: string;
}
