#!/bin/python
        
import sys, os
import subprocess
import re
import fileinput
        
def update_version(filename, version):
    
    with open(filename, 'rw') as f:
        for line in fileinput.input(filename, inplace=True):
            rexp = "__version__\s*=.*"
            line = re.sub(rexp, "__version__ = \"%s\"\n" % version, line),
            print line[0],

assert len(sys.argv) > 1

update_version(os.path.abspath("pyxrd/__version.py"), sys.argv[1])
update_version(os.path.abspath("mvc/__version.py"), sys.argv[1])

print subprocess.check_output(['git', 'add', 'pyxrd/__version.py'])
print subprocess.check_output(['git', 'add', 'mvc/__version.py'])
print subprocess.check_output(['git', 'commit', '-m', 'Version bump'])
print subprocess.check_output(['git', 'tag', '-a', sys.argv[1], '-m', '%s' % sys.argv[1]])
