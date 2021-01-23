#!/usr/bin/python3
# original: https://git.samba.org/?p=rsync.git;a=blob_plain;f=support/git-set-file-times
# modified: Line 66: debug info

import os, re, argparse, subprocess
from datetime import datetime

NULL_COMMIT_RE = re.compile(r'\0\0commit [a-f0-9]{40}$|\0$')

def main():
    if not args.git_dir:
        cmd = 'git rev-parse --show-toplevel 2>/dev/null || echo .'
        top_dir = subprocess.check_output(cmd, shell=True, encoding='utf-8').strip()
        args.git_dir = os.path.join(top_dir, '.git')
        if not args.prefix:
            os.chdir(top_dir)

    git = [ 'git', '--git-dir=' + args.git_dir ]

    if args.tree:
        cmd = git + 'ls-tree -z -r --name-only'.split() + [ args.tree ]
    else:
        cmd = git + 'ls-files -z'.split()

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, encoding='utf-8')
    out = proc.communicate()[0]
    ls = set(out.split('\0'))
    ls.discard('')

    if not args.tree:
        # All modified files keep their current mtime.
        proc = subprocess.Popen(git + 'ls-files -m -z'.split(), stdout=subprocess.PIPE, encoding='utf-8')
        out = proc.communicate()[0]
        for fn in out.split('\0'):
            if fn == '':
                continue
            if args.list:
                mtime = os.lstat(fn).st_mtime
                print_line(fn, mtime, mtime)
            ls.discard(fn)

    cmd = git + 'log -r --name-only --no-color --pretty=raw --no-renames -z'.split()
    if args.tree:
        cmd.append(args.tree)
    cmd += ['--'] + args.files

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, encoding='utf-8')
    for line in proc.stdout:
        line = line.strip()
        m = re.match(r'^committer .*? (\d+) [-+]\d+$', line)
        if m:
            commit_time = int(m[1])
        elif NULL_COMMIT_RE.search(line):
            line = NULL_COMMIT_RE.sub('', line)
            files = set(fn for fn in line.split('\0') if fn in ls)
            if not files:
                continue
            for fn in files:
                if args.prefix:
                    fn = args.prefix + fn
                mtime = os.lstat(fn).st_mtime
                if args.list:
                    print_line(fn, mtime, commit_time)
                elif mtime != commit_time:
                    if not args.quiet:
                        print(f"Setting {datetime.utcfromtimestamp(mtime)} -> {datetime.utcfromtimestamp(commit_time)} - {fn}",)
                    os.utime(fn, (commit_time, commit_time), follow_symlinks = False)
            ls -= files
            if not ls:
                break
    proc.communicate()


def print_line(fn, mtime, commit_time):
    if args.list > 1:
        ts = str(commit_time).rjust(10)
    else:
        ts = datetime.utcfromtimestamp(commit_time).strftime("%Y-%m-%d %H:%M:%S")
    chg = '.' if mtime == commit_time else '*'
    print(chg, ts, fn)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Set the times of the current git checkout to their last-changed time.", add_help=False)
    parser.add_argument('--git-dir', metavar='GIT_DIR', help="The git dir to query (defaults to affecting the current git checkout).")
    parser.add_argument('--tree', metavar='TREE-ISH', help="The tree-ish to query (defaults to the current branch).")
    parser.add_argument('--prefix', metavar='PREFIX_STR', help="Prepend the PREFIX_STR to each filename we tweak.")
    parser.add_argument('--quiet', '-q', action='store_true', help="Don't output the changed-file information.")
    parser.add_argument('--list', '-l', action='count', help="List files & times instead of changing them. Repeat for Unix timestamp instead of human readable.")
    parser.add_argument('files', metavar='FILE', nargs='*', help="Specify a subset of checked-out files to tweak.")
    parser.add_argument("--help", "-h", action="help", help="Output this help message and exit.")
    args = parser.parse_args()
    main()

# vim: sw=4 et