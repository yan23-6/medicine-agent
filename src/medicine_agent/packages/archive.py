"""Single-file .medpkg transport; directory representations stay in private workspaces."""
import json
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from medicine_agent.domain.ids import file_sha256
from medicine_agent.packages.bundle import read_bundle, contained
from medicine_agent.analysis.store import process_lock

MAX_FILES = 100_000
MAX_BYTES = 8 * 1024**3
SOURCE_FILES={'sources.jsonl','fragments.jsonl','evidence.jsonl','knowledge.jsonl','relations.jsonl',
              'raw_fields.jsonl','runs.jsonl','revision.json','extensions.json','tcm.json',
              'corrections.json','ownership.json'}


def resources(root):
    bundle = read_bundle(root)
    names = {'bundle.json', *bundle.files}
    for component in bundle.components:
        manifest = json.loads((root/component.path/'manifest.json').read_text('utf-8'))
        if not set(manifest['files'])<=SOURCE_FILES:
            raise ValueError('Unsupported source resource in this package-file version')
        names.add(component.path+'/manifest.json')
        names.update(component.path+'/'+name for name in manifest['files'])
        if (root/component.path/'checksums.json').exists():
            names.add(component.path+'/checksums.json')
    return bundle, names


def unpack_archive(file, destination):
    destination = Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    try:
        with zipfile.ZipFile(file) as archive:
            infos = archive.infolist()
            if len(infos)>MAX_FILES or sum(i.file_size for i in infos)>MAX_BYTES:
                raise ValueError('Package exceeds supported archive limits')
            if not any(i.filename=='bundle.json' for i in infos):
                raise ValueError('Package archive omits its protocol header')
            seen=set()
            for item in infos:
                name=item.filename
                parts=PurePosixPath(name)
                if (not name or '\\' in name or ':' in name or parts.is_absolute() or
                    '..' in parts.parts or name in seen or item.is_dir() or
                    stat.S_ISLNK(item.external_attr >> 16) or item.flag_bits & 1):
                    raise ValueError('Unsafe or duplicate archive entry')
                seen.add(name)
                target=contained(destination,name)
                target.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(item) as source,target.open('xb') as output:
                    shutil.copyfileobj(source,output)
        bundle, expected=resources(destination)
        if expected!=seen:
            raise ValueError('Archive contains undeclared or missing resources')
        return bundle
    except Exception:
        # Only remove the newly created, verified extraction directory.
        if destination.resolve()==destination.parent.resolve()/destination.name and not destination.is_symlink():
            shutil.rmtree(destination)
        raise


def pack_archive(root, target):
    root,target=Path(root),Path(target)
    bundle,names=resources(root)
    if target.suffix.lower()!='.medpkg':
        raise ValueError('A package must be a .medpkg file')
    target.parent.mkdir(parents=True,exist_ok=True)
    handle,temp=tempfile.mkstemp(prefix='.pending-package-',suffix='.medpkg',dir=target.parent)
    os.close(handle)
    temp=Path(temp)
    try:
        with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(names):
                archive.write(contained(root,name),name)
        # Validate the completed file before it becomes discoverable.
        with tempfile.TemporaryDirectory(prefix='verify-',dir=root.parent) as verify:
            unpack_archive(temp,Path(verify)/'contents')
        with temp.open('r+b') as stream:
            os.fsync(stream.fileno())
        with process_lock(target.parent/'.package-publish.lock'):
            if target.exists():
                if file_sha256(target.read_bytes())!=file_sha256(temp.read_bytes()):
                    # ZIP timestamps can differ; compare validated content identity.
                    with tempfile.TemporaryDirectory(prefix='existing-',dir=root.parent) as verify:
                        existing=unpack_archive(target,Path(verify)/'contents')
                        if existing!=bundle:
                            raise ValueError('Existing package file belongs to different content')
                return target
            temp.rename(target)
            return target
    finally:
        temp.unlink(missing_ok=True)
