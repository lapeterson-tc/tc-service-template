import { ErrorHandler } from '@angular/core';
import { GlobalErrorHandler } from './global-error-handler';

export const errorHandlerProvider = [{ provide: ErrorHandler, useClass: GlobalErrorHandler }];
