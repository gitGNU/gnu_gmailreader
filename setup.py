#!/usr/bin/env python

from distutils.core import setup

setup(name='gmailreader',
      version='0.6',
      description='E-mail reader for gmail',
      author='Rafael C. Almeida',
      author_email='almeidaraf@gmail.com',
      url='http://www.nongnu.org/gmailreader/',
      py_modules=['Config', 'configvars', 'MIMEParser', 'tabler'],
      data_files=[('man/man1', ['gmailreader.1'])],
      scripts=['gmailreader.py']
     )
