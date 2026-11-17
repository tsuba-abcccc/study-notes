#!/usr/bin/env python3
"""extract.py PDF OUT.txt : characters in content-stream order, one paragraph (¶) per line.
Each char is followed by nothing; a parallel OUT.txt.font file holds 'B' for bold fonts, '-' otherwise."""
import re, subprocess, sys, html
pdf, out = sys.argv[1], sys.argv[2]
xml = subprocess.run(['gs', '-q', '-dNOPAUSE', '-dBATCH', '-sDEVICE=txtwrite', '-dTextFormat=0', '-sOutputFile=-', pdf],
                     capture_output=True).stdout.decode('utf-8', 'replace')
chars = []; fonts = []
font = ''
for m in re.finditer(r'<span [^>]*font="([^"]*)"|<char [^>]*c="([^"]*)"', xml):
    if m.group(1) is not None:
        font = re.sub(r'^[A-Z]{6}\+', '', m.group(1))
        continue
    c = html.unescape(m.group(2))
    if c.isspace() or c == ' ':
        continue
    chars.append(c)
    fonts.append(('B' if re.search(r'Bold|lmbx|cmbx|Hei', font, re.I) else '-') * len(c))
text = ''.join(chars); ft = ''.join(fonts)
# split into paragraphs at the pilcrow
res = []; resf = []
start = 0
for i, c in enumerate(text):
    if c == '¶':
        res.append(text[start:i]); resf.append(ft[start:i]); start = i + 1
res.append(text[start:]); resf.append(ft[start:])
open(out, 'w', encoding='utf-8').write('\n'.join(res) + '\n')
open(out + '.font', 'w', encoding='utf-8').write('\n'.join(resf) + '\n')
print(pdf, 'chars:', len(text), 'paragraphs:', len(res))
