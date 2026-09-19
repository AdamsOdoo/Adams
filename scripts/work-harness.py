#!/usr/bin/env python3
"""Adams adapter to a separately provided, exact private toolkit checkout.

No download credentials or private resources are stored in this repository.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]


def git(root, *args):
    return subprocess.check_output(
        ['git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE, timeout=30
    ).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'doctor', 'test'])
    parser.add_argument('--metadata-only', action='store_true')
    args, rest = parser.parse_known_args()
    config = json.loads((PROJECT / '.odoo-harness/connection.json').read_text())
    revision = config['toolkit_commit']
    if (config['schema_version'] != 1 or config['mode'] != 'external-private'
            or config['application_repository'] != 'AdamsOdoo/Adams'
            or config['toolkit_repository'] != 'MostafaEssamm12/Odoo'
            or config['scope'] != 'development-only'
            or not re.fullmatch('[0-9a-f]{40}', revision)):
        raise ValueError('Invalid connection metadata')
    origin = git(PROJECT, 'remote', 'get-url', 'origin').removesuffix('.git')
    if origin not in ('https://github.com/AdamsOdoo/Adams', 'git@github.com:AdamsOdoo/Adams'):
        raise ValueError('Application origin mismatch')
    if args.metadata_only:
        if args.command != 'check' or rest:
            raise ValueError('--metadata-only is limited to check')
        print(json.dumps({'status': 'metadata-valid', 'runtime_verified': False, **config}))
        return 0
    supplied = os.environ.get('ODOO_HARNESS_HOME')
    if not supplied:
        raise ValueError('Set ODOO_HARNESS_HOME to the separately authenticated private checkout')
    root = Path(supplied).resolve()
    if root.is_relative_to(PROJECT) or PROJECT.is_relative_to(root):
        raise ValueError('Application and toolkit must be separate checkouts')
    expected_origins = ('https://github.com/MostafaEssamm12/Odoo', 'git@github.com:MostafaEssamm12/Odoo')
    if (git(root, 'remote', 'get-url', 'origin').removesuffix('.git') not in expected_origins
            or git(root, 'rev-parse', 'HEAD') != revision or git(root, 'status', '--porcelain')):
        raise ValueError('Toolkit origin, exact revision or clean-worktree check failed')
    if args.command == 'check':
        if rest:
            raise ValueError('Unexpected check arguments')
        skills = sorted(p.parent.name for p in (root / '.agents/skills').glob('*/SKILL.md'))
        if len(skills) != 8:
            raise ValueError('Expected eight toolkit skills')
        print(json.dumps({'status': 'external-resources-verified', 'toolkit_commit': revision,
                          'skills': skills, 'runtime_verified': False}, indent=2))
        return 0
    if args.command == 'doctor':
        if rest:
            raise ValueError('Unexpected doctor arguments')
        return subprocess.call([sys.executable, '-m', 'odoo_harness', 'doctor'], cwd=root)
    protected = ('--candidate', '--expected-commit')
    if any(x.startswith('--') and any(flag.startswith(x.split('=')[0]) for flag in protected)
           for x in rest):
        raise ValueError('The adapter binds candidate and expected commit; do not override them')
    if git(PROJECT, 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Commit candidate changes before running Odoo tests')
    return subprocess.call([sys.executable, str(root / 'runtime/run_project.py'),
                            '--candidate', str(PROJECT), '--expected-commit',
                            git(PROJECT, 'rev-parse', 'HEAD'), *rest], cwd=root)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (KeyError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print('Harness setup error: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
