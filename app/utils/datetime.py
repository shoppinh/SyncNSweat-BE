
from datetime import datetime, timedelta


def get_date_in_current_week(day_name: str) -> datetime:
    """
    Return the datetime corresponding to the given weekday in the current week.

    The "current week" is interpreted using the weekday index of ``datetime.now()``:
    Monday is 0 and Sunday is 6, as returned by :meth:`datetime.datetime.weekday`.
    The function computes the date within this same calendar week whose weekday
    matches ``day_name`` by applying a signed day offset to the current date.

    This means:

    * If ``day_name`` is the same weekday as today, the returned datetime is today
      (with the current time-of-day at the moment of the call).
    * If ``day_name`` refers to a weekday earlier in the same week than today,
      a past date within the current week is returned (it does **not** advance
      to the next week).
    * If ``day_name`` refers to a weekday later in the same week than today,
      a future date within the current week is returned.

    The input is case-insensitive and must be one of:
    ``"monday"``, ``"tuesday"``, ``"wednesday"``, ``"thursday"``, ``"friday"``,
    ``"saturday"``, or ``"sunday"``. Any other value will result in a
    :class:`ValueError`.

    The returned :class:`datetime.datetime` is timezone-naive and is based on
    the local time returned by :func:`datetime.datetime.now`.

    :param day_name: Name of the target weekday (full English name, case-insensitive).
    :return: A naive ``datetime`` representing the occurrence of ``day_name`` in
             the same calendar week as the current date, preserving the current
             time-of-day.
    :raises ValueError: If ``day_name`` does not correspond to a supported weekday.
    """
    # Mapping days to their index
    days_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2, 
        "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
    }
    
    target_idx = days_map.get(day_name.lower())

    if target_idx is None:
        valid_days = ", ".join(days_map.keys())
        raise ValueError(f"Invalid day name. Expected one of: {valid_days} (case-insensitive)")  

    today = datetime.now()
    # today.weekday() returns 0 for Monday, 6 for Sunday
    current_idx = today.weekday()
    
    # Calculate the difference (positive or negative)
    delta = target_idx - current_idx
    target_date = today + timedelta(days=delta)
    # Normalize to start of day to avoid varying time components
    target_date = datetime.combine(target_date.date(), datetime.min.time())
    
    return target_date