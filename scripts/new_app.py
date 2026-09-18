#!/usr/bin/env python3
"""Rename this template into a new ThreatConnect API Service App.

Rewrites the identity fields that must be unique per app -- a fresh ``appId``
(two apps sharing one cannot both be installed on an instance), the display
name, the URL path segment, and the package name -- across every file that
carries them, and resets the version to 1.0.0.

Dry run by default; pass ``--apply`` to write.

    python3 scripts/new_app.py --name "Threat Dashboard" --path threat_dashboard
    python3 scripts/new_app.py --name "Threat Dashboard" --path threat_dashboard --apply

What it does NOT do (deliberately -- these are judgement calls):
  * delete the example feature (api/endpoint/example/, the dashboard page,
    its tests). Build your own alongside it, then remove it.
  * rewrite docs/, README.md or CLAUDE.md prose.
  * touch anything under ui/node_modules, deps/, ui_build/ or target/.
"""

# standard library
import argparse
import json
import re
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Current template identity -- what gets replaced.
OLD_DISPLAY_NAME = 'Service Template'
OLD_DISPLAY_PATH = 'service_template'
OLD_PACKAGE_NAME = 'TC_Service_Template'


def slugify_package(name: str) -> str:
    """Turn a display name into a TC package name (``TC_Threat_Dashboard``)."""
    cleaned = re.sub(r'[^A-Za-z0-9]+', ' ', name).strip()
    return 'TC_' + '_'.join(part.capitalize() for part in cleaned.split())


def valid_path(value: str) -> bool:
    """A display path becomes a URL segment; keep it boring."""
    return bool(re.fullmatch(r'[a-z0-9][a-z0-9_-]*', value))


def plan(name: str, path: str, package: str, app_id: str) -> list[tuple[Path, str, str]]:
    """Return ``(file, old_text, new_text)`` for every file to rewrite."""
    edits: list[tuple[Path, str, str]] = []

    def rewrite(rel: str, subs: list[tuple[str, str]]):
        target = REPO / rel
        if not target.is_file():
            print(f'  ! missing, skipped: {rel}', file=sys.stderr)
            return
        old = target.read_text()
        new = old
        for find, repl in subs:
            new = new.replace(find, repl)
        if new != old:
            edits.append((target, old, new))

    ident = [
        (OLD_DISPLAY_NAME, name),
        (OLD_DISPLAY_PATH, path),
        (OLD_PACKAGE_NAME, package),
    ]

    # install.json / app_spec.yml carry the appId too.
    install = REPO / 'install.json'
    spec = REPO / 'app_spec.yml'
    old_ids = set()
    for f in (install, spec):
        if f.is_file():
            old_ids.update(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', f.read_text()))

    id_subs = [(old, app_id) for old in old_ids]

    rewrite('install.json', ident + id_subs)
    rewrite('app_spec.yml', ident + id_subs)
    rewrite('tcex.json', ident)
    rewrite('ui/package.json', [(OLD_DISPLAY_PATH, path)])
    rewrite('ui/angular.json', [(OLD_DISPLAY_PATH, path)])
    rewrite('ui/src/index.html', [(OLD_DISPLAY_NAME, name)])
    rewrite('ui/src/app/app.component.ts', [(OLD_DISPLAY_NAME, name)])
    rewrite('api/endpoint/storage/transfer.py', [('tc-service-template-storage', f'{path.replace("_", "-")}-storage')])
    return edits


def reset_version() -> list[tuple[Path, str, str]]:
    """Reset programVersion to 1.0.0 in both manifests."""
    edits = []
    for rel, pattern, repl in (
        ('install.json', r'"programVersion": "[^"]+"', '"programVersion": "1.0.0"'),
        ('app_spec.yml', r'programVersion: \S+', 'programVersion: 1.0.0'),
    ):
        target = REPO / rel
        if not target.is_file():
            continue
        old = target.read_text()
        new = re.sub(pattern, repl, old)
        if new != old:
            edits.append((target, old, new))
    return edits


def merge(a: list, b: list) -> list:
    """Merge two edit lists, applying both to the same file in order."""
    by_file: dict[Path, tuple[str, str]] = {}
    for target, old, new in a + b:
        if target in by_file:
            first_old, first_new = by_file[target]
            # Re-apply this edit's transform on top of the previous result.
            by_file[target] = (first_old, new if first_new == old else first_new)
        else:
            by_file[target] = (old, new)
    return [(f, o, n) for f, (o, n) in by_file.items()]


def show(edits: list[tuple[Path, str, str]]):
    """Print a per-file summary of what would change."""
    for target, old, new in edits:
        changed = sum(1 for a, b in zip(old.splitlines(), new.splitlines()) if a != b)
        print(f'  {target.relative_to(REPO)}  ({changed} line(s) changed)')


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--name', required=True, help='Display name, e.g. "Threat Dashboard"')
    parser.add_argument(
        '--path',
        required=True,
        help='Default URL path segment, lowercase, e.g. threat_dashboard',
    )
    parser.add_argument('--package', help=f'Package name (default: derived, e.g. {slugify_package("Threat Dashboard")})')
    parser.add_argument('--app-id', help='App UUID (default: a freshly generated one)')
    parser.add_argument('--apply', action='store_true', help='Write the changes (default: dry run)')
    args = parser.parse_args()

    if not valid_path(args.path):
        print(f'error: --path must be lowercase alphanumeric/underscore/hyphen, got {args.path!r}', file=sys.stderr)
        return 2

    package = args.package or slugify_package(args.name)
    app_id = args.app_id or str(uuid.uuid4())

    print('New app identity:')
    print(f'  displayName  {args.name}')
    print(f'  displayPath  {args.path}')
    print(f'  packageName  {package}')
    print(f'  appId        {app_id}')
    print()

    edits = merge(plan(args.name, args.path, package, app_id), reset_version())
    if not edits:
        print('Nothing to change -- has this template already been renamed?')
        return 0

    print('Files to rewrite:')
    show(edits)
    print()

    if not args.apply:
        print('Dry run. Re-run with --apply to write.')
        return 0

    for target, _old, new in edits:
        target.write_text(new)
    print(f'Wrote {len(edits)} file(s).')
    print()
    print('Next:')
    print('  1. Verify install.json: python3 -c "import json;print(json.load(open(\'install.json\')))"')
    print('  2. Rebuild:  cd ui && npm install && npx ng build && cd .. && tcex deps && tcex package')
    print('  3. Replace the example feature (api/endpoint/example/, ui/.../components/dashboard/)')
    print('  4. Update README.md, CLAUDE.md and docs/ prose by hand.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
