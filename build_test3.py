"""test_data3.json = test_data2.json + issue-group id per Q&A (field 10, qa_labels_0.25.npy from qa_group.py)."""
import json, numpy as np
d = json.loads(open('test_data2.json', encoding='utf-8').read().replace('<\/', '</'))
lab = np.load('qa_labels_0.25.npy'); assert len(lab) == len(d['qa'])
for row, g in zip(d['qa'], lab): row.append(int(g))
open('test_data3.json', 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\/'))
print(len(d['units']), len(d['qa']))
