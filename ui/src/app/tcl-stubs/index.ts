/**
 * Local stubs for @tc-eng/component-library.
 *
 * Each TCL component is replaced with a minimal stub that accepts the same
 * inputs/outputs and renders children via <ng-content>. This lets the app
 * compile and run without the private GitLab registry.
 */

/* eslint-disable @angular-eslint/component-selector, @angular-eslint/directive-selector,
   @angular-eslint/no-output-on-prefix, @angular-eslint/no-input-rename */

import {
    Component,
    Directive,
    EventEmitter,
    Injectable,
    Input,
    NgModule,
    Output,
} from '@angular/core';
import { CommonModule } from '@angular/common';

// ── Enums & types ────────────────────────────────────────

export enum ButtonTheme {
    Primary = 'primary',
    Secondary = 'secondary',
    Tertiary = 'tertiary',
    Quaternary = 'quaternary',
    Danger = 'danger',
}

export enum AlertType {
    Success = 'success',
    Error = 'error',
    Warning = 'warning',
    Info = 'info',
}

export enum MenuItemType {
    Default = 'default',
    Danger = 'danger',
}

export enum CheckboxState {
    Checked = 'checked',
    Unchecked = 'unchecked',
    Indeterminate = 'indeterminate',
}

export enum IconTheme {
    Default = 'default',
    Light = 'light',
    Dark = 'dark',
}

// ── Icon stubs ───────────────────────────────────────────

const iconStub = { name: '', data: '' };
export const alert = { ...iconStub, name: 'alert' };
export const arrowDown = { ...iconStub, name: 'arrow-down' };
export const arrowUp = { ...iconStub, name: 'arrow-up' };
export const check = { ...iconStub, name: 'check' };
export const chevronLeft = { ...iconStub, name: 'chevron-left' };
export const chevronRight = { ...iconStub, name: 'chevron-right' };
export const download = { ...iconStub, name: 'download' };
export const helpCircle = { ...iconStub, name: 'help-circle' };
export const info = { ...iconStub, name: 'info' };
export const list = { ...iconStub, name: 'list' };
export const moreVertical = { ...iconStub, name: 'more-vertical' };
export const repeat = { ...iconStub, name: 'repeat' };
export const sparkles = { ...iconStub, name: 'sparkles' };
export const trash = { ...iconStub, name: 'trash' };
export const upload = { ...iconStub, name: 'upload' };
export const caretDown = { ...iconStub, name: 'caret-down' };
export const caretRight = { ...iconStub, name: 'caret-right' };
export const copy = { ...iconStub, name: 'copy' };
export const alertCircle = { ...iconStub, name: 'alert-circle' };
export const alertTriangle = { ...iconStub, name: 'alert-triangle' };
export const checkCircle = { ...iconStub, name: 'check-circle' };
export const dragHandle = { ...iconStub, name: 'drag-handle' };
export const history = { ...iconStub, name: 'history' };
export const plus = { ...iconStub, name: 'plus' };

@Injectable({ providedIn: 'root' })
export class IconRegistry {
    registerIcons(_icons: any[]): void {}
}

// ── Stub components ──────────────────────────────────────

@Component({
    selector: 'tcl-button',
    template:
        '<button [disabled]="disabled" (click)="onClick.emit($event)"><ng-content></ng-content></button>',
})
export class TclButtonStub {
    @Input() disabled: any;
    @Input() theme: any;
    @Input() featureVersion: any;
    @Input() size: any;
    @Output() onClick = new EventEmitter<any>();
}

@Component({
    selector: 'tcl-icon-button',
    template:
        '<button [disabled]="disabled" (click)="onClick.emit($event)"><ng-content></ng-content></button>',
})
export class TclIconButtonStub {
    @Input() disabled: any;
    @Input() icon: any;
    @Input() theme: any;
    @Input() featureVersion: any;
    @Output() onClick = new EventEmitter<any>();
}

@Component({
    selector: 'tcl-svg-icon',
    template: '<span class="tcl-icon-stub"></span>',
})
export class TclSvgIconStub {
    @Input() name: any;
    @Input() theme: any;
}

@Component({
    selector: 'tcl-tabs',
    template: '<div class="tcl-tabs-stub"><ng-content></ng-content></div>',
})
export class TclTabsStub {
    @Input() containerTabs: any;
    @Input() isCollapsible: any;
    @Input() tabsRight: any;
    @Input() verticalLayout: any;
    @Output() onTabChange = new EventEmitter<number>();
}

@Component({
    selector: 'tcl-tab-item',
    template: '',
})
export class TclTabItemStub {
    @Input() tabTitle: any;
    @Input() active: any;
    @Input() feature: any;
}

@Component({
    selector: 'tcl-toggle',
    template:
        '<label><input type="checkbox" (change)="toggle.emit($event)"><ng-content></ng-content></label>',
})
export class TclToggleStub {
    @Input() color: any;
    @Input() label: any;
    @Input() size: any;
    @Input() textPos: any;
    @Output() toggle = new EventEmitter<any>();
}

@Component({
    selector: 'tcl-text-input',
    template: '<input [placeholder]="placeholder" [disabled]="disabled" />',
})
export class TclTextInputStub {
    @Input() placeholder: any;
    @Input() disabled: any;
    @Input() label: any;
    @Input() value: any;
    @Input() type: any;
    @Input() error: any;
    @Input() required: any;
    @Input() showClearTextIcon: any;
    @Input() showCount: any;
    @Output() onInputChange = new EventEmitter<any>();
    @Output() valueChange = new EventEmitter<any>();
    clear(): void {}
}
export { TclTextInputStub as TextInputComponent };

@Component({
    selector: 'tcl-table',
    template: '<table><ng-content></ng-content></table>',
})
export class TclTableStub {
    @Input() data: any;
    @Input() columns: any;
    @Input() rows: any;
    @Input() value: any;
    @Input() paginator: any;
    @Input() responsive: any;
    @Input() rowsPerPageOptions: any;
    @Input() expandedRowKeys: any;
}

@Component({
    selector: 'tcl-collapsible-card',
    template: '<div class="tcl-card-stub"><ng-content></ng-content></div>',
})
export class TclCollapsibleCardStub {
    @Input() collapsed: any;
    @Input() collapsible: any;
    @Input() opened: any;
    @Output() collapseToggle = new EventEmitter<any>();
}

@Component({
    selector: 'tcl-card',
    template: '<div class="tcl-card-stub"><ng-content></ng-content></div>',
})
export class TclCardStub {}

@Component({
    selector: 'tcl-header',
    template: '<div class="tcl-header-stub"><ng-content></ng-content></div>',
})
export class TclHeaderStub {}

@Component({
    selector: 'tcl-dropdown-v2',
    template: '<select><ng-content></ng-content></select>',
})
export class TclDropdownV2Stub {
    @Input() options: any;
    @Input() selections: any;
    @Input() placeholder: any;
    @Input() label: any;
    @Input() menuItems: any;
    @Input() readOnly: any;
    @Output() onSelectionChange = new EventEmitter<any>();
}

@Component({
    selector: 'tcl-dropdown',
    template: '<select><ng-content></ng-content></select>',
})
export class TclDropdownStub {
    @Input() options: any;
    @Input() featureVersion: any;
    @Input() isThin: any;
    @Output() onSelectionChange = new EventEmitter<any>();
}

@Component({
    selector: 'tcl-dropdown-button',
    template: '<div><ng-content></ng-content></div>',
})
export class TclDropdownButtonStub {
    @Input() theme: any;
    @Input() label: any;
    @Input() featureVersion: any;
}

@Component({
    selector: 'tcl-menu-item',
    template:
        '<!-- eslint-disable @angular-eslint/template/click-events-have-key-events, @angular-eslint/template/interactive-supports-focus -- dev-only stub -->' +
        '<div (click)="onClick.emit($event)"><ng-content></ng-content></div>',
})
export class TclMenuItemStub {
    @Input() type: any;
    @Input() label: any;
    @Output() onClick = new EventEmitter<any>();
}

@Component({
    selector: 'tcl-loading-spinner',
    template: '<span>Loading...</span>',
})
export class TclLoadingSpinnerStub {
    @Input() size: any;
}

@Component({
    selector: 'tcl-loading-icon',
    template: '<span>...</span>',
})
export class TclLoadingIconStub {
    @Input() size: any;
}

@Component({
    selector: 'tcl-edit-buttons',
    template:
        '<div><button (click)="onSave.emit()">Save</button><button (click)="onCancel.emit()">Cancel</button></div>',
})
export class TclEditButtonsStub {
    @Input() disabled: any;
    @Input() featureVersion: any;
    @Input() addDeleteBtn: any;
    @Input() disableSave: any;
    @Input() editModeActive: any;
    @Output() onSave = new EventEmitter<any>();
    @Output() onCancel = new EventEmitter<any>();
}

@Component({
    selector: 'tcl-badge',
    template: '<span class="tcl-badge-stub"><ng-content></ng-content></span>',
})
export class TclBadgeStub {
    @Input() value: any;
    @Input() theme: any;
}

@Component({
    selector: 'tcl-side-drawer',
    template: '<div [class.open]="opened"><ng-content></ng-content></div>',
})
export class TclSideDrawerStub {
    @Input() opened: any;
    @Input() open: any;
    @Input() title: any;
    @Input() titleText: any;
    @Output() onDrawerClose = new EventEmitter<any>();
}

@Component({
    selector: 'tcl-modal',
    template: '<div><ng-content></ng-content></div>',
})
export class TclModalStub {
    @Input() opened: any;
    @Output() onClose = new EventEmitter<any>();
}

@Component({
    selector: 'tcl-radio-button',
    template: '<label><input type="radio" /><ng-content></ng-content></label>',
})
export class TclRadioButtonStub {
    @Input() checked: any;
    @Input() name: any;
    @Input() value: any;
    @Output() onSelect = new EventEmitter<any>();
}

@Component({
    selector: 'tcl-textarea',
    template: '<textarea><ng-content></ng-content></textarea>',
})
export class TclTextareaStub {
    @Input() value: any;
    @Input() placeholder: any;
    @Output() valueChange = new EventEmitter<any>();
}

@Component({
    selector: 'tcl-counter',
    template: '<span><ng-content></ng-content></span>',
})
export class TclCounterStub {
    @Input() value: any;
}

@Component({
    selector: 'tcl-breadcrumb',
    template: '<nav><ng-content></ng-content></nav>',
})
export class TclBreadcrumbStub {
    @Input() model: any;
}

@Component({
    selector: 'tcl-stepper',
    template: '<div><ng-content></ng-content></div>',
})
export class TclStepperStub {
    @Input() steps: any;
    @Input() activeStep: any;
    @Input() activeZeroIndex: any;
    @Input() featureVersion: any;
    @Input() vertical: any;
}

@Component({
    selector: 'tcl-info-tooltip',
    template: '<span><ng-content></ng-content></span>',
})
export class TclInfoTooltipStub {
    @Input() content: any;
}

// ── Stub directives ──────────────────────────────────────

@Directive({ selector: '[tclPendo]' })
export class TclPendoStub {
    @Input() feature: any;
    @Input() qa: any;
}

@Directive({ selector: '[tclFileDrop]' })
export class TclFileDropStub {
    @Output() filesSelected = new EventEmitter<any>();
}

@Directive({ selector: '[tclInputTextarea]' })
export class TclInputTextareaStub {
    @Input() featureVersion: any;
}

@Directive({ selector: '[tclTooltip]' })
export class TclTooltipStub {
    @Input() tclTooltip: any;
}

// ── All declarations ─────────────────────────────────────

const ALL_DECLARATIONS = [
    TclButtonStub,
    TclIconButtonStub,
    TclSvgIconStub,
    TclTabsStub,
    TclTabItemStub,
    TclToggleStub,
    TclTextInputStub,
    TclTableStub,
    TclCollapsibleCardStub,
    TclCardStub,
    TclHeaderStub,
    TclDropdownV2Stub,
    TclDropdownStub,
    TclDropdownButtonStub,
    TclMenuItemStub,
    TclLoadingSpinnerStub,
    TclLoadingIconStub,
    TclEditButtonsStub,
    TclBadgeStub,
    TclSideDrawerStub,
    TclModalStub,
    TclRadioButtonStub,
    TclTextareaStub,
    TclCounterStub,
    TclBreadcrumbStub,
    TclStepperStub,
    TclInfoTooltipStub,
    TclPendoStub,
    TclFileDropStub,
    TclInputTextareaStub,
    TclTooltipStub,
];

// ── Stub modules ─────────────────────────────────────────
// Each module matches the name imported in app.module.ts and declares+exports
// the relevant component(s). Using a shared declarations array keeps it DRY.

@NgModule({ declarations: ALL_DECLARATIONS, exports: ALL_DECLARATIONS, imports: [CommonModule] })
export class BadgeModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class BreadcrumbModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class ButtonModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class CollapsibleCardModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class CounterModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class DropdownButtonModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class DropdownModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class DropdownV2Module {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class EditButtonsModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class FileDropModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class IconButtonModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class InfoTooltipModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class InputTextareaDirectiveModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class LoadingIconModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class LoadingSpinnerModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class MenuItemModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class ModalModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class PendoModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class RadioButtonModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class SideDrawerModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class StepperModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class SvgIconModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class TableModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class TabsModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class TextareaModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class TextInputModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class ToggleModule {}

@NgModule({ imports: [BadgeModule], exports: [BadgeModule] })
export class TooltipModule {}
