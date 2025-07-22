import logging
from datetime import datetime, timedelta, time


def seconds_until(_hour, _minute):
    given_time = time(hour=_hour, minute=_minute)
    now = datetime.now()
    future_exec = datetime.combine(now, given_time)
    if (future_exec - now).days < 0:
        future_exec = datetime.combine(now + timedelta(days=1), given_time)
    logging.debug(
        f"seconds_until: Seconds to wait.. {(future_exec - now).total_seconds()}"
    )
    return (future_exec - now).total_seconds()
