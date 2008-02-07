"""Contains a class that handles config-files."""
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

import os

class Config:
    """This is a readonly config-file handler."""
    def __init__(self, fname):
        """__init__(self, string)

        fname is the name of the config-file to be read."""
        self.attrs = {}
        try:
            lines = open(fname).read().split('\n')
        except:
            open(fname, 'w').close()
            os.chmod(fname, 0600)
        else:
            for line in lines:
                arg = line.split('=', 1)
                key = arg[0].strip()
                self.attrs[key] = reduce(str.__add__, arg[1:], '').strip()
    
    def get(self, key, default = lambda: None):
        """get(string, f() -> string|None) -> string|None

        This method was created allowing for lazy evaluation, you should pass a
        function as a parameter which, when evaluated will return the default
        value. This allow for very small code for when we want to read user
        input as a default."""
        if self.attrs.has_key(key):
            return self.attrs[key]
        else:
            return default()
