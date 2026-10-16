"""Verify a portable directory of immutable source packages and shared provenance."""
import json
from pathlib import Path
from medicine_agent.domain.ids import stable_id, file_sha256
from medicine_agent.domain.learning import DerivedBundle


def contained(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Bundle resource escapes its directory')
    return path


def read_bundle(root: Path):
    bundle = DerivedBundle.model_validate_json((root/'bundle.json').read_text('utf-8'))
    payload = bundle.model_dump(mode='json',exclude={'bundle_id'})
    if bundle.bundle_id != stable_id('bundle',payload):
        raise ValueError('Bundle identity mismatch')
    from medicine_agent.packages.io import validate_package_path
    seen, active_families, active_index = set(), {}, {}
    for component in bundle.components:
        if component.path in seen or not component.path.startswith('components/'):
            raise ValueError('Invalid component path')
        seen.add(component.path)
        path = contained(root,component.path)
        if file_sha256((path/'manifest.json').read_bytes()) != component.manifest_sha256:
            raise ValueError('Bundle component manifest changed')
        if not validate_package_path(path).valid:
            raise ValueError('Invalid bundle component')
        manifest = json.loads((path/'manifest.json').read_text('utf-8'))
        if manifest['package_id'] != component.package_id:
            raise ValueError('Bundle component identity changed')
        if component.active:
            revision = json.loads((path/'revision.json').read_text('utf-8')) if (path/'revision.json').exists() else {}
            family = revision.get('family',component.package_id)
            if family in active_families and active_families[family] != component.package_id:
                raise ValueError('Select one active version per source lane')
            active_families[family] = component.package_id
            from medicine_agent.packages.tcm import read_graph
            graph = read_graph(path)
            if graph:
                for node in graph.nodes:
                    active_index[(component.package_id,node.node_id)]={'node':node.model_dump(mode='json')}
    for relative,expected in bundle.files.items():
        path = contained(root,relative)
        if (not relative or not Path(relative).parts or Path(relative).parts[0] not in {'links','reviews','history'} or Path(relative).suffix!='.json' or
            relative in {'bundle.json','manifest.json'} or file_sha256(path.read_bytes()) != expected):
            raise ValueError('Bundle association or review data changed')
        if relative.startswith('history/'):
            previous=DerivedBundle.model_validate_json(path.read_text('utf-8'))
            if previous.bundle_id!=stable_id('bundle',previous.model_dump(mode='json',exclude={'bundle_id'})):
                raise ValueError('Inherited package lineage identity changed')
            available={(c.package_id,c.manifest_sha256) for c in bundle.components}
            if not {(c.package_id,c.manifest_sha256) for c in previous.components}<=available:
                raise ValueError('Inherited package lineage lost source content')
    recorded={c.package_id for c in bundle.components}
    recorded.update(Path(name).stem for name in bundle.files if name.startswith('history/'))
    if not set(bundle.base_package_ids)<=recorded:
        raise ValueError('Bundle lost its base-package lineage')
    from medicine_agent.analysis.concepts import concept_groups
    if [g.model_dump(mode='json') for g in bundle.concept_groups] != concept_groups(active_index):
        raise ValueError('Bundle concept membership differs from its sources')
    return bundle
