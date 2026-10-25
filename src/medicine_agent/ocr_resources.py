"""Local OCR file readiness; no backend imports, downloads or model execution."""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import stat

MAX_MODEL_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_CONFIG_BYTES = 4 * 1024 * 1024
DESCRIPTIONS = {'3.10.0': 'rapidocr-3.10.0.json'}


class ResourceInvalid(ValueError):
    pass


def _regular(path, directory=False):
    info = path.lstat()
    if getattr(info, 'st_file_attributes', 0) & 0x400 or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ResourceInvalid('OCR_RESOURCE_LINK_REJECTED')
    return info


def _hash(path, limit, expected_size=None):
    before = _regular(path)
    if before.st_size > limit or (expected_size is not None and before.st_size != expected_size):
        raise ResourceInvalid('OCR_RESOURCE_SIZE_INVALID')
    with path.open('rb') as stream:
        info = os.fstat(stream.fileno())
        if (info.st_ino, info.st_size, info.st_mtime_ns) != (before.st_ino, before.st_size, before.st_mtime_ns) or not stat.S_ISREG(info.st_mode):
            raise ResourceInvalid('OCR_RESOURCE_CHANGED')
        digest, count = hashlib.sha256(), 0
        while chunk := stream.read(min(1024 * 1024, limit - count + 1)):
            count += len(chunk)
            if count > limit:
                raise ResourceInvalid('OCR_RESOURCE_SIZE_INVALID')
            digest.update(chunk)
        after = os.fstat(stream.fileno())
        if (info.st_size, info.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or count != info.st_size:
            raise ResourceInvalid('OCR_RESOURCE_CHANGED')
    return digest.hexdigest()


def _verify(package_root, model_root, version, description):
    report = dict(contract='ocr-resources', version='0.1.0', backend='rapidocr', backend_version=version,
                  status='blocked', models=[], diagnostic_codes=[], native_runtime='not_evaluated',
                  inference='not_evaluated', license='not_evaluated', supply_chain_trust='not_evaluated')
    paths = {}
    try:
        if description.get('backend_version') != version or description.get('contract') != 'ocr-resource-description' or description.get('version') != '0.1.0' or description.get('backend') != 'rapidocr':
            raise ResourceInvalid('OCR_RESOURCE_DESCRIPTION_INVALID')
        config = description['files']
        models = description['models']
        if set(config) != {'config.yaml', 'default_models.yaml'} or len(models) != 3 or {m['role'] for m in models} != {'det','cls','rec'}:
            raise ResourceInvalid('OCR_RESOURCE_DESCRIPTION_INVALID')
        total = 0
        filenames = set()
        for item in models:
            filename, size, sha = item['filename'], item['bytes'], item['sha256']
            if not isinstance(filename, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+\.onnx', filename) or filename in filenames or type(size) is not int or not 0 < size <= MAX_MODEL_BYTES or not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}',sha):
                raise ResourceInvalid('OCR_RESOURCE_DESCRIPTION_INVALID')
            filenames.add(filename)
            total += size
        if total > MAX_TOTAL_BYTES:
            raise ResourceInvalid('OCR_RESOURCE_SIZE_INVALID')
        _regular(package_root, directory=True)
        for filename, sha in sorted(config.items()):
            if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):
                raise ResourceInvalid('OCR_RESOURCE_DESCRIPTION_INVALID')
            if _hash(package_root/filename, MAX_CONFIG_BYTES) != sha:
                raise ResourceInvalid('OCR_DEFAULT_CONFIG_CHANGED')
        _regular(model_root, directory=True)
        for item in models:
            path = model_root/item['filename']
            row = dict(role=item['role'], filename=item['filename'], status='blocked')
            try:
                sha = _hash(path, MAX_MODEL_BYTES, item['bytes'])
                if sha != item['sha256']:
                    raise ResourceInvalid('OCR_RESOURCE_HASH_INVALID')
                row.update(status='passed', sha256=sha, bytes=item['bytes'])
                paths[item['role']] = path
            except FileNotFoundError:
                report['diagnostic_codes'].append('OCR_RESOURCE_MISSING')
            except ResourceInvalid as exc:
                report['diagnostic_codes'].append(str(exc))
            report['models'].append(row)
        report['diagnostic_codes'] = sorted(set(report['diagnostic_codes']))
        if not report['diagnostic_codes']:
            report['status']='passed'
    except FileNotFoundError:
        report['diagnostic_codes']=['OCR_RESOURCE_MISSING']
    except ResourceInvalid as exc:
        report['diagnostic_codes']=[str(exc)]
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        report['diagnostic_codes']=['OCR_RESOURCES_INVALID']
    return report, paths if report['status']=='passed' else {}


def _local(model_root=None):
    report = dict(contract='ocr-resources',version='0.1.0',backend='rapidocr',backend_version=None,
                  status='blocked',models=[],diagnostic_codes=[],native_runtime='not_evaluated',
                  inference='not_evaluated',license='not_evaluated',supply_chain_trust='not_evaluated')
    try:
        dist=metadata.distribution('rapidocr')
        version=dist.version
        report['backend_version']=version
        if version not in DESCRIPTIONS:
            report.update(status='not_evaluated',diagnostic_codes=['OCR_BACKEND_VERSION_NOT_EVALUATED'])
            return report, {}
        description_path=Path(__file__).parent/'resources/ocr'/DESCRIPTIONS[version]
        if _regular(description_path).st_size > MAX_CONFIG_BYTES:
            raise ResourceInvalid('OCR_RESOURCE_DESCRIPTION_INVALID')
        description=json.loads(description_path.read_text('utf-8'))
        package_root=Path(dist.locate_file('rapidocr'))
        return _verify(package_root,Path(model_root) if model_root is not None else package_root/'models',version,description)
    except metadata.PackageNotFoundError:
        report['diagnostic_codes']=['OCR_BACKEND_MISSING']
    except ResourceInvalid as exc:
        report['diagnostic_codes']=[str(exc)]
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        report['diagnostic_codes']=['OCR_RESOURCES_INVALID']
    return report, {}


def inspect_ocr_resources(model_root=None):
    """Check bytes only; an alternate root is not a runtime reconfiguration."""
    return _local(model_root)[0]


def validated_model_paths():
    """Internal runtime gate: only return all default paths after verification."""
    report, paths=_local()
    if report['status']!='passed':
        raise ResourceInvalid('OCR_RESOURCES_UNAVAILABLE')
    return paths


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-root',type=Path)
    args=parser.parse_args()
    report=inspect_ocr_resources(args.model_root)
    print(json.dumps(report,ensure_ascii=True,indent=2))
    raise SystemExit(0 if report['status']=='passed' else 1)


if __name__=='__main__':
    main()
