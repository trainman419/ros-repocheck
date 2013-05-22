#! /usr/bin/env python

"""
usage: %prog command [--path PATH_TO_REPO] REV_FILE
"""

import os, sys, string
from optparse import OptionParser
import subprocess
import yaml
import re

_pkgtxt = ""

def expdep(dstr):
  multid = dstr.split('|')
  deps = []
  for d in multid:
    m = re.search('(.+)\s+\(([<>=]*)\s*(.*)\)',d)
    if m:
      deps.append((m.group(1).strip(), m.group(2), m.group(3)))
    else:
      deps.append((d.strip(), '*', '*'))
  return deps
  
class Package(object):
    def __init__(self, pstr):
      self.name,self.ver,self.md5,depstr,provstr = pstr.split('\0',4)

      self.deps = []
      if len(depstr) > 0:
        self.deps = [expdep(d) for d in depstr.split(',')]

      self.provs = [self.name]
      if len(provstr) > 0:
        self.provs += [p.strip() for p in provstr.split(',')]

      self.subdeps = False

    def satisfies(self,dep):
      if dep[1] == '*':
        return True
      else:
        dpkgcmd = ['dpkg', '--compare-versions', self.ver, dep[1], dep[2]]
        return (subprocess.call(dpkgcmd) == 0)

    def IsProv(self):
      return False

def main(argv, stdout, environ):

  global _pkgtxt

  parser = OptionParser(__doc__.strip())
  parser.add_option("--path",action="store",type="string", dest="path",default=".")
  parser.add_option("--distro",action="store",type="string", dest="distro", default="oneiric")

  (options, args) = parser.parse_args()

  repo_pkgs = {}
  repo_provs = {}
  reprepro_cmd = ['reprepro', '-b', options.path, """--list-format=${package}\\0${version}\\0${MD5Sum}\\0${depends}\\0${provides}\n""", '-T', 'deb', 'list', options.distro]
  (o,e) = subprocess.Popen(reprepro_cmd, stdout=subprocess.PIPE).communicate()
  for l in o.splitlines():
    p = Package(l)
    repo_pkgs[p.name] = p
    for prov in p.provs:
      if prov in repo_provs:
        prov_list = repo_provs[prov]
      else:
        prov_list = []
        repo_provs[prov] = prov_list
      prov_list.append(p)

  missing = 0

  for p in repo_pkgs:
    missing += check_deps(repo_pkgs, repo_provs, p)
    
  if missing > 0:
    print ""
    print "Missing Dependencies.  You can probably add the following to %s"%os.path.join(options.path,"conf/mirror.packages:")
    print ""
    print _pkgtxt

    sys.exit(1)
  else:
    sys.exit(0)


def check_deps(repo_pkgs, repo_provs, pkgname):
  
  global _pkgtxt

  if pkgname not in repo_pkgs:
    print >> sys.stderr, "Missing Package: %s"%pkgname
    return 1

  if repo_pkgs[pkgname].subdeps == True:
    return 0

  # We can set subdeps to True assuming we will finish if we've started
  # This keeps us from recursing
  repo_pkgs[pkgname].subdeps = True

  missing = 0

  for deplist in repo_pkgs[pkgname].deps:
    found = False
    for d in deplist:
      if d[0] in repo_provs:
        for p in repo_provs[d[0]]:
          if p.satisfies(d):
            found = True
            missing += check_deps(repo_pkgs, repo_provs, p.name)
            break
    if not found:
      print >> sys.stderr, "Missing Dep: %s For Package: %s"%(deplist, pkgname)
      missing += 1
      _pkgtxt += "%s install\n"%deplist[0][0]

  return missing

if __name__ == "__main__":
  main(sys.argv, sys.stdout, os.environ)
