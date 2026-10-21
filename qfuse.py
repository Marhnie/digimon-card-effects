"""RRF fusion of the retriever cosine and the 2-gram Jaccard (E31). Drop-in for server/app.py /api/search.

    from qfuse import Fuser
    F = Fuser(QA, DOC)                      # once: 2-gram sets of the official questions
    hits = F.hits(q, cos_scores, k)         # cos_scores aligned with DOC  ->  [{'i': qa_index, 's': rrf, 'cos': .., 'jac': ..}]
Same fusion as train/fuse_eval.py 'rrf' (k=60): 1/(60+rank_cos) + 1/(60+rank_jac).
"""
import re
import numpy as np


def _bg(s):
    t = re.sub(r'\s+', '', s)
    return {t[i:i + 2] for i in range(len(t) - 1)}


class Fuser:
    def __init__(self, QA, DOC, k0=60):
        self.DOC, self.k0 = DOC, k0
        self.BG = [_bg(QA[i][1]) for i in DOC]

    def jac(self, q):
        A = _bg(q)
        return np.array([len(A & B) / ((len(A) + len(B) - len(A & B)) or 1) for B in self.BG], dtype=np.float32)

    def hits(self, q, cos, k=10):
        cos = np.asarray(cos, dtype=np.float32); jc = self.jac(q)
        rk = lambda s: np.argsort(np.argsort(-s, kind='stable'), kind='stable') + 1
        f = 1 / (self.k0 + rk(cos)) + 1 / (self.k0 + rk(jc))
        o = np.argsort(-f, kind='stable')[:k]
        return [{'i': self.DOC[j], 's': round(float(f[j]), 5), 'cos': round(float(cos[j]), 4), 'jac': round(float(jc[j]), 4)} for j in o]
