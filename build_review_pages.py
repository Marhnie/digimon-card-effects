"""effect-review.html (v4.0 gold set, storage rv) and effect-review41.html (v4.1 changed items, storage rv41) from review_template.html"""
t = open('review_template.html', encoding='utf-8').read()
for src, out, title in (('review_data.json', 'effect-review.html', '효과 분류 검수'), ('review_data41.json', 'effect-review41.html', '효과 분류 재검수')):
    d = open(src, encoding='utf-8').read().replace('</', '<\/')
    open(out, 'w', encoding='utf-8').write(t.replace('__DATA__', d, 1).replace('<title>효과 분류 검수</title>', f'<title>{title}</title>', 1))
print('ok')
