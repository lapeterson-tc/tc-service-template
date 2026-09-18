/* Create a new injection token for injecting the window into a component. */
import { ClassProvider, FactoryProvider, InjectionToken, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export const THE_WINDOW = new InjectionToken('WindowToken');

// /* Define abstract class for obtaining reference to the global window object. */
export abstract class WindowReference {
    get nativeWindow(): Window | object {
        throw new Error('Not implemented.');
    }
}

/* Define class that implements the abstract class and returns the native window object. */
export class BrowserWindowReference extends WindowReference {
    constructor() {
        super();
    }

    get nativeWindow(): Window | object {
        return window;
    }
}

/* Create an factory function that returns the native window object. */
// PLAT-6938 Allow to pass eslint b/c we don't want to change w/o testing first
export function winFactory(
    browserWindowRef: BrowserWindowReference,
    platformId: object,
): Window | object {
    if (isPlatformBrowser(platformId)) {
        return browserWindowRef.nativeWindow;
    }
    return {};
}

/* Create a injectable provider for the WindowRef token that uses the BrowserWindowRef class. */
const browserWinProvider: ClassProvider = {
    provide: WindowReference,
    useClass: BrowserWindowReference,
};

/* Create an injectable provider that uses the windowFactory function for returning the native window object. */
const winProvider: FactoryProvider = {
    provide: THE_WINDOW,
    useFactory: winFactory,
    deps: [WindowReference, PLATFORM_ID],
};

/* Create an array of providers. */
export const WIN_PROVIDERS = [browserWinProvider, winProvider];
