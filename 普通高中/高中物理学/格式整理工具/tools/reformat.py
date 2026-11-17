#!/usr/bin/env python3
"""Reformat the body of 高中物理学.tex to the reference conventions.

Usage: reformat.py SRC.tex OUT_BODY.tex [--report]
Only the part between \\begin{document} and \\end{document} is processed.
"""
import re
import sys
from collections import Counter

C = r'\u3400-\u4dbf\u4e00-\u9fff'          # CJK ideographs
CP = C + r'\u3000-\u303f\uff00-\uffef\u2014\u2018\u2019\u201c\u201d\u2026\u00b7'  # + CJK punctuation

REPORT = []


def report(kind, msg):
    REPORT.append((kind, msg))


# ----------------------------------------------------------------------------
# brace helpers
# ----------------------------------------------------------------------------
def match_brace(s, i):
    """s[i] == '{' -> index of the matching '}'."""
    assert s[i] == '{', (s[max(0, i - 20):i + 20])
    depth = 0
    j = i
    while j < len(s):
        ch = s[j]
        if ch == '\\':
            j += 2
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError('unbalanced brace: ' + s[i:i + 60])


class Protector:
    """Replace spans by inert private-use placeholders and restore them later."""

    def __init__(self, open_ch, close_ch):
        self.o, self.c = open_ch, close_ch
        self.items = []

    def put(self, text):
        self.items.append(text)
        return '%s%d%s' % (self.o, len(self.items) - 1, self.c)

    def restore(self, s):
        pat = re.compile('%s(\\d+)%s' % (self.o, self.c))
        while True:
            s2 = pat.sub(lambda m: self.items[int(m.group(1))], s)
            if s2 == s:
                return s
            s = s2


# ----------------------------------------------------------------------------
# math normalisation
# ----------------------------------------------------------------------------
TEXTLIKE = r'\\(?:text|textbf|textrm|textit|textnormal|mbox|hbox|fbox|intertext|tag|label|ref|eqref)\s*\{'
STYLE_SENSITIVE = re.compile(r'\\(?:frac|tfrac|sum|int|prod|lim|max|min|binom|over|sqrt)(?![a-zA-Z])')


def depth_map(s):
    """brace depth of every character."""
    d = []
    depth = 0
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '\\' and i + 1 < len(s):
            d.extend([depth, depth])
            i += 2
            continue
        if ch == '{':
            d.append(depth)
            depth += 1
        elif ch == '}':
            depth -= 1
            d.append(depth)
        else:
            d.append(depth)
        i += 1
    return d


def norm_math(s, display):
    prot = Protector('\ue010', '\ue011')
    # protect text-mode groups inside math
    out = []
    i = 0
    pat = re.compile(TEXTLIKE)
    while True:
        m = pat.search(s, i)
        if not m:
            out.append(s[i:])
            break
        b = m.end() - 1
        e = match_brace(s, b)
        out.append(s[i:m.start()])
        out.append(prot.put(s[m.start():e + 1]))
        i = e + 1
    s = ''.join(out)

    # --- token level unification
    s = re.sub(r'\\rm\s*\{', r'\\mathrm{', s)
    s = re.sub(r'\{\\rm\s+([^{}]*)\}', r'\\mathrm{\1}', s)
    s = re.sub(r'\\ \s*\\mathrm\{', r'\\unit{', s)
    s = s.replace('^{\\prime\\prime}', "''").replace('^{\\prime}', "'").replace('^\\prime', "'")
    s = re.sub(r'\^\{\\prime ?(\d)\}', r"'^\1", s)
    s = re.sub(r'\^\{\\circ\}(?=[A-Za-z])', r'^\\circ ', s)
    s = s.replace('^{\\circ}', '^\\circ')
    s = s.replace('\\bre\\bre', '\\qquad ').replace('\\bre', '\\quad ')

    # --- white space
    s = s.replace('\t', ' ')
    s = re.sub(r' +', ' ', s)
    s = re.sub(r'(?<!\\) (?=[=+\-<>&])', '', s)          # before operators
    s = re.sub(r'(?<=[=+\-<>&]) ', '', s)                 # after operators
    s = re.sub(r'(?<![\\]), (?!\\ )', ',', s)             # after commas
    s = re.sub(r'(?<!\\) (?=\\)', '', s)                  # before a control sequence
    s = re.sub(r'\\\\ +(?![\[*])', r'\\\\', s)            # after \\
    s = re.sub(r'(?<=[{(]) ', '', s)
    s = re.sub(r'(?<!\\) (?=[})])', '', s)
    s = re.sub(r'(?<!\\) (?=[\^_])', '', s)
    s = re.sub(r'(\\(?:qquad|quad)) (?=[^a-zA-Z])', r'\1', s)
    s = '\n'.join(l.strip() for l in s.split('\n'))
    s = s.strip()

    # --- display style handling
    if display:
        if not re.search(r'\\begin\{(?!aligned|gathered|split)', s):
            dm = depth_map(s)
            res = []
            i = 0
            while i < len(s):
                if dm[i] == 0 and s.startswith('\\displaystyle', i):
                    i += len('\\displaystyle')
                    if i < len(s) and s[i] == ' ':
                        i += 1
                    continue
                if dm[i] == 0 and s.startswith('\\dfrac', i):
                    res.append('\\frac')
                    i += len('\\dfrac')
                    continue
                res.append(s[i])
                i += 1
            s = ''.join(res)
    else:
        dm = depth_map(s)
        pos = [m.start() for m in re.finditer(r'\\displaystyle|\\dfrac', s) if dm[m.start()] == 0]
        if pos and not (len(pos) == 1 and pos[0] == 0 and s.startswith('\\displaystyle')):
            firstds = [p for p in pos if s.startswith('\\displaystyle', p)]
            limit = firstds[0] if firstds else len(s)
            if STYLE_SENSITIVE.search(s[:limit]):
                report('displaystyle-kept', s)
            else:
                res = []
                i = 0
                while i < len(s):
                    if dm[i] == 0 and s.startswith('\\displaystyle', i):
                        i += len('\\displaystyle')
                        if i < len(s) and s[i] == ' ':
                            i += 1
                        continue
                    if dm[i] == 0 and s.startswith('\\dfrac', i):
                        res.append('\\frac')
                        i += len('\\dfrac')
                        continue
                    res.append(s[i])
                    i += 1
                body = ''.join(res)
                s = '\\displaystyle' + (' ' if re.match(r'[a-zA-Z]', body) else '') + body
    for bad in ('\\rm', '\\prime'):
        if re.search(re.escape(bad) + r'(?![a-zA-Z])', s):
            report('math-leftover', bad + ' :: ' + s[:120])
    return prot.restore(s)


# ----------------------------------------------------------------------------
# text normalisation (one logical paragraph / caption / heading)
# ----------------------------------------------------------------------------
UNITS = ['km/h', 'km/s', 'm/s', 'N/C', 'J/C', 'GHz', 'kHz', 'MHz', 'Hz', 'mm', 'cm', 'km', 'nm', 'kg', 'mol', 'mL',
         'min', 'kW', 'eV', 'Pa', 'm', 's', 'g', 'N', 'J', 'W', 'V', 'A', 'C', 'K', 'L', 'h', 'T']
UNIT_RE = re.compile(r'(?<![A-Za-z0-9.\\{])(\d+(?: \d{3})*(?:\.\d+)?)(?:\\ | )(' + '|'.join(re.escape(u) for u in UNITS) +
                     r')(?![A-Za-z0-9/^_}])')

REFLIKE = re.compile(r'\\(ref|eqref|pageref)\{([^{}]*)\}')
OPAQUE = re.compile(r'\\(?:label|includegraphics|hspace|vspace|input)\*?(?:\[[^\]]*\])?\{[^{}]*\}')


def split_inline_math(s):
    """yield (is_math, chunk); chunk for math excludes the dollars."""
    out = []
    i = 0
    buf = []
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == '\\' and i + 1 < n:
            buf.append(s[i:i + 2])
            i += 2
            continue
        if ch == '$':
            j = i + 1
            while j < n and s[j] != '$':
                j += 2 if s[j] == '\\' else 1
            if j >= n:
                raise ValueError('unclosed $ in: ' + s[:200])
            if buf:
                out.append((False, ''.join(buf)))
                buf = []
            out.append((True, s[i + 1:j]))
            i = j + 1
            continue
        buf.append(ch)
        i += 1
    if buf:
        out.append((False, ''.join(buf)))
    return out


def norm_text(s):
    MO, MC, RO, RC, EO, EC, OO, OC = '\ue000', '\ue001', '\ue002', '\ue003', '\ue004', '\ue005', '\ue006', '\ue007'
    pm = Protector(MO, MC)      # inline math
    pr = Protector(RO, RC)      # \ref, \pageref
    pe = Protector(EO, EC)      # \eqref
    po = Protector(OO, OC)      # opaque commands

    def protect_math(text):
        parts = []
        for is_math, chunk in split_inline_math(text):
            if is_math:
                if '\n\n' in chunk:
                    raise ValueError('blank line in inline math: ' + chunk[:100])
                parts.append(pm.put('$' + norm_math(chunk.replace('\n', ' '), display=False) + '$'))
            else:
                parts.append(chunk)
        return ''.join(parts)

    if re.search(r'\\vspace', s):
        report('vspace-in-text-removed', s[:60])
        s = re.sub(r'(?:\\par)?\\vspace\*?\{[^{}]*\}', '', s)
    s = re.sub(r'\$\\ (' + '|'.join(re.escape(u) for u in UNITS) + r')(?![A-Za-z0-9/^_}])', r'\\unit{\1}$', s)
    s = re.sub(r'(?<![A-Za-z0-9.\\{])(\d+(?:\.\d+)?)\\ \$\\mathrm\{([^{}$]*)\}\$', r'$\1\\unit{\2}$', s)
    s = protect_math(s)
    s = OPAQUE.sub(lambda m: po.put(m.group(0)), s)
    s = REFLIKE.sub(lambda m: (pe if m.group(1) == 'eqref' else pr).put(m.group(0)), s)

    # punctuation: full width -> half width, TeX quotes -> Chinese quotes
    s = s.replace('：', ':').replace('，', ',').replace('。', '.')
    s = s.replace('``', '“').replace("''", '”')
    if re.search(r"[`']", s):
        report('single-quote', s[:100])
    s = s.replace('\\ \\ \\ ', '\\bre ').replace('\\ \\ ', '\\bre ')

    # numbers with units written in text mode -> math
    def unit_sub(m):
        report('unit', m.group(0) + ' @ ' + s[max(0, m.start() - 12):m.end() + 6].replace('\n', ' '))
        return '$%s\\unit{%s}$' % (m.group(1).replace(' ', '\\,'), m.group(2))
    s = UNIT_RE.sub(unit_sub, s)
    s = re.sub(r'(\$[^$]*\\unit\{[^$]*)\$ = \$([^$]*\\unit\{[^$]*\$)', r'\1=\2', s)
    s = protect_math(s)

    s = s.replace('\t', ' ')
    s = re.sub(r' +', ' ', s)
    # ideographs <-> inline math
    s = re.sub('([%s]) ?(%s)' % (C, MO), r'\1 \2', s)
    s = re.sub('(%s) ?([%s])' % (MC, C), r'\1 \2', s)
    s = re.sub('([%s]) ?(\\\\textbf\\{%s)' % (C, MO), r'\1 \2', s)
    s = re.sub('(%s\\}) ?([%s])' % (MC, C), r'\1 \2', s)
    s = re.sub('(%s) ?(\\\\textbf\\{[%s])' % (MC, C), r'\1 \2', s)
    s = re.sub('([%s]\\}) ?(%s)' % (C, MO), r'\1 \2', s)
    # ideographs <-> latin letters / digits
    s = re.sub('([%s])([A-Za-z0-9])' % C, r'\1 \2', s)
    s = re.sub('([A-Za-z0-9%%])([%s])' % C, r'\1 \2', s)
    # references
    s = re.sub('([图表例第式节章]) (%s)' % RO, r'\1\2', s)
    s = re.sub('([%s])(%s)' % (C, RO), lambda m: m.group(0) if m.group(1) in '图表例第式节章' else m.group(1) + ' ' + m.group(2), s)
    s = re.sub('(%s) ?([%s])' % (RC, C), r'\1 \2', s)
    s = re.sub('(第%s\\d+%s) ([章节])' % (RO, RC), r'\1\2', s)
    s = re.sub('([%s]) ?(%s)' % (C, EO), r'\1 \2', s)
    s = re.sub('(%s) ?([%s])' % (EC, C), r'\1 \2', s)
    # parentheses
    s = re.sub('([%s%s])\\(' % (C, MC), r'\1 (', s)
    s = re.sub('\\)([%s%s])' % (C, MO), r') \1', s)
    s = re.sub('([%s]\\})\\(' % C, r'\1 (', s)
    s = re.sub('\\)(\\\\textbf\\{[%s])' % C, r') \1', s)
    s = re.sub(r' +(\\footnote\{)', r'\1', s)
    # space after western punctuation
    s = re.sub('([,;:?!.])([%s%s“]|\\\\textbf\\{)' % (C, MO), r'\1 \2', s)
    # no space before western punctuation
    s = re.sub(r'(?<=[^\s\\]) +([,;:?!])', r'\1', s)
    s = re.sub('(?<=[^\\s\\\\]) +(\\.)(?=\\s|$|[%s%s“])' % (C, MO), r'\1', s)
    # trailing space inside a group -> outside
    s = re.sub('([,;:.?!”]) \\}(?=[%s%s])' % (C, MO), r'\1} ', s)
    s = re.sub(r'([,;:.?!”]) \}', r'\1}', s)
    # Chinese quotes hug their neighbours
    s = re.sub('([%s]) +“' % C, r'\1“', s)
    s = re.sub('” +([%s])' % C, r'”\1', s)
    s = re.sub('“ +', '“', s)
    s = re.sub(' +”', '”', s)
    s = re.sub(r' +', ' ', s).strip()

    s = po.restore(pe.restore(pr.restore(pm.restore(s))))
    return s


# ----------------------------------------------------------------------------
# scanning the body into blocks
# ----------------------------------------------------------------------------
DENVS = ['equation*', 'equation', 'align*', 'align', 'eqnarray*', 'eqnarray', 'empheq', 'gather*', 'gather']
FENVS = ['figure', 'wrapfigure', 'table']
BEGIN_RE = re.compile(r'\\begin\{(%s)\}' % '|'.join(re.escape(e) for e in DENVS + FENVS))


def scan(body):
    blocks = []
    buf = []
    i = 0
    n = len(body)

    def flush():
        if buf:
            blocks.append(('text', ''.join(buf)))
            buf.clear()

    while i < n:
        ch = body[i]
        if ch == '\\':
            m = BEGIN_RE.match(body, i)
            if m:
                env = m.group(1)
                endtok = '\\end{%s}' % env
                j = body.index(endtok, m.end())
                flush()
                blocks.append(('float' if env in FENVS else 'denv', env, body[m.end():j]))
                i = j + len(endtok)
                continue
            if body.startswith('\\[', i):
                j = body.index('\\]', i + 2)
                flush()
                blocks.append(('denv', '[', body[i + 2:j]))
                i = j + 2
                continue
            buf.append(body[i:i + 2])
            i += 2
            continue
        if ch == '%':
            raise ValueError('comment in body near: ' + body[i:i + 80])
        if ch == '$':
            if body.startswith('$$', i):
                j = body.index('$$', i + 2)
                flush()
                blocks.append(('denv', '$$', body[i + 2:j]))
                i = j + 2
                continue
            j = i + 1
            while body[j] != '$':
                j += 2 if body[j] == '\\' else 1
            buf.append(body[i:j + 1])
            i = j + 1
            continue
        buf.append(ch)
        i += 1
    flush()
    return blocks


# ----------------------------------------------------------------------------
# display math blocks
# ----------------------------------------------------------------------------
def fmt_display(env, raw):
    """-> dict(kind, opts, body, labels, mergeable)"""
    opts = ''
    if env == 'empheq':
        m = re.match(r'\s*(\[[^\]]*\]\{[^}]*\})', raw)
        opts = m.group(1)
        raw = raw[m.end():]
    labels = re.findall(r'\\label\{([^{}]*)\}', raw)
    inline_labels = env.startswith('align')
    if not inline_labels:
        raw = re.sub(r'\\label\{[^{}]*\}', '', raw)
    if re.search(r'\\vspace\*?\{[^}]*\}', raw):
        report('vspace-in-display-removed', raw.strip()[:80])
        raw = re.sub(r'\\vspace\*?\{[^}]*\}', '', raw)
    lines = [l.strip() for l in raw.split('\n')]
    lines = [l for l in lines if l]
    if inline_labels:
        ml = []
        for l in lines:
            if ml and re.match(r'\\(label|tag)\{', l):
                ml[-1] += l
            else:
                ml.append(l)
        lines = ml
    body = norm_math('\n'.join(lines), display=True)
    tags = re.findall(r'\\tag\{[^{}]*\}', body)
    if tags and not inline_labels:
        # a \tag goes to the end of the last line
        assert len(tags) == 1
        body = re.sub(r'\s*\\tag\{[^{}]*\}\s*', '\n', body).strip()
        body = '\n'.join(l for l in body.split('\n') if l.strip())
        body += ' ' + tags[0] + ''.join('\\label{%s}' % l for l in labels)
    kind = env
    if env in ('$$', '[', 'equation*'):
        kind = '['
    elif env in ('eqnarray', 'eqnarray*'):
        assert '&' not in body, body
        kind = 'equation' if env == 'eqnarray' else '['
        report('eqnarray-converted', body[:60])
    elif env == 'align*' and not tags:
        kind = 'aligned['
    if kind == '[' and labels and not tags:
        report('label-in-unnumbered-display', str(labels))
    if kind == '[' and tags:
        inline_labels = True
    return dict(type='display', kind=kind, opts=opts, body=body, labels=labels, inline_labels=inline_labels,
                mergeable=(kind == '[' and not tags and not labels and '\\begin{' not in body and '\\\\' not in body))


def render_display(d):
    lab = '' if d['inline_labels'] else ''.join('\\label{%s}' % l for l in d['labels'])
    k = d['kind']
    if k == '[':
        return '\\[\n%s\n\\]' % d['body'] + ('\n' + lab if lab else '')
    if k == 'aligned[':
        return '\\[\n\\begin{aligned}\n%s\n\\end{aligned}\n\\]' % d['body']
    if k == 'gathered[':
        return '\\[\n\\begin{gathered}\n%s\n\\end{gathered}\n\\]' % d['body']
    if k == 'empheq':
        return '\\begin{empheq}%s%s\n%s\n\\end{empheq}' % (d['opts'], lab, d['body'])
    return '\\begin{%s}%s\n%s\n\\end{%s}' % (k, lab, d['body'], k)


# ----------------------------------------------------------------------------
# floats
# ----------------------------------------------------------------------------
def fmt_float(env, raw):
    raw = raw.replace('\t', ' ')
    if env == 'wrapfigure':
        m = re.match(r'\s*(\[[^\]]*\])?(\{[^}]*\}\{[^}]*\})', raw)
        if m.group(1):
            report('wrapfigure-lines-dropped', m.group(0).strip())
        head = '\\begin{wrapfigure}' + m.group(2)
        raw = raw[m.end():]
    else:
        m = re.match(r'\s*(\[[^\]]*\])?', raw)
        head = '\\begin{%s}[htbp]' % env
        raw = raw[m.end():]
    raw = re.sub(r'\\(?:begin|end)\{(?:centering|center)\}', '', raw)
    raw = re.sub(r'\\(?:centering|flushright)(?![a-zA-Z])', '', raw)
    elems = []          # (kind, text)
    labels = []
    i = 0
    n = len(raw)
    while i < n:
        if raw[i].isspace():
            i += 1
            continue
        m = re.compile(r'\\subfloat\[').match(raw, i)
        if m:
            # optional argument may contain math with brackets; scan to the matching ]
            j = m.end()
            depth = 0
            while not (raw[j] == ']' and depth == 0):
                if raw[j] == '{':
                    depth += 1
                elif raw[j] == '}':
                    depth -= 1
                j += 1
            cap = raw[m.end():j]
            b = raw.index('{', j)
            e = match_brace(raw, b)
            inner = re.sub(r'\s+', '', raw[b + 1:e]) if '\\includegraphics' in raw[b + 1:e] else raw[b + 1:e].strip()
            lab = re.findall(r'\\label\{([^{}]*)\}', inner)
            inner = re.sub(r'\\label\{[^{}]*\}', '', inner)
            if not re.fullmatch(r'\\includegraphics\[[^\]]*\]\{[^{}]*\}', inner):
                report('subfloat-unusual', inner[:100])
            elems.append(('sub', '\\subfloat[%s]{%s%s}' % (norm_text(cap), inner,
                                                           ''.join('\\label{%s}' % l for l in lab))))
            labels.extend(('fig', l) for l in lab)
            i = e + 1
            continue
        m = re.compile(r'\\includegraphics(\[[^\]]*\])?\{[^{}]*\}').match(raw, i)
        if m:
            elems.append(('gfx', m.group(0)))
            i = m.end()
            continue
        m = re.compile(r'\\caption\{').match(raw, i)
        if m:
            e = match_brace(raw, m.end() - 1)
            elems.append(('caption', '\\caption{%s}' % norm_text(raw[m.end():e].replace('\n', ' '))))
            i = e + 1
            continue
        m = re.compile(r'\\label\{([^{}]*)\}').match(raw, i)
        if m:
            elems.append(('label', m.group(1)))
            i = m.end()
            continue
        m = re.compile(r'\\(?:hspace|vspace)\*?\{[^{}]*\}|\\quad(?![a-zA-Z])|\\qquad(?![a-zA-Z])|\\hfill(?![a-zA-Z])|(?:\\bre)+(?![a-zA-Z])|\\\\').match(raw, i)
        if m:
            elems.append(('sep', m.group(0)))
            i = m.end()
            continue
        m = re.compile(r'\\begin\{tabular\}').match(raw, i)
        if m:
            e = raw.index('\\end{tabular}', i) + len('\\end{tabular}')
            elems.append(('tabular', fmt_tabular(raw[i:e])))
            i = e
            continue
        # unknown material: take the rest of the line
        e = raw.find('\n', i)
        e = n if e < 0 else e
        report('float-unknown', raw[i:e])
        elems.append(('raw', raw[i:e].strip()))
        i = e
    # assemble
    out = [head, '\\centering']
    kind = 'tab' if env == 'table' else 'fig'
    lab = [t for k, t in elems if k == 'label']
    if len(lab) > 1:
        report('float-multi-label', str(lab))
    caps = [t for k, t in elems if k == 'caption']
    pending_label = list(lab)
    cap_seen = False
    for idx, (k, t) in enumerate(elems):
        if k == 'label':
            if not cap_seen and caps:
                report('label-before-caption-moved', t)
            continue
        if k == 'sep' and t.startswith('\\vspace'):
            report('vspace-in-float-removed', t)
            continue
        if k == 'sep' and out and t != '\\\\' and elems[idx - 1][0] in ('sub', 'gfx'):
            out[-1] += t
            continue
        out.append(t)
        if k == 'caption':
            cap_seen = True
            for l in pending_label:
                out.append('\\label{%s}' % l)
                labels.append((kind, l))
            pending_label = []
    for l in pending_label:
        report('float-label-without-caption', l)
        out.append('\\label{%s}' % l)
        labels.append((kind, l))
    out.append('\\end{%s}' % env)
    return dict(type='float', text='\n'.join(out), labels=labels)


def fmt_tabular(raw):
    m = re.match(r'\\begin\{tabular\}(\{.*?\})\s*\n', raw)
    lines = [l.strip() for l in raw.split('\n') if l.strip()]
    res = []
    for l in lines:
        if l.startswith('\\begin{tabular}') or l.startswith('\\end{tabular}') or l == '\\hline':
            res.append(l)
            continue
        hl = ''
        if l.startswith('\\hline'):
            res.append('\\hline')
            l = l[len('\\hline'):].strip()
        cells = l
        tail = ''
        mm = re.search(r'\s*\\\\\s*(\\hline)?\s*$', cells)
        if mm:
            tail = ' \\\\'
            hl = mm.group(1) or ''
            cells = cells[:mm.start()]
        cells = re.sub(r' +', ' ', ' & '.join(norm_text(c.strip()) for c in re.split(r'(?<!\\)&', cells)))
        res.append(cells + tail)
        if hl:
            res.append(hl)
    return '\n'.join(res)


# ----------------------------------------------------------------------------
# text blocks -> items
# ----------------------------------------------------------------------------
HEAD_RE = re.compile(r'\\(part|chapter|section|subsection|subsubsection)(\*?)\{')
LINE_CMDS = re.compile(r'\\(bigskip|medskip|smallskip|newpage|clearpage|maketitle|tableofcontents|setdisplaywhitespace|'
                       r'frontmatter|mainmatter|appendix|centering|noindent)$|'
                       r'\\(pagenumbering|setlength)\{.*\}$')


def is_cjk(ch):
    return bool(re.match('[%s]' % CP, ch))


def join(a, b):
    if not a:
        return b
    if is_cjk(a[-1]) and is_cjk(b[0]):
        return a + b
    return a + ' ' + b


def process(body):
    blocks = scan(body)
    items = []
    state = dict(blank=False, open=False)

    def add(it):
        it['pre_blank'] = state['blank']
        state['blank'] = False
        items.append(it)

    for blk in blocks:
        if blk[0] == 'denv':
            d = fmt_display(blk[1], blk[2])
            add(d)
            state['open'] = False
            continue
        if blk[0] == 'float':
            add(fmt_float(blk[1], blk[2]))
            state['open'] = False
            continue
        lines = blk[1].split('\n')
        for li, line in enumerate(lines):
            st = line.strip()
            if not st:
                # the first/last pieces of a block are partial lines, not blank lines
                if 0 < li < len(lines) - 1:
                    state['blank'] = True
                    state['open'] = False
                continue
            while st:
                m = HEAD_RE.match(st)
                if m:
                    e = match_brace(st, m.end() - 1)
                    add(dict(type='heading', level=m.group(1), star=m.group(2), title=st[m.end():e]))
                    state['open'] = False
                    st = st[e + 1:].strip()
                    continue
                m = re.match(r'\\label\{([^{}]*)\}', st)
                if m and (not state['open'] or items[-1]['type'] in ('heading', 'begin')):
                    prev = items[-1]
                    if prev['type'] in ('heading', 'begin') and not state['blank']:
                        prev.setdefault('labels', []).append(m.group(1))
                    else:
                        report('stray-label', m.group(1))
                        add(dict(type='cmd', text=m.group(0)))
                    st = st[m.end():].strip()
                    continue
                m = re.match(r'\\begin\{([a-zA-Z*]+)\}((?:\[[^\]]*\])?)', st)
                if m:
                    add(dict(type='begin', env=m.group(1), opt=m.group(2)))
                    state['open'] = False
                    st = st[m.end():].strip()
                    continue
                m = re.match(r'\\end\{([a-zA-Z*]+)\}', st)
                if m:
                    add(dict(type='end', env=m.group(1)))
                    state['open'] = False
                    st = st[m.end():].strip()
                    continue
                if LINE_CMDS.match(st):
                    add(dict(type='cmd', text=st))
                    state['open'] = False
                    st = ''
                    continue
                # text; an \end{..} later on the same line closes it
                m = re.search(r'\\end\{(example|solution|enumerate|itemize|center)\}', st)
                rest = ''
                if m:
                    st, rest = st[:m.start()].strip(), st[m.start():]
                if st:
                    if st.startswith('\\item') or st.startswith('\\subparagraph'):
                        add(dict(type='item' if st.startswith('\\item') else 'para', text=st))
                        state['open'] = True
                    elif state['open'] and not state['blank'] and items[-1]['type'] in ('para', 'item'):
                        items[-1]['text'] = join(items[-1]['text'], st)
                    else:
                        add(dict(type='para', text=st))
                        state['open'] = True
                st = rest
        # a display/float follows: the paragraph is interrupted, text after it starts a new source line
        state['open'] = False
    return items


LIST_ENVS = ('enumerate', 'itemize', 'center', 'description', 'quote')
PAR_ENVS = ('example', 'solution', 'cnproof')


def need_blank(prev, cur):
    if not cur['pre_blank']:
        return False
    pt, ct = prev['type'], cur['type']
    if pt in ('heading', 'begin'):
        return False
    if ct in ('heading', 'begin', 'end', 'display', 'item'):
        return False
    if pt == 'end' and prev['env'] in PAR_ENVS:
        return False
    return True      # para/float after para/display/float/end-of-list


def render(items):
    # merge runs of plain displays into gathered
    merged = []
    for it in items:
        if (it['type'] == 'display' and it['mergeable'] and merged and merged[-1]['type'] == 'display'
                and (merged[-1].get('mergeable') or merged[-1]['kind'] == 'gathered[')):
            prev = merged[-1]
            prev['body'] = prev['body'].rstrip() + '\\\\\n' + it['body']
            prev['kind'] = 'gathered['
            prev['mergeable'] = False
            report('displays-merged', it['body'][:50])
            continue
        merged.append(it)
    items = merged

    cleaned = []
    for it in items:
        if (it['type'] == 'cmd' and it['text'].startswith('\\setlength') and cleaned
                and cleaned[-1]['type'] == 'begin' and cleaned[-1]['env'] in ('enumerate', 'itemize')):
            cleaned[-1]['opt'] = '[itemsep=0pt]'
            continue
        cleaned.append(it)
    items = cleaned

    out = []
    labels = []        # (prefix, name)
    prev = None
    for it in items:
        if prev is not None and need_blank(prev, it):
            out.append('')
        t = it['type']
        if t == 'heading':
            line = '\\%s%s{%s}' % (it['level'], it['star'], norm_text(it['title']))
            for l in it.get('labels', []):
                line += '\\label{%s}' % l
                labels.append(('chap' if it['level'] == 'chapter' else 'sec', l))
            out.append(line)
        elif t == 'begin':
            line = '\\begin{%s}%s' % (it['env'], it['opt'])
            for l in it.get('labels', []):
                line += '\\label{%s}' % l
                labels.append(('ex' if it['env'] == 'example' else it['env'], l))
            out.append(line)
        elif t == 'end':
            out.append('\\end{%s}' % it['env'])
        elif t == 'cmd':
            out.append(it['text'])
        elif t in ('para', 'item'):
            out.append(norm_text(it['text']))
        elif t == 'display':
            out.append(render_display(it))
            labels.extend(('eq', l) for l in it['labels'])
        elif t == 'float':
            out.append(it['text'])
            labels.extend(it['labels'])
        prev = it
    return '\n'.join(out) + '\n', labels


def relabel(text, labels):
    text = re.sub(r'\\(label|ref|eqref|pageref)\{([^{}]*)\}',
                  lambda m: '\\%s{%s}' % (m.group(1), re.sub(r'\s+', '', m.group(2))), text)
    labels = [(p, re.sub(r'\s+', '', n)) for p, n in labels]
    names = Counter(n for _, n in labels)
    for n, c in names.items():
        if c > 1:
            report('duplicate-label', n)
    mp = {}
    for p, n in labels:
        mp.setdefault(n, p)
    defined = set(re.findall(r'\\label\{([^{}]*)\}', text))
    for n in defined - set(mp):
        report('label-unclassified', n)
        mp[n] = 'item'
    used = set(re.findall(r'\\(?:ref|eqref|pageref)\{([^{}]*)\}', text))
    for n in used - defined:
        report('ref-undefined', n)

    def new(n):
        if n not in mp:
            return n
        short = n
        for pre in ('fig', 'eq', 'tab', 'sec', 'ex'):
            if re.match(pre + r'[:\-_]', n):
                short = n[len(pre) + 1:]
        return '%s:%s' % (mp[n], short)

    text = re.sub(r'\\(label|ref|eqref|pageref)\{([^{}]*)\}', lambda m: '\\%s{%s}' % (m.group(1), new(m.group(2))), text)
    text = re.sub(r'\(\\ref\{(eq:[^{}]*)\}\)', r'\\eqref{\1}', text)
    return text


def main():
    src = open(sys.argv[1], encoding='utf-8').read()
    a = src.index('\\begin{document}') + len('\\begin{document}')
    b = src.index('\\end{document}')
    body = src[a:b]
    # dead template code
    body, n = re.subn(r'(?m)^%.*\n', '', body)
    report('comment-lines-removed', str(n))
    body, n = re.subn(r'\\\((.*?)\\\)', r'$\1$', body)
    report('paren-math-converted', str(n))
    items = process(body)
    text, labels = render(items)
    text = relabel(text, labels)
    open(sys.argv[2], 'w', encoding='utf-8').write(text)
    if '--report' in sys.argv:
        cnt = Counter(k for k, _ in REPORT)
        for k, c in sorted(cnt.items()):
            print('%5d  %s' % (c, k))
        show = sys.argv[sys.argv.index('--report') + 1:] if len(sys.argv) > sys.argv.index('--report') + 1 else []
        for k, msg in REPORT:
            if k in show or 'all' in show:
                print('[%s] %s' % (k, msg))


if __name__ == '__main__':
    main()
