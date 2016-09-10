#!/usr/bin/env python
# -*- coding:utf-8 -*-

import re
import sys

top_level=77
lnk_temp='%s- [%s](#%s)'

def generate_toc(fname):
    global top_level
    lines = []
    with open(fname, 'r') as file:
        lines = file.readlines()
    headers = [e.strip() for e in lines if re.match(r'#+', e)]
    #find top_level
    for i,h in enumerate(headers):
        ln = len(re.search(r'^#+',h).group(0))
        top_level = ln if ln < top_level else top_level
        headers[i] = re.sub(r'^#+\s*', str(ln)+' ', h)
    headers = [tr_header(h) for h in headers]
    with open(fname,'w') as f:
        f.write('\n'.join(headers) + '\n')
        f.write(''.join(lines) + '\n')
        f.write('\n\n')


def tr_header(header):
    global lnk_temp
    lvl, txt = re.findall(r'^(\d+) (.*)', header)[0]
    return lnk_temp%((int(lvl)-top_level)*'    ', txt, re.sub(' ','-',re.sub('[^-a-z0-9 ]','',txt.lower())))

if __name__ == '__main__':
    if len(sys.argv)<2:
        print """
            Usage:
            toc.py <markdown file>
        """
    else:
        infile = sys.argv[1]
        generate_toc(infile)
