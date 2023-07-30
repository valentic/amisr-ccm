#!/usr/bin/env python3
"""Lockfile"""

import os
import pathlib
import time
import errno


class LockFile:
    """LockFile Manager"""

    def __init__(self, path, log):
        self.path = pathlib.Path(path)
        self.pid = os.getpid()
        self.log = log

    def acquire(self, max_retries=10, wait_time=1):
        """Acquire the lock"""

        self.log.debug("Trying to acquire lock")

        retry = 0

        while True:
            try:
                fd = os.open(self.path, os.O_EXCL | os.O_RDWR | os.O_CREAT)
                # we created the file, so we own it
                self.log.debug("  - lock file created")
                break
            except OSError as e1:
                if e1.errno != errno.EEXIST:
                    self.log.exception("Error creating lock!")
                    # should not occur
                    raise

                self.log.debug("  - lock file already exists")

                try:
                    # the lock file exists, try to read the pid to see if it is ours
                    pid = int(self.path.read_text("utf-8"))
                    self.log.debug("  - opened lock file")
                except OSError as e2:
                    self.log.exception("Failed to open lock file!")
                    if e2.errno != errno.ENOENT:
                        self.log.error("not ENOENT, aborting")
                        raise
                    # The file went away, try again
                    if retry < max_retries:
                        retry += 1
                        self.log.debug("  - trying again, retry: %d", retry)
                        time.sleep(wait_time)
                        continue
                    self.log.debug("  - max retries, return false")
                    return False

                # Check if the pid is ours

                self.log.debug("  - checking pid")
                self.log.debug("  - pid=%d, ours=%d", pid, self.pid)

                if pid == self.pid:
                    # it's ours, we are done
                    self.log.debug("  - we own this file, return true")
                    return True

                self.log.debug("  - not ours")

                # It's not ours, see if the PID exists
                try:
                    os.kill(pid, 0)
                    self.log.debug("  - owner pid still exists, return false")
                    # PID is still active, this is somebody's lock file
                    return False
                except OSError as e3:
                    if e3.errno != errno.ESRCH:
                        self.log.debug("  - owner still exists, return false")
                        # PID is still active, this is somebody's lock file
                        return False

                self.log.debug("  - owner is not running anymore")

                # The original process is gone. Try to remove.
                try:
                    self.path.unlink()
                    time.sleep(5)
                    # It worked, must have been ours. Try again.
                    self.log.debug("  - removed lock file. try again")
                    continue
                except:  # pylint: disable=bare-except
                    self.log.debug("  - failed to remove. return false")
                    return False

        # If we get here, we have the lock file. Record our PID.

        self.log.debug("  - record pid in file")

        fh = os.fdopen(fd, "w", encoding="utf=8")
        fh.write(f"{self.pid}")
        fh.close()

        self.log.debug("  - lock acquired!")

        return True

    def release(self):
        """Release the lock"""

        if self.ownlock():
            self.path.unlink()

    def _readlock(self):
        try:
            return int(self.path.read_text("utf-8"))
        except:  # pylint: disable=bare-except
            return 8**10

    def is_locked(self):
        """Check if locked"""

        try:
            pid = self._readlock()
            os.kill(pid, 0)
            return True
        except:  # pylint: disable=bare-except
            return False

    def ownlock(self):
        """Check if we own the lock"""

        pid = self._readlock()
        return pid == self.pid

    def __del__(self):
        self.release()
