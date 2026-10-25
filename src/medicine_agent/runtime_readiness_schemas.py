"""Single standard-library source for package-external readiness JSON Schemas."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path


def _object(properties, required=None):
    return {'type':'object','additionalProperties':False,'properties':properties,
            'required':list(properties) if required is None else required}


def _array(items, **bounds):
    return dict(type='array',items=items,**bounds)


def _enum(*values):
    return dict(type='string',enum=list(values))


def schemas():
    text={'type':'string'}
    nonempty={'type':'string','minLength':1}
    count={'type':'integer','minimum':0}
    digest={'type':'string','pattern':'^[0-9a-f]{64}$'}
    diagnostics=_array({'type':'string','pattern':'^[A-Z][A-Z0-9_]*$'},uniqueItems=True)
    status=_enum('passed','blocked','not_evaluated')
    unchecked={'const':'not_evaluated'}
    nullable={'type':['string','null']}
    filename={'type':'string','pattern':r'^[A-Za-z0-9_.-]+\.onnx$'}
    distribution=_object(dict(name=nonempty,version=nullable,python_status=_enum('passed','not_evaluated','incompatible')))
    requirement=_object(dict(parent=nonempty,name=nonempty,requirement=nonempty,
                             extras=_array(nonempty,uniqueItems=True),
                             status=_enum('passed','not_applicable','not_evaluated','missing','incompatible'),installed_version=nullable))
    environment=_object(dict(version={'const':'0.1.0'},contract={'const':'environment-preflight'},status=status,
        python=nonempty,implementation=text,os=text,architecture=text,
        project=_object(dict(name={'const':'medicine-agent'},version=nullable,
                             source=_enum('unknown','installed_metadata','editable','local_directory','archive','other_direct_source'))),
        distributions=_array(distribution,maxItems=500),requirements=_array(requirement,maxItems=5000),
        diagnostic_codes=diagnostics,version_snapshot=_array(nonempty,maxItems=500),
        offline_cache=unchecked,runtime_imports=unchecked,model_resources=unchecked,reproducible_lock={'const':False}))
    wheel=_object(dict(name=nonempty,version=nonempty,
        filename={'type':'string','pattern':r'^[^/\\]+\.whl$'},bytes=count,sha256=digest))
    wheelhouse=_object(dict(contract={'const':'wheelhouse-readiness'},version={'const':'0.1.0'},status=status,
        metadata_resolution=_enum('passed','not_evaluated'),wheels=_array(wheel,maxItems=500),
        missing=_array(nonempty,maxItems=500,uniqueItems=True),diagnostic_codes=diagnostics,
        installation=unchecked,native_runtime=unchecked,model_resources=unchecked,supply_chain_trust=unchecked))
    resource_row=_object(dict(role=_enum('det','cls','rec'),filename=filename,status=_enum('passed','blocked'),sha256=digest,bytes=count),['role','filename','status'])
    resource_row.update({'if':{'properties':{'status':{'const':'passed'}}},'then':{'required':['sha256','bytes']}})
    resources=_object(dict(contract={'const':'ocr-resources'},version={'const':'0.1.0'},backend={'const':'rapidocr'},
        backend_version=nullable,status=status,models=_array(resource_row,maxItems=3),diagnostic_codes=diagnostics,
        native_runtime=unchecked,inference=unchecked,license=unchecked,supply_chain_trust=unchecked))
    description=_object(dict(contract={'const':'ocr-resource-description'},version={'const':'0.1.0'},backend={'const':'rapidocr'},
        backend_version=nonempty,files=_object({'config.yaml':digest,'default_models.yaml':digest}),
        models=_array(_object(dict(role=_enum('det','cls','rec'),filename=filename,
                                  bytes={'type':'integer','minimum':1,'maximum':512*1024*1024},sha256=digest)),minItems=3,maxItems=3,uniqueItems=True)))
    result={}
    for name,value in [('EnvironmentPreflightReport',environment),('WheelhouseReadinessReport',wheelhouse),
                       ('OCRResourceReport',resources),('OCRResourceDescription',description)]:
        result[name]=dict(value, title=name, **{'$schema':'https://json-schema.org/draft/2020-12/schema',
                                              '$id':f'urn:medicine-agent:runtime-readiness:0.1.0:{name}'})
    return deepcopy(result)


def export_runtime_schemas(output_root):
    output_root=Path(output_root)
    written={}
    def write(path,value):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8',newline='\r\n')
    for name,value in schemas().items():
        relative=f'common/{name}.schema.json'
        path=output_root/relative
        write(path,value)
        written[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
    index=dict(contract_set='runtime-readiness',contract_version='0.1.0',files=dict(sorted(written.items())))
    write(output_root/'schema-index.json',index)
    return index


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(export_runtime_schemas(args.output_dir),indent=2))


if __name__=='__main__':
    main()
