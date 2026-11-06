"""Build backend/tests/fixtures/server_exchange_reference.json (phase 0 step 3).

The server's exchange evaluator (xiangqi-server ``xiangqi_server/api/util/exchange.py``)
runs unmodified, imported from SERVER_ROOT. That directory needs only the
evaluator's own imports. The lab's phase-0 notes use a minimal local shim, which
must never be committed here. This script contains no server code, and the
fixture records only inputs and the server's outputs.

Sampling:
- positions: public/data capturing-tactics fens, the first 1,500 checkmate lines
  and the first 40 Fake Human games;
- seed 20261105;
- 8,000 captures and 2,000 quiet moves.

Every sampled move is written out, not only the diffs. The script also compares
each value with xq_classify.exchange on the pure board and writes any mismatch
to DIFFS.

Usage, from the repository root:
    python backend/scripts/build_server_exchange_reference.py . <SERVER_ROOT>         backend/tests/fixtures/server_exchange_reference.json <DIFFS.json>
"""
import collections
import json
import random
import sys
import time

LAB, SHIM, OUT, DIFFS = sys.argv[1:5]
sys.path[:0] = [f'{LAB}/backend', SHIM]
from xq_classify import board as b  # noqa: E402  pure generator, the package default
from xq_classify.exchange import evaluate_exchange as lab_eval  # noqa: E402
from xiangqi_server.api.util.exchange import evaluate_exchange as srv_eval  # noqa: E402

assert b.current_backend().name == 'pure'
START = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1'
SEED, CAPTURES = 20261105, 8000
rng = random.Random(SEED)
fens = set()
for p in json.load(open('public/data/capturing-tactics.json', encoding='utf-8'))['puzzles']:
    fens.update(p.get('fens') or [])
for p in json.load(open('public/data/checkmate-puzzles.json', encoding='utf-8'))['puzzles'][:1500]:
    if p['importStatus'] == 'invalid':
        continue
    f = p['initialFen']
    for m in [p['blunderMove'], *p['pv']]:
        fens.add(f)
        try:
            f = b.apply_move(f, m)
        except b.BoardError:
            break
for g in json.load(open('public/data/fake-human-games.json', encoding='utf-8'))['games'][:40]:
    f = START
    for m in g['moves']:
        fens.add(f)
        try:
            f = b.apply_move(f, m)
        except b.BoardError:
            break
fens = sorted(f for f in fens if 'K' in f.split()[0] and 'k' in f.split()[0])
rng.shuffle(fens)


def up(m: str) -> str:
    return f'{m[0]}{int(m[1]) + 1}{m[2]}{int(m[3]) + 1}'


cases = []
for f in fens:
    try:
        moves = b.legal_moves(f)
    except b.BoardError:
        continue
    position = b.parse_fen(f)
    caps = [m for m in moves if m[2:] in position and position[m[2:]].upper() != 'K']
    quiet = [m for m in moves if m[2:] not in position]
    cases += [(f, m, 'capture') for m in caps]
    cases += [(f, m, 'quiet') for m in rng.sample(quiet, min(1, len(quiet)))]
caps = [c for c in cases if c[2] == 'capture']
quiet = [c for c in cases if c[2] == 'quiet']
sample = rng.sample(caps, min(CAPTURES, len(caps))) + rng.sample(quiet, min(CAPTURES // 4, len(quiet)))
print(f'positions={len(fens)} capture_moves={len(caps)} sample={len(sample)}', flush=True)

rows, diffs, kinds, t0 = [], [], collections.Counter(), time.time()
for i, (f, m, kind) in enumerate(sample, 1):
    lab, server = lab_eval(f, m), srv_eval(f, up(m))
    if server != int(server):
        raise SystemExit(f'non-integer server value {server!r} for {f} {m}')
    rows.append([f, m, kind, int(server)])
    kinds[(kind, 'same' if lab == server else 'diff')] += 1
    if lab != server:
        diffs.append({'fen': f, 'move': m, 'kind': kind, 'lab': lab, 'server': server})
    if i % 2000 == 0:
        print(f'{i} done, {len(diffs)} diffs, {time.time() - t0:.0f}s', flush=True)
print(dict(kinds), 'elapsed', round(time.time() - t0))

fixture = {
    'comment': (
        "Exchange values computed by xiangqi-server's xiangqi_server/api/util/exchange.py, "
        'run unmodified through a local '
        'pyffish shim. Upstream outputs, not human labels: if xq_classify.exchange disagrees, the two '
        'implementations have diverged. Moves are this project\'s 0-9 UCCI ranks; the server was given '
        'the same moves in its 1-10 ranks. No server source is included.'
    ),
    'source': {
        'serverFile': 'xiangqi_server/api/util/exchange.py',
        'serverFileSha256Lf': '1d894f60834a24b4a497d520484fb8fb12c9f59bab0714f559ae6a915aa0a592',
        'sampling': {
            'seed': SEED,
            'captures': CAPTURES,
            'quiet': CAPTURES // 4,
            'positions': len(fens),
            'from': [
                'public/data/capturing-tactics.json fens',
                'public/data/checkmate-puzzles.json first 1500 lines',
                'public/data/fake-human-games.json first 40 games',
            ],
        },
    },
    'fields': ['fen', 'move', 'kind', 'server'],
    'cases': rows,
}
with open(OUT, 'w', encoding='utf-8', newline='\n') as handle:
    handle.write(json.dumps({k: v for k, v in fixture.items() if k != 'cases'}, ensure_ascii=False, indent=1)[:-2])
    handle.write(',\n "cases": [\n')
    handle.write(',\n'.join('  ' + json.dumps(row, ensure_ascii=False) for row in rows))
    handle.write('\n ]\n}\n')
json.dump(diffs, open(DIFFS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.loads(open(OUT, encoding='utf-8').read())  # the hand-assembled file must parse
print('wrote', OUT, len(rows), 'cases;', len(diffs), 'diffs')
