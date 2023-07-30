#!/usr/bin/env python3

import datetime
import logging
import time

from schedule import ScheduleManager

def test():

    logging.basicConfig(level=logging.INFO)

    scheduler = ScheduleManager(logging)

    filespec = ["demo.conf", "year.conf"]

    while True:
        time.sleep(1)

        if scheduler.reload(filespec):
            print("=" * 70)
            print("=" * 70)

        now = datetime.datetime.now(datetime.timezone.utc)

        schedule = scheduler.match(now)

        print("-" * 60)
        print("Current schedule")

        for key in sorted(vars(schedule)):
            attr = getattr(schedule, key)
            if not callable(attr):
                print(f"{key:20s}: {attr}")

        print(f"  special: pump={schedule.get_int('pump')}")

if __name__ == '__main__':
    test()
