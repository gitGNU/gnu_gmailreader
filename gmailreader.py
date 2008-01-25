#!/usr/bin/env python
"A console-based gmail e-mail reader."
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

import sys
import readline
import subprocess
import os
import os.path
import email
import select
import urllib2
import shutil
import HTMLParser

from getpass import getpass
from htmlentitydefs import entitydefs

import libgmail

from MIMEParser import MIMEParser
import configvars as conf
from Config import Config
from tabler import tabler

# Time (in seconds) to wait between e-mail checks
TIMEOUT = 10

# These are the constants identifying the commands
LIST_FOLDERS = 'lf'
LIST_EMAILS = 'lm'
ENTER_FOLDER = 'cd'
ARCHIVE = 'ar'
READ_EMAIL = 'o'
COMPOSE = 'c'
SEND_DRAFT = 's'
REPORT_SPAM = '!'
WAIT_EMAIL = 'wait'
HELP = 'help'
QUIT = 'q'


class NoCommandError(Exception):
    """Command doesn't exist."""
    pass


class ExecutionError(Exception):
    """something went wrong while executing a command."""
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class FieldParser(HTMLParser.HTMLParser):
    """This is an HTML Parser which ignores any tag except span. Only the data
    between <span> is stored in the text attribute.
    
    This is handy for filtering out the HTML on subject and author fields."""

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.inside_span = False
        self.email = ''
        self.text = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'span':
            self.inside_span = True
            self.email = dict(attrs)['id'].replace('_upro_', '')

    def handle_data(self, data):
        if self.inside_span:
            self.text += data + (' <%s>' % self.email)
        else:
            self.text += data

    def handle_endtag(self, tag):
        if tag == 'span':
            self.inside_span = False


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
        """__init__(self, string, AccountState, GmailAccount)

        This will just save the current AccountState and GmailAccount to the
        object without doing anything."""
        self.state = state
        self.acc = acc

    def execute(self):
        """This method will execute the command, potentially changing the
        AccountState that was passed to the object's __init__."""
        pass


class ListFolders(Command):
    def execute(self):
        # folders like inbox, all, etc are threated differently than labels by
        # libgmail.
        if self.acc.getLabelNames():
            all_labels = libgmail.STANDARD_FOLDERS + self.acc.getLabelNames()
        else:
            all_labels = libgmail.STANDARD_FOLDERS
        self.state.labels = list(all_labels)

        for i, name in enumerate(all_labels):
            print i, name


class Archive(Command):
    def __init__(self, s, state, acc):
        """__init__(self, string, AccountState, GmailAccount)

        Differently than the standard __init__, it will take the string s into
        account as the command's arguments."""
        Command.__init__(self, s, state, acc)
        self.arg = s.strip()

    def execute(self):
        try:
            self.acc.archiveThread(self.state.active_threads[int(self.arg)])
        except AttributeError:
            print "Version %s of libgmail doesn't support archiving" %\
                  libgmail.Version
        except ValueError:
            raise ExecutionError("`ar' expects a number as parameter")


class ReportSpam(Command):
    def __init__(self, s, state, acc):
        """__init__(self, string, AccountState, GmailAccount)

        Differently than the standard __init__, it will take the string s into
        account as the command's arguments."""
        Command.__init__(self, s, state, acc)
        self.arg = s.strip()

    def execute(self):
        try:
            self.acc.reportSpam(self.state.active_threads[int(self.arg)])
        except AttributeError:
            print "Version %s of libgmail doesn't support spam reporting" %\
                  libgmail.Version
        except ValueError:
            raise ExecutionError("`!' expects a number as parameter")


class EnterFolder(Command):
    def __init__(self, s, state, acc):
        """__init__(self, string, AccountState, GmailAccount)

        Differently than the standard __init__, it will take the string s into
        account as the command's arguments."""
        Command.__init__(self, s, state, acc)
        self.arg = s.strip()

    def execute(self):
        if not self.arg:
            raise ExecutionError('cd command expects a number ' +
                                 'or value as parameter')

        if self.state.labels:
            all_labels = self.state.labels
        elif self.acc.getLabelNames():
            all_labels = list(libgmail.STANDARD_FOLDERS +
                              self.acc.getLabelNames())
        else:
            all_labels = list(libgmail.STANDARD_FOLDERS)

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

        self.state.active_threads = []
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
                      self.__fix_all(c.authors),
                      self.__fix_all(c.subject),
                     )
                    )

        for line in tabler(t):
            print line

    #XXX: helper functions. They're ok for now, but I might want to revist them,
    #     maybe write something better as -- if -- the project moves
    def __fix_all(self, s):
        s = self.__fix_encoding(s)
        s = self.__fix_html(s)
        s = self.__entitytoletter(s)

        return s

    def __entitytoletter(self, s):
        newdefs = []
        for k, v in entitydefs.items():
            newdefs.append(('&'+k+';', v))

        for k, v in newdefs:
            s = s.replace(k, v)

        return s

    def __fix_html(self, s):
        parser = FieldParser()
        try:
            parser.feed(s)
            parser.close()
        except HTMLParser.HTMLParseError:
            parser.text = s

        return parser.text

    def __fix_encoding(self, s):
        final = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and s[i+1] == 'u':
                num = int(s[i+2:i+6], 16)
                final.append(unichr(num).encode('utf-8'))
                i += 6
            else:
                final.append(s[i])
                i += 1

        return ''.join(final).strip()


class ReadEmail(Command):
    EMAIL_DIVISOR = '\n\n'+(80*'-')+'\n\n'

    def __init__(self, s, state, acc):
        """__init__(self, string, AccountState, GmailAccount)

        Differently than the standard __init__, it will take the string s into
        account as the command's arguments."""
        Command.__init__(self, s, state, acc)
        self.arg = s.strip()

    def __print_field(self, msg, field):
        value = msg.get(field)
        if value:
            return field.capitalize()+': '+value
        else:
            return ''

    def __format(self, text, msgid):
        msg = email.message_from_string(text)
        mget = lambda field: self.__print_field(msg, field)

        mp = MIMEParser(text)
        body = mp.body
        if mp.forward:
            body += '\n\n' + mp.forward

        fields = [mget('to'),
                  mget('cc'),
                  mget('from'),
                  mget('date'),
                  'Message-ID: %s' % msgid,
                  mget('subject'),
                  '\n',
                  body,
                  self.EMAIL_DIVISOR]

        return '\n'.join([x for x in fields if x])

    def __add_quote(self, text):
        buffer = []
        for line in text.split('\n'):
            line = '> ' + line
            buffer.append(line)
        return '\n'.join(buffer)

    def __reply_maker(self, text):
        msg = email.message_from_string(text)

        #extracting information
        frm = msg.get('From', '')
        cc = msg.get('CC', '').split(',')
        to = msg.get('To', '').split(',')
        id = msg.get('Message-id', '')
        body = msg.get_payload()
        subject = msg.get('Subject', '')
        if 're:' not in subject.lower():
            subject = 'Re: ' + subject

        #setting up the reply
        body = self.__add_quote(body)
        body = ("On %s, %s wrote:\n" % (msg.get('Date'), frm)) + body
        newmsg = email.message_from_string(body)
        newmsg['To'] = frm
        receivers = [x for x in to if self.acc.name not in x]
        receivers.extend(cc)
        newmsg['CC'] =  ', '.join(receivers)
        newmsg['In-reply-to'] = id
        newmsg['Subject'] = subject

        return newmsg.as_string()

    def execute(self):
        try:
            conversation = self.state.active_threads[int(self.arg)]
        except ValueError:
            raise ExecutionError("`o' expects a number as parameter")
        except IndexError:
            raise ExecutionError("Invalid thread number")

        f = open(conf.TMP, 'w')
        for msg in conversation:
            print>>f, self.__format(msg.source, msg.id)
        f.close()
        mtime = os.path.getmtime(conf.TMP)

        os.system('%s %s' % (conf.EDITOR, conf.TMP))

        if mtime != os.path.getmtime(conf.TMP):
            shutil.copy(conf.TMP, conf.DRAFT)
            text = self.__reply_maker(open(conf.DRAFT).read())
            f = open(conf.DRAFT, 'w')
            f.write(text)
            f.close()


class WaitEmail(Command):
    def __init__(self, s, state, acc):
        """__init__(self, string, AccountState, GmailAccount)

        Differently than the standard __init__, it will take the string s into
        account as the command's arguments. But instead of using the whole
        string as one argument, it will split it into several arguments."""
        Command.__init__(self, s, state, acc)
        self.arg = [x.strip() for x in s.split()]

    def __search_new(self):
        for folder in self.arg:
            try:
                if folder in libgmail.STANDARD_FOLDERS:
                    conversations = self.acc.getMessagesByFolder(folder)
                else:
                    conversations = self.acc.getMessagesByLabel(folder)
            except urllib2.URLError:
                return
            for msg in conversations:
                if msg.unread:
                    return folder

    def execute(self):
        folder = None
        while 1:
            rl, wl, xl = select.select([sys.stdin],[],[],TIMEOUT)
            if sys.stdin in rl:
                sys.stdin.read(1)
                break
            folder = self.__search_new()
            if folder:
                break

        if folder:
            conf = Config(os.path.expanduser('~/.gmailreader/config'))
            script = os.path.expanduser(conf.get('script'))
            if script:
                subprocess.call([script])
            CommandFactory.generate('cd %s' % folder, self.acc).execute()
            CommandFactory.generate('lm', self.acc).execute()


class SendEmail(Command):
    def execute(self):
        text = open(conf.DRAFT).read()
        attrs = email.message_from_string(text)
        msg = libgmail.GmailComposedMessage(attrs.get('to'),
                                            attrs.get('subject'),
                                            attrs.get_payload(),
                                            attrs.get('cc'),
                                            attrs.get('bcc'))
        self.acc.sendMessage(msg, replyTo=attrs.get('in-reply-to'))


class ComposeEmail(Command):
    def execute(self):
        os.system('%s %s' % (conf.EDITOR, conf.DRAFT))


class Help(Command):
    def execute(self):
        s = """Help:
lf              - List folders
lm              - List e-mails
cd <num>|<name> - Go inside the folder indicated by `num'
                  (as shown by lf) or by the folder's name
o <num>         - Open e-mail of the number `num' indicated
                  when `lm' was executed
wait <name1> <name2> ... - Keeps on waiting for the named folders
                           if new email arrives it executes a script
                           pointed out on .gmailreader/config and
                           prints the folder contents on screen
c               - Edit draft file
s               - Send draft
ar <num>        - Archive e-mail indicated by the number `num'
! <num>         - Report e-mail indicated by the number `num' as spam
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
        elif cmdtype == ARCHIVE:
            return Archive(rest, cls.accstate, acc)
        elif cmdtype == REPORT_SPAM:
            return ReportSpam(rest, cls.accstate, acc)
        elif cmdtype == WAIT_EMAIL:
            return WaitEmail(rest, cls.accstate, acc)
        elif cmdtype == HELP:
            return Help(rest, cls.accstate, acc)
        elif cmdtype == QUIT:
            raise SystemExit
        else:
            raise NoCommandError()


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

    # Start by printing the inbox contents
    CommandFactory.generate(LIST_EMAILS, acc).execute()

    while 1:
        try:
            cmd = raw_input('gmail> ').strip()
            if cmd:
                command = CommandFactory.generate(cmd, acc)
            else:
                continue
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
        main()
    except KeyboardInterrupt:
        print
