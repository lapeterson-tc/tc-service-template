import { Injectable } from '@angular/core';

import clone from 'clone-deep';

@Injectable({ providedIn: 'root' })
export class ClonerService {
    deepClone<T>(value: T): T {
        return clone<T>(value);
    }
}
