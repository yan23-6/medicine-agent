"""Internal compatibility experiment for the existing single-file library API."""
import argparse
import gc
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import runpy
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
D01=ROOT/'tasks/benchmarks/b18_progress_probe.py'
assert hashlib.sha256(D01.read_bytes()).hexdigest()=='baa8a61ffbc5151bb9e97bdd14fc02fef2bd88da88504383d7d96b90168e729c'
PROTECTED=runpy.run_path(str(D01))['protected']
TOKEN='LIBJOIN_SOFTWARE_ONLY'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value): path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def files(root): return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


class SyntheticModel:
    provider='synthetic-local-software-only'
    model='b19-frozen-one-node'
    def __init__(self): self.calls=0
    def generate_json(self,*,system,user,schema):
        self.calls+=1
        value=json.loads(user)
        evidence=(value['evidence'] if isinstance(value,dict) else value)[-1]
        quote=dict(evidence_id=evidence['evidence_id'],text=evidence['raw_text'])
        return dict(nodes=[dict(node_id='local',source_id=evidence['source_id'],title='Shared synthetic concept',
            statement=evidence['raw_text'],categories=['tcm_foundation'],quotes=[quote],
            groups=[dict(group_id='g',kind='theory',facts=[dict(field_id='tcm.theory_proposition_text',
                value=evidence['raw_text'],quotes=[quote])])])])


def build(root,count):
    from medicine_agent.analysis.file_learning import FileLearningService
    from medicine_agent.packages.tcm import read_graph
    from medicine_agent.domain.ids import content_hash
    (root/'inputs').mkdir()
    records=[]
    for i in range(count):
        source=root/'inputs'/f'source-{i:04}.txt'
        source.write_text(f'{TOKEN} SOURCE{i:04}; self authored, no medical assertion.\n',encoding='utf-8')
        owner='author-a' if i%2==0 else 'author-b'
        model=SyntheticModel()
        learning=FileLearningService(root/'generation'/f'work-{i:04}',root/'knowledge',model)
        task=learning.submit(dict(paths=[str(source)],owner_id=owner,allowed_use='self-authored-software-test'))
        result=learning.run(task['task_id'])
        assert result['status']=='completed' and model.calls==1
        archive=root/'knowledge'/result['package_path']
        representation,bundle=learning.library.load(archive)
        assert len(bundle.components)==1
        component=bundle.components[0]
        graph=read_graph(representation/component.path)
        assert len(graph.nodes)==1
        node=graph.nodes[0]
        sources=[json.loads(line) for line in (representation/component.path/'sources.jsonl').read_text('utf-8').splitlines()]
        assert len(sources)==1 and sources[0]['sha256']==sha(source) and sources[0]['source_id']==node.source_id
        assert node.statement==source.read_text('utf-8').strip() and node.review_status=='unreviewed'
        records.append(dict(index=i,filename=archive.name,archive_sha256=sha(archive),bundle_id=bundle.bundle_id,
            component_id=component.package_id,node_id=node.node_id,node_sha256=content_hash(node.model_dump(mode='json')),
            source_id=node.source_id,source_sha256=sha(source),owner_id=owner))
    for key in ('source_id','source_sha256','component_id','bundle_id'):
        assert len({r[key] for r in records})==count
    save(root/'corpus.json',records)
    return records


def checked_move(source,destination,boundary):
    # Verify absolute endpoints before moving any own fixture directory/file.
    source,destination,boundary=source.resolve(),destination.resolve(),boundary.resolve()
    assert boundary.is_relative_to(ROOT) and source.is_relative_to(boundary) and destination.is_relative_to(boundary)
    assert source!=boundary and destination!=boundary and source.exists() and not destination.exists()
    destination.parent.mkdir(parents=True,exist_ok=True)
    source.rename(destination)


def validate_query(library,facade,records,expected,text=TOKEN):
    from medicine_agent.domain.ids import content_hash
    before=files(library.root)
    response=library.query(facade,text=text,max_hops=0,max_nodes=50)
    assert files(library.root)==before
    assert response['status']=='research_candidate' and response['medical_review']=='unreviewed'
    assert not response['consultation_available'] and not response['user_reviews'] and not response['review_errors']
    expected_by_key={(r['component_id'],r['node_id']):r for r in records if r['index'] in expected}
    observed={}
    for package in response['packages']:
        for raw in package['medical_nodes']:
            node={k:v for k,v in raw.items() if k!='retrieval_facets'}
            key=(package['package']['package_id'],node['node_id'])
            assert key in expected_by_key and key not in observed
            item=expected_by_key[key]
            assert content_hash(node)==item['node_sha256'] and node['source_id']==item['source_id']
            assert node['review_status']=='unreviewed' and package['package']['owner_id']==item['owner_id']
            sources=package['medical_sources']; evidence=package['medical_evidence']
            assert len(sources)==1 and sources[0]['source_id']==item['source_id'] and sources[0]['sha256']==item['source_sha256']
            assert evidence and all(e['source_id']==item['source_id'] for e in evidence)
            assert all(e['raw_text']==node['statement'] for e in evidence)
            observed[key]=item['index']
    assert set(observed)==set(expected_by_key)
    return dict(matched_nodes=len(observed),distinct_sources=len(set(observed.values())),
        owners=sorted({r['owner_id'] for r in records if r['index'] in expected}),
        identity_set=sorted([list(k) for k in observed]),
        package_files=response['package_files'],public_bytes_unchanged=True)


def worker(root,count):
    def no_network(event,args):
        if event in ('socket.connect','socket.getaddrinfo'): raise RuntimeError('NETWORK_FORBIDDEN')
    sys.addaudithook(no_network)
    from medicine_agent.analysis.library import PackageLibrary
    from medicine_agent.bootstrap import create_facade
    root.mkdir(parents=True,exist_ok=False)
    records=build(root,count)
    public=root/'knowledge'
    library=PackageLibrary(public,root/'query-cache')
    facade=create_facade()
    all_ids=set(range(count)); stages=[]
    def stage(name,expected,valid_files,bad_files,text=TOKEN):
        row=validate_query(library,facade,records,expected,text)
        good=[p for p in row['package_files'] if p['state']=='research_candidate']
        bad=[p for p in row['package_files'] if p['state']=='quarantined']
        assert len(good)==valid_files and len(bad)==bad_files
        assert {p['package_id'] for p in good}=={r['bundle_id'] for r in records if r['index'] in all_ids and (r['index']!=0 or valid_files>=count)}
        assert all(p['file']=='broken.medpkg' and p['error']=='PACKAGE_FILE_INVALID' for p in bad)
        for p in public.glob('*.medpkg'):
            if p.name=='exact-copy.medpkg': assert sha(p)==records[0]['archive_sha256']
            elif p.name=='broken.medpkg': assert p.read_bytes()==b'not a medpkg archive'
            else: assert sha(p)==next(r['archive_sha256'] for r in records if r['filename']==p.name)
        stages.append(dict(stage=name,expected_nodes=len(expected),**row))
    stage('initial-common',all_ids,count,0)
    stage('unique-source-0',{0},count,0,text='SOURCE0000')
    original=public/records[0]['filename']
    duplicate=public/'exact-copy.medpkg'
    shutil.copy2(original,duplicate)
    stage('exact-copy-deduplicated',all_ids,count+1,0)
    (public/'broken.medpkg').write_bytes(b'not a medpkg archive')
    stage('bad-file-isolated',all_ids,count+1,1)
    checked_move(original,root/'holding/original.medpkg',root)
    stage('primary-removed-copy-retains-source',all_ids,count,1)
    checked_move(duplicate,root/'holding/copy.medpkg',root)
    stage('last-copy-removed-no-stale-content',all_ids-{0},count-1,1)
    stage('removed-unique-token-absent',set(),count-1,1,text='SOURCE0000')
    checked_move(root/'holding/original.medpkg',original,root)
    stage('restored-same-identities',all_ids,count,1)
    # Copy only public delivery files. Then make original input, generation,
    # public directory and prior query workspace unavailable at their old paths.
    migrated=root/'migrated-knowledge'
    shutil.copytree(public,migrated)
    del library
    gc.collect()
    for folder in ('knowledge','inputs','generation','query-cache'):
        checked_move(root/folder,root/'retired'/folder,root)
    public=migrated
    library=PackageLibrary(public,root/'migration-fresh-cache')
    stage('migrated-copy-only-new-workspace',all_ids,count,1)
    assert not any((root/name).exists() for name in ('knowledge','inputs','generation','query-cache'))
    assert len(stages)==9
    save(root/'stages.json',stages)
    return dict(status='passed',sources=count,stages=9,independent_source_fingerprints=count,
        same_title_not_merged=True,owners_not_query_partitions=True,duplicate_deduplicated=True,
        corrupt_file_isolated=True,withdraw_restore_identity_stable=True,copy_only_migration=True,
        medical_review='unreviewed',consultation_available=False)


def suite(output,smoke):
    base=(ROOT/'artifacts/b19-d01').resolve(); output=output.resolve()
    assert base.is_relative_to(ROOT) and output.is_relative_to(base) and output!=base
    output.mkdir(parents=True,exist_ok=False)
    before=PROTECTED(); save(output/'protected-before.json',before)
    save(output/'environment.json',dict(python=sys.version,os=platform.platform(),executable=sys.executable,
        pydantic=version('pydantic'),source_sha256=sha(Path(__file__)),
        scope='single-file experimental API correctness; no latency SLO or real clinical sources'))
    counts=[2] if smoke else [1,5,20]
    results=[]; failure=None
    for count in counts:
        label=f'sources-{count}'
        try:
            child=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).resolve()),'--worker',str(count),
                '--case-root',str(output/label)],capture_output=True,text=True,encoding='utf-8',timeout=900,cwd=ROOT)
            (output/(label+'.stdout.log')).write_text(child.stdout,encoding='utf-8')
            (output/(label+'.stderr.log')).write_text(child.stderr,encoding='utf-8')
            result=json.loads(child.stdout)
            save(output/(label+'.json'),dict(result,exit_code=child.returncode))
            if child.returncode or result.get('status')!='passed': raise RuntimeError('CASE_FAILED')
            results.append(result)
        except subprocess.TimeoutExpired:
            save(output/(label+'.json'),dict(status='timeout',timeout_seconds=900))
            failure=dict(case=label,code='CASE_TIMEOUT'); break
        except Exception as exc:
            failure=dict(case=label,exception_type=type(exc).__name__,code='CASE_OR_OUTPUT_FAILED'); break
    after=PROTECTED(); save(output/'protected-after.json',after)
    passed=not failure and before==after
    save(output/'summary.json',dict(status='executed_pending_review' if passed else 'failed',smoke=smoke,
        expected_profiles=counts,completed_profiles=len(results),failure=failure,
        protected_unchanged=before==after,results=results))
    print(json.dumps(dict(output=str(output),failure=failure,completed_profiles=len(results),protected_unchanged=before==after)))
    return 0 if passed else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path); parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--worker',type=int,choices=[1,2,5,20]); parser.add_argument('--case-root',type=Path)
    args=parser.parse_args()
    if args.worker:
        try: print(json.dumps(worker(args.case_root,args.worker)))
        except Exception as exc:
            print(json.dumps(dict(status='failed',exception_type=type(exc).__name__,code=getattr(exc,'code','COMPATIBILITY_ASSERTION_FAILED'))))
            raise SystemExit(1)
    else:
        if args.output is None: parser.error('--output required')
        raise SystemExit(suite(args.output,args.smoke))


if __name__=='__main__': main()
