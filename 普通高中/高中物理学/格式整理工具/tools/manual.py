#!/usr/bin/env python3
"""Hand-picked fixes applied after reformat.py.  Usage: manual.py BODY.tex OUT.tex"""
import re
import sys

lines = open(sys.argv[1], encoding='utf-8').read().split('\n')


def find(prefix, start=0):
    for i in range(start, len(lines)):
        if lines[i].startswith(prefix):
            return i
    raise SystemExit('not found: ' + prefix)


# --- front matter ------------------------------------------------------------
i = find('\\part{')
lines[:i] = ['\\frontmatter', '\\maketitle', '\\tableofcontents', '\\mainmatter']

# --- hand-written solutions / proofs -> environments ---------------------------
SOL_ENDS = [
    ('solution', '因此, 射出点与墙壁间的水平距离为', 0),
    ('solution', '由此解得 $W=-9.6', 0),
    ('solution', '由此解出 $\\Delta W=36\\unit{J}$.', 0),
    ('solution', '由此解得 $F_\\mathrm{f}=4\\unit{N}$.', 0),
    ('solution', '由此解得 $\\bar{F}=2.2G.$', 0),
    ('solution', '联立以上两式, 代入数据可得 $E_\\mathrm{p}=8', 0),
    ('solution', '\\frac{E_\\mathrm{k1}}{E_\\mathrm{k2}}=\\frac{v_1}{v_2}', 1),
]
PROOF_ENDS = [
    ('cnproof', '用第二式减去两倍的第一式', 0),
    ('cnproof', '所以 $AO=2AM$', 0),
]


def wrap(label, ends):
    pos = 0
    for env, endprefix, extra in ends:
        a = None
        for i in range(pos, len(lines)):
            if re.match(r'\\textbf\{%s\} ?(\\bre|\\ \\ \\ ) ?' % label, lines[i]):
                a = i
                break
        assert a is not None, endprefix
        b = find(endprefix, a) + extra
        rest = re.sub(r'^\\textbf\{%s\} ?(\\bre|\\ \\ \\ ) ?' % label, '', lines[a])
        lines[a] = '\\begin{%s}\n%s' % (env, rest)
        lines[b] += '\n\\end{%s}' % env
        # spacing that only imitated the environment is no longer needed
        j = b + 1
        while j < len(lines) and lines[j] in ('', '\\bigskip'):
            j += 1
        if any(l == '\\bigskip' for l in lines[b + 1:j]) or (b + 1 < len(lines) and lines[b + 1] == ''):
            del lines[b + 1:j]
        pos = b + 1


wrap('解', SOL_ENDS)
wrap('证明', PROOF_ENDS)

text = '\n'.join(lines)

# --- remaining run-in labels follow the reference notation ----------------------
text, n = re.subn(r'(?m)^\\textbf\{(分析|答案|解析|已知|求证)\} ?\\bre ?', r'\\par\\indent\\textbf{\1:} ', text)
print('run-in labels:', n)


def sub1(old, new):
    global text
    assert text.count(old) == 1, (old, text.count(old))
    text = text.replace(old, new)


# a formula that was centred with a row of \bre
m = re.search(r'(?m)^即(\\bre)+\$(.*)\$$', text)
body = m.group(2).replace('\\displaystyle', '')
text = text[:m.start()] + '即\n\\[\n' + body + '\n\\]' + text[m.end():]

sub1('弯曲的四指所指的方向就是磁感线环绕的方向.}\\bigskip', '弯曲的四指所指的方向就是磁感线环绕的方向.}\n\\bigskip')
# the old text block was 18cm wide; this figure spanned it
sub1('\\includegraphics[width=18cm]{pic/5.4-3.pdf}', '\\includegraphics[width=\\textwidth]{pic/5.4-3.pdf}')
sub1('$I=nqSv$\\ (其中', '$I=nqSv$ (其中')

open(sys.argv[2], 'w', encoding='utf-8').write(text)
