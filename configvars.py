import os
import sys

from Config import Config

# global variables setup
if os.system('mkdir -p ~/.gmailreader'):
    sys.stderr.write('Unable to create ~/.gmailreader\n')
    raise SystemExit, 1

DRAFT = os.path.expanduser('~/.gmailreader/draft')
TMP = os.path.expanduser('~/.gmailreader/tmp')

EDITOR = Config(os.path.expanduser('~/.gmailreader/config')).get('editor')
if not EDITOR:
    EDITOR = os.getenv('EDITOR')
if not EDITOR:
    EDITOR = 'vi'
