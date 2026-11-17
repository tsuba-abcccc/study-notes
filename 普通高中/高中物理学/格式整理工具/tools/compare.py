#!/usr/bin/env python3
"""compare.py : char-level diff of verify/old.txt vs verify/new.txt (content stream order)."""
import difflib, sys, collections
base = sys.argv[1] if len(sys.argv) > 1 else 'verify'
old = open(base + '/old.txt', encoding='utf-8').read()
new = open(base + '/new.txt', encoding='utf-8').read()
fo = open(base + '/old.txt.font', encoding='utf-8').read()
fn = open(base + '/new.txt.font', encoding='utf-8').read()
# paragraph-insensitive content comparison
o = old.replace('\n', ''); n = new.replace('\n', '')
fo = fo.replace('\n', ''); fn = fn.replace('\n', '')
print('content chars old/new:', len(o), len(n))
sm = difflib.SequenceMatcher(None, o, n, autojunk=False)
kinds = collections.Counter()
diffs = []
fontdiff = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        if fo[i1:i2] != fn[j1:j2]:
            for k in range(i2 - i1):
                if fo[i1 + k] != fn[j1 + k]:
                    fontdiff += 1
                    if fontdiff <= 15:
                        print('FONT', fo[i1 + k], '->', fn[j1 + k], repr(o[max(0, i1 + k - 12):i1 + k + 12]))
        continue
    a, b = o[i1:i2], n[j1:j2]
    kinds[(a, b)] += 1
    diffs.append((a, b, o[max(0, i1 - 18):i1], o[i2:i2 + 18]))
print('font (bold) mismatches on equal text:', fontdiff)
print('distinct diff kinds:', len(kinds), ' total diffs:', len(diffs))
for (a, b), c in kinds.most_common(60):
    print('%5d  %r -> %r' % (c, a, b))
if '--all' in sys.argv:
    for a, b, pre, post in diffs:
        print('  %s[%s => %s]%s' % (pre, a, b, post))
# paragraph structure
ol = old.split('\n'); nl = new.split('\n')
print('paragraphs old/new:', len(ol), len(nl))
