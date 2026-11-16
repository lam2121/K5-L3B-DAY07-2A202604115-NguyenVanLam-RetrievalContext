"""Convert an exported Day 6 chunk/benchmark JSON array to Day 7 JSON contract."""
import argparse
import json
from pathlib import Path


def convert_chunk(c):
    return {'id': c.get('id', c.get('chunk_id')), 'source_id': c.get('source_id', c.get('document_id')),
            'source': c.get('source'), 'page': c.get('page'), 'text': c.get('text'),
            'metadata': c.get('metadata', {})}


def convert_question(q):
    gold = q.get('gold')
    if gold is None:
        gold = [{'source_id': q.get('gold_source_id'), 'page': q.get('gold_page'),
                 'evidence': q.get('evidence_quote')}]
    result = {'id': q.get('id'), 'split': q.get('split'), 'question': q.get('question'),
              'gold': gold, 'expected_answer': q.get('expected_answer')}
    if 'filter' in q:
        result['filter'] = q['filter']
    return result


def align_gold_evidence(questions, chunks):
    import re
    chunk_by_page = {}
    for c in chunks:
        chunk_by_page.setdefault((c['source_id'], c['page']), []).append(c)

    for q in questions:
        for g in q.get('gold', []):
            ev = g.get('evidence')
            if not ev:
                continue
            key = (g.get('source_id'), g.get('page'))
            matching_chunks = chunk_by_page.get(key, [])
            if any(ev in c['text'] for c in matching_chunks):
                continue
            words = [re.escape(w) for w in re.split(r'\s+', ev.strip()) if w]
            pattern = r'\s+'.join(words)
            for c in matching_chunks:
                m = re.search(pattern, c['text'])
                if m:
                    g['evidence'] = m.group(0)
                    break


def main():
    parser = argparse.ArgumentParser(description='Chuyển JSON export Day 6 sang schema Day 7')
    parser.add_argument('--chunks', required=True, type=Path)
    parser.add_argument('--questions', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    raw_chunks = json.loads(args.chunks.read_text(encoding='utf-8'))
    raw_questions = json.loads(args.questions.read_text(encoding='utf-8'))
    if not isinstance(raw_chunks, list) or not isinstance(raw_questions, list):
        raise ValueError('Hai file đầu vào phải là JSON arrays')
    # Conversion does not infer missing metadata or inspect test evidence.
    chunks = [convert_chunk(c) for c in raw_chunks]
    questions = [convert_question(q) for q in raw_questions]
    align_gold_evidence(questions, chunks)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in (('chunks.json', chunks), ('questions.json', questions)):
        (args.output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Đã chuyển đổi; kiểm tra output và chạy baseline trên dev để kiểm chứng.')


if __name__ == '__main__':
    main()
