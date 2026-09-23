#!/usr/bin/env python3
"""Compare independently captured reference/Odoo regions; never update baselines.

Inputs are private manifests, not business evidence committed to this repository.
Exit 0 means byte-identical rendered regions, 1 means visible review required,
2 means the captures cannot establish parity. Requires Pillow.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageEnhance

APPROVED_HTML_SHA256 = '36ec95831f3f1e82e0709594d5c177938e3b3805ccd763b1e59c13933b2d7f4a'
MATCH_FIELDS = ('browser', 'fonts', 'zoom', 'device_scale', 'theme', 'language',
                'viewport', 'content_width', 'company', 'dates', 'controls',
                'data', 'state', 'region')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_capture(manifest_path, item):
    path = (manifest_path.parent / item['file']).resolve()
    if digest(path) != item['sha256']:
        raise ValueError(f"Capture changed after recording: {item['id']}")
    with Image.open(path) as source:
        source.load()
        box = item['box']
        if len(box) != 4 or any(type(n) is not int for n in box):
            raise ValueError('box must contain four integer pixel coordinates')
        x, y, right, bottom = box
        if not (0 <= x < right <= source.width and 0 <= y < bottom <= source.height):
            raise ValueError(f"Invalid dashboard-owned crop: {item['id']}")
        return path, source.convert('RGB').crop(box)


def compare(reference_path, actual_path, output):
    reference = json.loads(reference_path.read_text())
    actual = json.loads(actual_path.read_text())
    if reference.get('role') != 'approved-reference' or actual.get('role') != 'actual-odoo':
        raise ValueError('Independent approved-reference and actual-odoo manifests required')
    if reference.get('html_sha256') != APPROVED_HTML_SHA256:
        raise ValueError('Reference does not identify the approved HTML')
    if not reference.get('adjustments'):
        raise ValueError('Explicit UI07/UI08/UI20/company reference adjustments required')
    if not actual.get('source_sha') or not actual.get('build') or not actual.get('module_versions'):
        raise ValueError('Exact Odoo candidate identity required')
    if reference_path.resolve() == actual_path.resolve():
        raise ValueError('Reference and implementation must be separate')
    if output.exists():
        raise ValueError('Output directory already exists; preserve previous evidence')
    refs = {item['id']: item for item in reference['captures']}
    acts = {item['id']: item for item in actual['captures']}
    if not refs or len(refs) != len(reference['captures']) or len(acts) != len(actual['captures']) or refs.keys() != acts.keys():
        raise ValueError('Unique, matching capture IDs required; missing states cannot pass')
    pairs = []
    for name, ref in refs.items():
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
            raise ValueError('Capture IDs must be filename-safe')
        act = acts[name]
        for field in MATCH_FIELDS:
            if field not in ref or field not in act or ref[field] != act[field]:
                raise ValueError(f'{name}: unmatched {field}; recapture matching states')
        if ref.get('masks') or act.get('masks'):
            raise ValueError('This comparator accepts unmasked captures only')
        rp, ri = load_capture(reference_path, ref)
        ap, ai = load_capture(actual_path, act)
        if rp == ap:
            raise ValueError(f'{name}: implementation cannot serve as its own baseline')
        if ri.size != ai.size:
            raise ValueError(f'{name}: region dimensions differ; do not resize to conceal geometry')
        pairs.append((name, ri, ai))
    output.mkdir(parents=True, mode=0o700)
    results = []
    for name, ref, act in pairs:
        delta = ImageChops.difference(ref, act)
        bounds = delta.getbbox()
        ref.save(output / f'{name}-reference.png')
        act.save(output / f'{name}-odoo.png')
        Image.blend(ref, act, .5).save(output / f'{name}-overlay.png')
        ImageEnhance.Contrast(delta).enhance(3).save(output / f'{name}-diff.png')
        results.append({'id': name, 'status': 'review-required' if bounds else 'exact',
                        'difference_bounds': bounds,
                        'review': 'Inspect typography, geometry, spacing, controls, wrapping and overflow. '
                                  'Rendering variation requires a written explanation; no percentage waives defects.'})
    report = {'reference_manifest_sha256': digest(reference_path),
              'actual_manifest_sha256': digest(actual_path),
              'source_sha': actual['source_sha'], 'build': actual['build'],
              'results': results,
              'status': 'review-required' if any(x['status'] != 'exact' for x in results) else 'exact'}
    (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    return 1 if report['status'] != 'exact' else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('actual', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        sys.exit(compare(args.reference, args.actual, args.output))
    except (ValueError, KeyError, OSError) as error:
        print(f'Cannot establish parity: {error}', file=sys.stderr)
        sys.exit(2)
