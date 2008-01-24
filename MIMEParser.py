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
import email
import subprocess

def _get_body(msg):
    body = msg.get_payload(decode=True)
    charset = msg.get_content_charset()
    if charset:
        try:
            body = body.decode(charset).encode('utf-8')
        except UnicodeDecodeError:
            pass
    if msg.get_content_type() == 'text/html':
        p = subprocess.Popen(['html2text'],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE)
        (body, err) = p.communicate(body)
        
    return body

def _scan_type(msg, t):
    if msg.is_multipart():
        msgs = []
        if msg.get_content_type() == t:
            msgs.append(msg)
        parts = msg.get_payload()
        for m in parts:
            if m.get_content_type() == t:
                msgs.append(m)
            msgs.extend(_scan_type(m, t))
        return msgs
    else:
        if msg.get_content_type() == t:
            return [msg]
        else:
            return []

def _parse_multipart(multimsg):
    forwards = _scan_type(multimsg, 'message/rfc822')
    forwards_html = []
    forwards_plain = []
    for f in forwards:
        forwards_html.extend(_scan_type(f, 'text/html'))
        forwards_plain.extend(_scan_type(f, 'text/plain'))

    html = [x for x in _scan_type(multimsg, 'text/html')\
              if x not in forwards_html]
    plain = [x for x in _scan_type(multimsg, 'text/plain')\
               if x not in forwards_html]

    if forwards_html:
        forwards = forwards_html[0]
    elif forwards_plain:
        forwards = forwards_plain[0]
    else:
        forwards = None

    if html:
        text = html[0]
    elif plain:
        text = plain[0]
    else:
        text = None

    return (text, forwards)

class MIMEParser:
    def __init__(self, text):
        msg = email.message_from_string(text)
        if msg.is_multipart():
            (payload, forward) = _parse_multipart(msg)
            if payload:
                self.body = _get_body(payload)
            else:
                self.body = ''
            if forward:
                self.forward = _get_body(forward)
            else:
                self.forward = ''
        else:
            self.body = _get_body(msg)
            self.forward = ''
