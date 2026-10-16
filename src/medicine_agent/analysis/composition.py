"""Build private, self-contained representations before single-file publication."""
import json
import shutil
import tempfile
from pathlib import Path

from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.store import atomic_json, digest
from medicine_agent.analysis.concepts import concept_groups
from medicine_agent.domain.ids import stable_id, file_sha256
from medicine_agent.domain.learning import DerivedBundle
from medicine_agent.domain.reviews import ReviewRecord
from medicine_agent.domain.tcm_knowledge import KnowledgeAssociation
from medicine_agent.packages.bundle import read_bundle
from medicine_agent.packages.io import validate_package_path


def parts(path):
    path=Path(path)
    if (path/'bundle.json').exists():
        bundle=read_bundle(path)
        return [(path/c.path,c.active) for c in bundle.components]
    if not validate_package_path(path).valid:
        raise AnalysisError('BASE_PACKAGE_INVALID','A base package is missing or invalid')
    return [(path,True)]


def _sidecars(roots):
    result={'links':{},'reviews':{}}
    for root in roots:
        for kind,model,identity in (('links',KnowledgeAssociation,'association_id'),('reviews',ReviewRecord,'review_id')):
            for file in sorted(Path(root).rglob(kind+'/*.json')):
                if any(p.startswith('.pending') for p in file.relative_to(root).parts):continue
                if not file.resolve().is_relative_to(Path(root).resolve()):
                    raise AnalysisError('PACKAGE_PATH_INVALID','Sidecar escapes its root')
                value=json.loads(file.read_text('utf-8'))
                if set(value)!={'record','sha256'} or digest(value['record'])!=value['sha256']:
                    raise AnalysisError('BASE_HISTORY_INVALID','Association or review checksum differs')
                record=model.model_validate(value['record'])
                rid=getattr(record,identity)
                payload=record.model_dump(mode='json',exclude={identity})
                if kind=='links':
                    payload={k:payload[k] for k in ('source','target','relation','rationale')}
                if rid!=stable_id('link' if kind=='links' else 'review',payload):
                    raise AnalysisError('BASE_HISTORY_INVALID','Association or review identity differs')
                if rid in result[kind] and result[kind][rid]!=value:
                    raise AnalysisError('BASE_HISTORY_INVALID','Conflicting copies of a history record')
                result[kind][rid]=value
    return result


def compose(inputs, destination, *, contributor_id=None, base_ids=None, sidecar_roots=()):
    """Retain every source resource; only the active query view selects source versions."""
    from medicine_agent.analysis.catalog import PackageCatalog
    from medicine_agent.analysis.associations import node_index
    inputs=[Path(p) for p in inputs]
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    pool={}
    def collect(path,active):
        manifest=json.loads((path/'manifest.json').read_text('utf-8'))
        sha=file_sha256((path/'manifest.json').read_bytes())
        key=(manifest['package_id'],sha)
        if key not in pool:pool[key]=(path,active,manifest)
        return key
    chosen=set()
    for root in inputs:
        for path,active in parts(root):chosen.add(collect(path,active))
    for root in sidecar_roots:
        if (Path(root)/'bundle.json').exists():
            for path,active in parts(root):collect(path,active)
    sidecars=_sidecars([*inputs,*sidecar_roots])
    # Carry available linked sources; unavailable references remain explicitly unresolved.
    while True:
        ids={k[0] for k in chosen}
        required=set(ids)
        for value in sidecars['links'].values():
            edge=value['record'];pair={edge['source']['package_id'],edge['target']['package_id']}
            if pair & ids:required.update(pair)
        added={k for k in pool if k[0] in required}-chosen
        if not added:break
        chosen.update(added)
    stage=Path(tempfile.mkdtemp(prefix='.pending-compose-',dir=destination.parent))
    try:
        components=[]
        families={}
        ancestor_ids=set()
        for key in sorted(chosen):
            source,active,manifest=pool[key]
            relative='components/'+stable_id('component',{'package_id':key[0],'manifest_sha256':key[1]})
            target=stage/relative;target.mkdir(parents=True)
            for name in {*manifest['files'],'manifest.json'}:
                src=source/name;out=target/name
                if not src.resolve().is_relative_to(source.resolve()) or not out.resolve().is_relative_to(target):
                    raise AnalysisError('PACKAGE_PATH_INVALID','Inherited resource escapes its package')
                out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,out)
            atomic_json(target/'checksums.json',manifest['files'])
            if (source/'corrections.json').exists():
                audit=json.loads((source/'corrections.json').read_text('utf-8'))
                ancestor_ids.update(e['parent_package_id'] for e in audit['history'])
            revision=json.loads((target/'revision.json').read_text('utf-8')) if (target/'revision.json').exists() else {}
            family=revision.get('family',key[0]);sequence=revision.get('sequence',0)
            components.append({'path':relative,'package_id':key[0],'manifest_sha256':key[1],'active':active})
            if active:families.setdefault(family,[]).append((sequence,key[0],relative))
        pins={}
        allowed=set()
        for family,values in families.items():
            highest=max(v[0] for v in values);latest=[v for v in values if v[0]==highest]
            if len({v[1] for v in latest})!=1:
                raise AnalysisError('REVISION_CONFLICT','Choose one conflicting source revision before composing')
            allowed.update(v[2] for v in latest);pins[family]=latest[0][2]
        for component in components:component['active']=component['path'] in allowed
        atomic_json(stage/'.selected.json',pins)
        ids={k[0] for k in chosen};unresolved=set()
        for kind,values in sidecars.items():
            for rid,value in values.items():
                record=value['record']
                if kind=='reviews':
                    include=record['request']['target']['address']['package_id'] in ids|ancestor_ids
                else:
                    pair={record['source']['package_id'],record['target']['package_id']}
                    include=bool(pair & ids)
                    if include:unresolved.update(pair-ids)
                if include:atomic_json(stage/kind/(rid+'.json'),value)
        catalog=PackageCatalog(stage)
        index=node_index(catalog)
        active_ids={c['package_id'] for c in components if c['active']}
        groups=concept_groups({k:v for k,v in index.items() if k[0] in active_ids})
        existing={(tuple(sorted((v['record']['source'].items()))),tuple(sorted(v['record']['target'].items())))
                  for v in sidecars['links'].values()}
        for group in groups:
            source=group['members'][0]
            for target in group['members'][1:]:
                pair=(tuple(sorted(source.items())),tuple(sorted(target.items())))
                if pair in existing or pair[::-1] in existing:continue
                payload={'source':source,'target':target,'relation':'related',
                    'rationale':'标题或别名一致的候选概念关联；各来源解释独立，不代表定义完全相同'}
                record=KnowledgeAssociation(association_id=stable_id('link',payload),**payload).model_dump(mode='json')
                atomic_json(stage/'links'/(record['association_id']+'.json'),{'record':record,'sha256':digest(record)})
                existing.add(pair)
        reviews=catalog.reviews()
        if reviews['errors'] or any(s['user_review_state']=='history_invalid' for s in reviews['states'].values()):
            raise AnalysisError('BASE_HISTORY_INVALID','Review history is incomplete or conflicting')
        # Flattening source storage must not flatten away the parent packages' lineage.
        for root in inputs:
            if not (root/'bundle.json').exists():continue
            inherited=read_bundle(root)
            for name in inherited.files:
                if name.startswith('history/'):
                    target=stage/name;target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(root/name,target)
            atomic_json(stage/'history'/(inherited.bundle_id+'.json'),inherited.model_dump(mode='json'))
        files={p.relative_to(stage).as_posix():file_sha256(p.read_bytes())
               for kind in ('links','reviews','history') for p in (stage/kind).glob('*.json')}
        payload={'version':'0.1.0','contributor_id':contributor_id,'base_package_ids':sorted(set(base_ids or [])),
            'components':components,'files':files,'concept_groups':groups,
            'unresolved_package_ids':sorted(unresolved),'status':'research_candidate'}
        bundle=DerivedBundle(bundle_id=stable_id('bundle',payload),**payload)
        atomic_json(stage/'bundle.json',bundle.model_dump(mode='json'))
        read_bundle(stage)
        if destination.exists():
            if read_bundle(destination)!=bundle:
                raise AnalysisError('OUTPUT_CONFLICT','Existing composition belongs to another operation')
            return destination
        stage.rename(destination)
        return destination
    finally:
        if stage.exists() and stage.resolve().parent==destination.parent.resolve() and stage.name.startswith('.pending-compose-'):
            shutil.rmtree(stage)
