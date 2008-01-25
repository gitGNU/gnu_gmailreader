"Exports the function tabler which makes an string table from a list"
# -*- coding: utf-8 -*-

# Copyright (c) 2008
#       Rafael Cunha de Almeida <almeidaraf@gmail.com>. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#    3. The name of the author may not be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

def _greatest_len(l):
    return max(map(len, l))

def _compose_field(lines):
    x = _greatest_len(lines) + 1
    fields = []
    for line in lines:
        fields.append(line+((x-len(line))*' '))

    return fields

def _concat(t1, t2):
    t = []
    for a, b in zip(t1,t2):
        t.append(a+b)

    return t

def tabler(t):
    """tabler([[string]]) -> [string]

    Takes a list of lists of strings and format them in order to the user to be
    able to print a table on the screen. Each string on the returned list is a
    new entry"""
    if not t:
        return []

    table = []
    table = _compose_field([x[0] for x in t])
    table = _concat(table, _compose_field([x[1] for x in t]))
    table = _concat(table, _compose_field([x[2] for x in t]))

    #XXX: this is a little too specific for our implementation, we might want to
    #     make this more general.
    indentsize = _greatest_len([x[0] for x in t]) +\
                 _greatest_len([x[1] for x in t])
    table = _concat(table, ['\n'+((2+indentsize)*' ')+x[3] for x in t])

    # removing extra space by the end of the line
    for i in xrange(len(table)):
        result = []
        for x in table[i].split('\n'):
            result.append(x.rstrip())
        table[i] = '\n'.join(result)

    return table
