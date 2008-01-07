#!/usr/bin/env python

# Copyright (c) 2008
#       Rafael C. Almeida <almeidaraf@gmail.com>. All rights reserved.
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

import sys
import readline
import subprocess
import os
import os.path

from getpass import getpass
from htmlentitydefs import entitydefs

import libgmail


LIST_FOLDERS = 'lf'
LIST_EMAILS = 'lm'
ENTER_FOLDER = 'cd'
READ_EMAIL = 'o'
COMPOSE = 'c'
SEND_DRAFT = 's'
HELP = 'help'
QUIT = 'q'


class NoCommandError(Exception):
    pass


class ExecutionError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class AccountState:
    """This class have variables that must be shared along the commands. The
    ReadEmail command must know what were the last messages displayed to the
    user, for instance."""
    def __init__(self):
        # starting directory is not a label
        self.current_dir = 'inbox'
        self.isLabel = False
        self.labels = []
        # threads from the last lm command
        self.active_threads = []


class Command:
    """This is the basic unit of the program. All the user does is type down
    commands which will give him messages on the screen."""
    def __init__(self, s, state, acc):
        self.state = state
        self.acc = acc

    def execute(self):
        pass


class ListFolders(Command):
    def execute(self):
        all_labels = libgmail.STANDARD_FOLDERS + self.acc.getLabelNames()
        self.state.labels = list(all_labels)

        for i, name in enumerate(all_labels):
            print i, name


class EnterFolder(Command):
    def __init__(self, s, state, acc):
        Command.__init__(self, s, state, acc)
        self.arg = s.strip()

    def execute(self):
        if not self.arg:
            raise ExecutionError('cd command expects a number ' +
                                 'or value as parameter')

        if self.state.labels:
            all_labels = self.state.labels
        else:
            all_labels = list(libgmail.STANDARD_FOLDERS +
                              self.acc.getLabelNames())

        try:
            i = int(self.arg)
            self.state.current_dir = all_labels[i]
        except IndexError:
            raise ExecutionError("Label %s doesn't exist" % i)
        except ValueError:
            label = self.arg
            if label not in all_labels:
                raise ExecutionError("Label %s doesn't exist" % label)
            else:
                self.state.current_dir = label

        self.state.isLabel = not self.state.current_dir in\
                                 libgmail.STANDARD_FOLDERS


class ListEmails(Command):
    def execute(self):
        if self.state.isLabel:
            conversations = self.acc.getMessagesByLabel(self.state.current_dir)
        else:
            conversations = self.acc.getMessagesByFolder(self.state.current_dir)

        self.state.active_threads = list(conversations)

        t = []
        for i, c in enumerate(conversations):
            t.append((str(i),
                      ['', 'N'][bool(c.unread)],
                      self.__fix_html(str(c.authors)),
                      self.__fix_html(self.__entitytoletter(str(c.subject))),
                     )
                    )

        for line in self.__tabler(t):
            print line

    #XXX: helper functions. They're ok for now, but I might want to revist them,
    #     maybe write something better as -- and if -- the project moves
    def __entitytoletter(self, s):
        newdefs = []
        for k, v in entitydefs.items():
            newdefs.append(('&'+k+';', v))

        for k, v in newdefs:
            s = s.replace(k, v)

        return s

    def __fix_html(self, s):
        s = s.replace(r'\u003cspan id\u003d"_upro_', '<')
        s = s.replace(r'"\>', '> ')
        s = s.replace(r'\u003c/span\>', '')
        #bold
        s = s.replace(r'\u003cb\>', '')
        s = s.replace(r'\u003c/b\>', '')

        return s

    def __greatest_len(self, l):
        return max(map(len, l))

    def __compose_field(self, lines):
        x = self.__greatest_len(lines) + 1
        fields = []
        for line in lines:
            fields.append(line+((x-len(line))*' '))

        return fields

    def __concat(self, t1, t2):
        t = []
        for a, b in zip(t1,t2):
            t.append(a+b)

        return t

    def __tabler(self, t):
        table = []
        table = self.__compose_field([x[0] for x in t])
        table = self.__concat(table, self.__compose_field([x[1] for x in t]))
        table = self.__concat(table, self.__compose_field([x[2] for x in t]))
        table = self.__concat(table, [x[3] for x in t])

        return table


class ReadEmail(Command):
    def __init__(self, s, state, acc):
        Command.__init__(self, s, state, acc)
        self.arg = s.strip()

    #XXX: This will need improvment, probably desearves a whole new class with
    #     much more features such as removing the HTML so it's better readable
    #     on a text editor and such.
    def __formating(self, text):
        return text.replace('\r', '')

    def execute(self):
        try:
            conversation = self.state.active_threads[int(self.arg)]
        except ValueError:
            raise ExecutionError("`o' expects a number as parameter")
        except IndexError:
            raise ExecutionError("Invalid thread number")

        f = open(TMP, 'w')
        mtime = os.path.getmtime(TMP)
        for msg in conversation:
            print>>f, self.__formating(msg.source)
        f.close()

        subprocess.call([EDITOR, TMP])

        if mtime != os.path.getmtime(TMP):
            try:
                os.remove(DRAFT)
            except:
                pass
            os.link(TMP, DRAFT)


class SendEmail(Command):
    #XXX: Write better handling -- rfc compatible -- maybe look around for good
    #     libs for this or maybe make my own. Instead of such sucky function.
    def __interpret_email(self, text):
        attrs = {'body':[]}
        for line in text.split('\n'):
            if line.startswith('To:'):
                attrs['to'] = line[3:].strip()
            elif line.startswith('CC:'):
                attrs['cc'] = line[3:].strip()
            elif line.startswith('Subject:'):
                attrs['subject'] = line[8:]
            else:
                attrs['body'].append(line)
        attrs['body'] = '\r\n'.join(attrs['body'])
        return attrs

    def execute(self):
        text = open(DRAFT).read()
        attrs = self.__interpret_email(text)
        msg = libgmail.GmailComposedMessage(attrs.get('to'),
                                            attrs.get('subject'),
                                            attrs.get('body'),
                                            attrs.get('cc'))
        print msg.__dict__
        self.acc.sendMessage(msg)


class ComposeEmail(Command):
    def execute(self):
        subprocess.call([EDITOR, DRAFT])


class Help(Command):
    def execute(self):
        s = """Help:
lf              - List folders
lm              - List e-mails
cd <num>|<name> - Go inside the folder indicated by `num'
                  (as shown by lf) or by the folder's name
o <num>         - Open e-mail of the number `num' indicated
                  when `lm' was executed
c               - Edit draft file
s               - Send draft
help            - Prints this message
q               - Quit (c-d and c-c also work)"""
        print s


class CommandFactory:
    """Factory class used to generate new Commands and keep the execution state
    throught the AccountState class"""
    accstate = AccountState()

    @classmethod
    def generate(cls, s, acc):
        """generate(str, GmailAccout) -> Command

        This method serves as a generator for an executable command"""
        tmp = s.split()
        cmdtype = tmp[0]
        rest = ''.join(tmp[1:])

        if cmdtype == LIST_FOLDERS:
            return ListFolders(rest, cls.accstate, acc)
        elif cmdtype == LIST_EMAILS:
            return ListEmails(rest, cls.accstate, acc)
        elif cmdtype == ENTER_FOLDER:
            return EnterFolder(rest, cls.accstate, acc)
        elif cmdtype == READ_EMAIL:
            return ReadEmail(rest, cls.accstate, acc)
        elif cmdtype == COMPOSE:
            return ComposeEmail(rest, cls.accstate, acc)
        elif cmdtype == SEND_DRAFT:
            return SendEmail(rest, cls.accstate, acc)
        elif cmdtype == HELP:
            return Help(rest, cls.accstate, acc)
        elif cmdtype == QUIT:
            raise SystemExit
        else:
            raise NoCommandError()


class Config:
    def __init__(self, fname):
        self.attrs = {}
        self.dummy = False
        try:
            lines = open(fname).read().split('\n')
        except:
            self.dummy = True
            return
        for line in lines:
            arg = line.split('=')
            self.attrs[arg[0].strip()] = reduce(str.__add__, arg[1:], '').strip()
    
    def get(self, key, default = None):
        if self.dummy:
            return default

        if default is None:
            return self.attrs[key]
        else:
            if self.attrs.has_key(key):
                return self.attrs[key]
            else:
                return default()


def main():
    conf = Config(os.path.expanduser('~/.gmailreader/config'))
    email = conf.get('username', lambda: raw_input("Username: "))
    email += '@gmail.com'
    pw = conf.get('password', lambda: getpass("Password: "))

    acc = libgmail.GmailAccount(email, pw)

    print 'Please wait while logging in ...'

    try:
        acc.login()
    except libgmail.GmailLoginFailure,e:
        print "Login failed: %s" % e.message
        raise SystemExit

    inboxmsgs = acc.getMessagesByFolder('inbox')
    unread = 0
    for msg in inboxmsgs:
        if msg.unread:
            unread += 1
    print 'You have %s unread messages in your inbox.' % unread

    while 1:
        try:
            command = CommandFactory.generate(raw_input('gmail> ').strip(), acc)
        except EOFError:
            print
            raise SystemExit
        except NoCommandError:
            print "what?!"
            continue

        try:
            command.execute()
        except ExecutionError, e:
            print "Error: ", e.message


if __name__ == '__main__':
    try:
        # global variables setup
        if os.system('mkdir -p ~/.gmailreader'):
            sys.stderr.write('Unable to create ~/.gmailreader\n')
            raise SystemExit, 1
        DRAFT = os.path.expanduser('~/.gmailreader/draft')
        TMP = os.path.expanduser('~/.gmailreader/tmp')
        EDITOR = os.getenv('EDITOR')
        if not EDITOR:
            EDITOR = 'vim'

        main()
    except KeyboardInterrupt:
        print
