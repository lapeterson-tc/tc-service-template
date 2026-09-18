import { Pipe, PipeTransform } from '@angular/core';

import { marked } from 'marked';

/**
 * Render a markdown (or plain HTML) string to HTML for [innerHTML] binding.
 *
 * Deliberately returns a plain string, NOT SafeHtml: Angular's built-in
 * sanitizer then strips scripts/event handlers on binding. Attribute values
 * come from every owner an entity is shared with, so they are untrusted.
 */
@Pipe({ name: 'markdown' })
export class MarkdownPipe implements PipeTransform {
    transform(value: unknown): string {
        if (value == null) return '';
        try {
            return marked.parse(String(value), { breaks: true, async: false }) as string;
        } catch {
            return String(value);
        }
    }
}
