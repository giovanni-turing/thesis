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
kept OPEN; content is written through that fd by write_all (memoryview loop,
EVERY byte accounted, zero-progress rejected). Immediately before rename the
temp pathname is verified to still name OUR inode (lstat == fstat); after
rename the destination must hold our inode. SIGTERM/SIGHUP/SIGINT are
converted to exits that unwind through the cleanup path, so an owned temp
never survives a signalled publication.

Usage: repro_publish.py <dest>   (report content on stdin)
       repro_publish.py --selftest
Test hook: REPRO_PUB_PAUSE_MARKER=<path> -- after writing the temp, touch
the marker and sleep 2 s so a test can deterministically interpose.
"""
import os
import signal
import sys
import tempfile
import time


def same_inode(a, b):
    return (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)


def write_all(fd, data, writer=os.write):
    """Write EVERY byte, looping on a memoryview; a zero-progress write is an
    error, and the total is verified against the payload length."""
    view = memoryview(data)
    total = 0
    while total < len(view):
        n = writer(fd, view[total:])
        if n is None or n <= 0:
            raise OSError(f"zero-progress write at {total}/{len(view)} bytes")
        total += n
    if total != len(view):
        raise OSError(f"short write: {total}/{len(view)} bytes")
    return total


def _install_signal_unwind():
    def _sig(num, _frame):
        raise SystemExit(128 + num)
    for s in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(s, _sig)


def publish(dest, data):
    fd, tmp = tempfile.mkstemp(prefix=".repro881_pub.", dir=os.path.dirname(dest) or ".")
    ours = True
    try:
        write_all(fd, data)
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


def _selftest():
    ok = True

    def t(name, good):
        nonlocal ok
        ok &= good
        print(f"{'PASS' if good else 'FAIL'}: {name}")

    # short-write writer: dribbles <=7 bytes per call; every byte must land
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "f")
        fd = os.open(p, os.O_WRONLY | os.O_CREAT, 0o600)
        payload = b"0123456789" * 11 + b"tail"
        n = write_all(fd, payload, writer=lambda f, v: os.write(f, v[:7]))
        os.close(fd)
        t("short-write-dribble-completes",
          n == len(payload) and open(p, "rb").read() == payload)
        # zero-progress writer must raise, not publish
        fd = os.open(p, os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            write_all(fd, b"abc", writer=lambda f, v: 0)
            t("zero-progress-raises", False)
        except OSError:
            t("zero-progress-raises", True)
        finally:
            os.close(fd)
        # end-to-end publish through the real path
        dest = os.path.join(td, "out.md")
        rc = publish(dest, b"CONTENT-OK")
        t("publish-roundtrip", rc == 0 and open(dest, "rb").read() == b"CONTENT-OK")
    print("PUBLISH-SELFTEST:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    _install_signal_unwind()
    if sys.argv[1:2] == ["--selftest"]:
        return _selftest()
    dest = sys.argv[1]
    data = sys.stdin.buffer.read()
    return publish(dest, data)


if __name__ == "__main__":
    sys.exit(main())
