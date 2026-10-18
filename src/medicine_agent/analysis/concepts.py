"""Non-destructive candidate concept views; all source assertions remain distinct."""
import unicodedata
from collections import defaultdict
from medicine_agent.domain.ids import stable_id


def concept_groups(index):
    labels = defaultdict(set)
    for key, record in index.items():
        for text in [record['node']['title'], *record['node']['aliases']]:
            label = ' '.join(unicodedata.normalize('NFKC',text).casefold().split())
            if label:
                labels[label].add(key)
    return [{'concept_id':stable_id('concept',{'label':label}), 'label':label,
             'members':[{'package_id':pid,'node_id':nid} for pid,nid in sorted(keys)],
             'status':'candidate','matching_method':'normalized_title_or_alias'}
            for label,keys in sorted(labels.items()) if len(keys)>1]


def _normalize(value):
    return ''.join(ch for ch in unicodedata.normalize('NFKC',value).casefold() if ch.isalnum())


def _bigrams(value):
    value=_normalize(value)
    return {value[i:i+2] for i in range(len(value)-1)} if len(value)>1 else set()


def concept_candidates(index, seeds, *, excluded=(), limit=50):
    """Find review candidates without creating or merging medical relationships."""
    seeds=sorted(set(seeds));excluded=set(excluded);records=[];seen=set()
    for source_key in seeds:
        source=index.get(source_key)
        if source is None:continue
        source_names={_normalize(v):v for v in [source['node']['title'],*source['node']['aliases']] if _normalize(v)}
        source_topics=set(source['node'].get('topics') or [])
        source_text=' '.join(source_names)
        for target_key,target in sorted(index.items()):
            if target_key==source_key or target_key[0]==source_key[0]:continue
            pair=tuple(sorted((source_key,target_key)))
            if pair in seen or pair in excluded:continue
            target_names={_normalize(v):v for v in [target['node']['title'],*target['node']['aliases']] if _normalize(v)}
            exact=set(source_names)&set(target_names)
            target_topics=set(target['node'].get('topics') or [])
            shared_topics=source_topics&target_topics
            left,right=_bigrams(source_text),_bigrams(' '.join(target_names))
            lexical=len(left&right)/len(left|right) if left|right else 0
            if exact:
                kind,score,terms='exact_name',1.0,[source_names[v] for v in sorted(exact)]
                rationale='标题或别名规范化后相同；仅是同定义候选，仍需核对各自原文和适用条件'
            elif shared_topics and lexical>=.2:
                kind,score,terms='topic_and_lexical',round(min(.89,.45+lexical/2),3),sorted(shared_topics)
                rationale='主题相同且名称存在词形重叠；可能相关但不能据此判为同义'
            elif lexical>=.55 and min(map(len,[source_text,''.join(target_names)]),default=0)>=2:
                kind,score,terms='lexical_overlap',round(min(.84,lexical),3),[]
                rationale='名称存在较高词形重叠；可能是异名、上下位或相关命题，须人工/证据复核'
            else:continue
            seen.add(pair)
            records.append({'source':source['address'],'target':target['address'],'candidate_type':kind,
                'score':score,'matched_terms':terms,'rationale':rationale,'status':'candidate'})
    return sorted(records,key=lambda x:(-x['score'],x['source']['package_id'],x['source']['node_id'],
                                       x['target']['package_id'],x['target']['node_id']))[:limit]
