"""E52: the prompt of our own 「AI 의견」 model — shared by train/train_gen.py (training) and server/ai_opinion.py (serving)."""
import re

SYSTEM = ('당신은 디지몬 카드게임(한국판)의 룰 판정 보조입니다. 주어진 카드 문구와 가까운 공식 Q&A만 근거로, '
          '공식 Q&A 답변처럼 답하세요. 네/아니요로 답할 수 있으면 「네,」 또는 「아니요,」로 시작하고 이유를 1~3문장으로 씁니다. '
          '근거가 부족하면 「판단할 근거가 부족합니다.」로 시작하세요.')
clean = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s or '').strip()


def prompt(x, QA, k=4):
    """x: {question, card, card_name, effect, card_text, neighbours:[{id, card, question}]}; QA: test_data4 qa rows (answers by id)"""
    card = f"{x.get('card', '')} {x.get('card_name', '')}\n효과: {x.get('effect') or ''}\n카드 전체: {(x.get('card_text') or '')[:700]}"
    nb = []
    for n in (x.get('neighbours') or [])[:k]:
        i = n['id']
        ans = clean(QA[i][2])[:300] if 0 <= i < len(QA) else ''
        nb.append(f"- [{n.get('card', '')}] Q: {n['question'][:260]}\n  A: {ans}")
    return f"질문: {x['question']}\n\n카드:\n{card}\n\n가까운 공식 Q&A:\n" + ('\n'.join(nb) if nb else '(없음)')


# E53: question translator — community wording -> official Q&A wording (the judge engine is most accurate on official wording)
TSYSTEM = ('당신은 디지몬 카드게임 질문을 공식 Q&A 문체로 옮기는 번역기입니다. 판정이나 답은 쓰지 말고, 질문만 공식 문체로 다시 쓰세요. '
           '선택한 카드는 「이 카드」로, 다른 카드는 「카드번호 이름」으로, 타이밍은 【등장 시】처럼, 키워드는 《블로커》처럼 씁니다. '
           '줄임말·별명은 공식 명칭으로 풀고, 원문에 없는 상황은 덧붙이지 마세요.')


def tprompt(x):
    return f"선택한 카드: {x.get('card', '')} {x.get('card_name', '')}\n질문: {x['source']}"
