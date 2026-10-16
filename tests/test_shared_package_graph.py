"""One active logical graph across builders without destructive source merging."""
import shutil
from medicine_agent.analysis.catalog import PackageCatalog
from medicine_agent.bootstrap import create_facade
from test_owned_analysis import prepare, update


def address(catalog, relative):
    pid=next(p['package_id'] for p in catalog.scan() if p['path']==relative)
    return next(i['target']['address'] for i in catalog.review_queue()['items'] if i['target']['address']['package_id']==pid)


def test_cross_builder_nested_links_multihop_cycle_and_migration(tmp_path):
    agent,_,a,_=prepare(tmp_path,name='a',text='起点专有原话。',owner='user-a')
    _,_,b,_=prepare(tmp_path,name='b',text='第二来源专有原话。',owner='user-b')
    _,_,c,_=prepare(tmp_path,name='c',text='第三来源专有原话。',owner='user-b')
    catalog=agent.catalog
    aa,bb,cc=[address(catalog,p) for p in (a,b,c)]
    catalog.associate(aa,bb,'related','自制跨用户关联')
    catalog.associate(bb,cc,'expands','自制二级关联')
    catalog.associate(cc,aa,'contradicts','自制循环与冲突保留')
    user_links=catalog.root/'user-b'/'links'
    user_links.parent.mkdir()
    shutil.move(str(catalog.root/'links'),user_links)
    shutil.copytree(user_links,catalog.root/'user-a'/'links')
    query=catalog.query(create_facade(),text='起点专有')
    assert len(query['related_nodes'])==2 and len(query['associations'])==3
    assert {n['package']['owner_id'] for n in query['related_nodes']}=={'user-b'}
    assert {e['raw_text'] for n in query['related_nodes'] for e in n['evidence']}=={'第二来源专有原话。','第三来源专有原话。'}
    assert len(catalog.associations()['associations'])==3
    moved=tmp_path/'moved';shutil.copytree(catalog.root,moved)
    migrated=PackageCatalog(moved)
    assert len(migrated.query(create_facade(),text='起点专有')['related_nodes'])==2
    target=moved/c
    holding=tmp_path/'holding';shutil.move(str(target),holding)
    unplugged=migrated.query(create_facade(),text='起点专有')
    assert len(unplugged['related_nodes'])==1
    assert any(e['resolution']=='target_unavailable' for e in unplugged['associations'])
    shutil.move(str(holding),target)
    assert len(migrated.query(create_facade(),text='起点专有')['related_nodes'])==2


def test_unselected_old_revision_is_reference_only_not_hidden_content(tmp_path):
    agent,source,old,_=prepare(tmp_path,name='book',units=[1])
    _,_,other,_=prepare(tmp_path,name='paper',text='联合查询独有入口。',owner='user-b')
    catalog=agent.catalog
    catalog.associate(address(catalog,old),address(catalog,other),'related','自制旧版本关联')
    result=agent.run(update(agent,source,old,[2])['task_id'])
    assert result['status']=='completed',result
    query=catalog.query(create_facade(),text='联合查询独有入口')
    assert not query['related_nodes']
    assert query['associations'][0]['resolution']=='target_inactive'
    assert query['associations'][0]['inactive_addresses']
    catalog.select(old)
    assert len(catalog.query(create_facade(),text='联合查询独有入口')['related_nodes'])==1
