#!/usr/bin/env python3
"""Inode-bound report publication (D58).

Contract: the destination DIRECTORY is assumed single-writer (the runner's
scratch root or an explicitly chosen report directory). Under that contract,
publication is exact; under a concurrent hostile writer in the same
directory, every replacement window EXCEPT the final lstat->rename syscall
gap is detected and fails WITHOUT touching the destination -- pathname
rename semantics cannot close that last gap, and no unconditional
preservation claim is made for it.

Mechanism: the temp is created by mkstemp (O_EXCL) and its file descriptor
kept OPEN; content is written through that fd. Immediately before rename the
temp pathname is verified to still name OUR inode (lstat == fstat) -- a
post-create replacement (the D58 probe) fails here, destination untouched,
and the foreign object at the temp pathname is left alone. After rename the
destination must hold our inode, else a nonzero exit reports the concurrent
writer.

Usage: repro_publish.py <dest>   (report content on stdin)
Test hook: REPRO_PUB_PAUSE_MARKER=<path> -- after writing the temp, touch
the marker and sleep 2 s so a test can deterministically interpose.
"""
import os
import sys
import tempfile
import time


def same_inode(a, b):
    return (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)


def main():
    dest = sys.argv[1]
    data = sys.stdin.buffer.read()
    fd, tmp = tempfile.mkstemp(prefix=".repro881_pub.", dir=os.path.dirname(dest) or ".")
    ours = True
    try:
        os.write(fd, data)
        os.fsync(fd)
        marker = os.environ.get("REPRO_PUB_PAUSE_MARKER")
        if marker:
            open(marker, "w").close()
            time.sleep(2)
        st_f = os.fstat(fd)
        try:
            st_l = os.lstat(tmp)
        except OSError:
            ours = False
            print("publish: temp pathname vanished after exclusive creation; "
                  "destination untouched", file=sys.stderr)
            return 1
        if not same_inode(st_l, st_f):
            ours = False   # the object at tmp is NOT ours -- leave it alone
            print("publish: temp pathname no longer names the exclusively "
                  "created inode (concurrent replacement); destination "
                  "untouched", file=sys.stderr)
            return 1
        if os.path.islink(dest):
            print("publish: destination is a symlink", file=sys.stderr)
            return 1
        os.rename(tmp, dest)
        ours = False   # renamed away; nothing left at tmp to clean
        st_d = os.lstat(dest)
        if not same_inode(st_d, st_f):
            print("publish: post-rename inode mismatch (concurrent writer in "
                  "destination directory)", file=sys.stderr)
            return 1
        return 0
    finally:
        if ours:
            try:
                if same_inode(os.lstat(tmp), os.fstat(fd)):
                    os.unlink(tmp)
            except OSError:
                pass
        os.close(fd)


if __name__ == "__main__":
    sys.exit(main())
