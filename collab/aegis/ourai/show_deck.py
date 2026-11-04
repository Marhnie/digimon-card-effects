"""python -X utf8 show_deck.py deck.json|-  : decklist with Korean names (card_effects/cards.json) when known, English otherwise."""
import collections, json, sys
K = {c['no']: c['name'] for c in json.load(open('C:/Users/Daewonmedia/card_effects/cards.json', encoding='utf-8'))}
E = {c['cardId']: c for c in json.load(open('C:/Users/Daewonmedia/aegis_engine/packages/shared/dist/cards/data/cards.json', encoding='utf-8'))}


def show(deck, base=None):
    cnt = collections.Counter(deck['mainDeck'])
    old = collections.Counter(base['mainDeck']) if base else None
    rows = []
    for cid, n in cnt.items():
        c = E.get(cid, {})
        kind = (c.get('kinds') or ['?'])[0]
        rows.append((kind, c.get('level') or 0, cid, n))
    out = []
    for kind, lv, cid, n in sorted(rows, key=lambda r: ({'Digimon': 0, 'Tamer': 1, 'Option': 2}.get(r[0], 3), r[1], r[2])):
        d = '' if old is None else f' ({n - old.get(cid, 0):+d})' if n != old.get(cid, 0) else ''
        out.append(f"{n}x {cid} {K.get(cid) or E.get(cid, {}).get('nameEn', '?')} [{kind}{' Lv' + str(lv) if lv else ''}]{d}")
    if old:
        for cid, n in old.items():
            if cid not in cnt: out.append(f"0x {cid} {K.get(cid) or E.get(cid, {}).get('nameEn', '?')} (-{n})")
    eggs = collections.Counter(deck['eggDeck'])
    out.append('디지타마: ' + ', '.join(f"{n}x {cid} {K.get(cid) or E.get(cid, {}).get('nameEn', '?')}" for cid, n in eggs.items()))
    return '\n'.join(out)


if __name__ == '__main__':
    d = json.load(sys.stdin if sys.argv[1] == '-' else open(sys.argv[1], encoding='utf-8'))
    print(show(d))
