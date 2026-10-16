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
