#!/usr/bin/env python3
"""
South African ID number helpers: validate, parse, mask, generate fake test IDs.

SA ID format: YYMMDD SSSS C A Z
  YYMMDD  date of birth
  SSSS    sequence; 0000-4999 female, 5000-9999 male
  C       0 = SA citizen, 1 = permanent resident, 2 = refugee (newer IDs)
  A       historically used, now typically 8 or 9
  Z       Luhn check digit

An ID number is a unique identifier that reveals date of birth, sex and citizenship
status. Treat it as high-risk personal information (POPIA s19; s57 when linked
across organisations). Never use it as a key, URL parameter or log value.

    python3 sa_id.py validate 5912280409005
    python3 sa_id.py mask 5912280409005
    python3 sa_id.py fake 5
"""
from __future__ import annotations

import random
import sys
from datetime import date
from typing import Optional

CITIZENSHIP = {"0": "SA citizen", "1": "permanent resident", "2": "refugee"}


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = ord(ch) - 48
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def luhn_check_digit(first12: str) -> str:
    for d in "0123456789":
        if luhn_ok(first12 + d):
            return d
    raise ValueError("unreachable")


def parse_dob(id_number: str, today: Optional[date] = None) -> Optional[date]:
    today = today or date.today()
    yy, mm, dd = int(id_number[0:2]), int(id_number[2:4]), int(id_number[4:6])
    century = 2000 if yy <= today.year % 100 else 1900
    try:
        return date(century + yy, mm, dd)
    except ValueError:
        return None


def is_valid(id_number: str) -> bool:
    s = id_number.strip().replace(" ", "")
    if len(s) != 13 or not s.isdigit():
        return False
    if parse_dob(s) is None:
        return False
    if s[10] not in CITIZENSHIP:
        return False
    return luhn_ok(s)


def parse(id_number: str) -> dict:
    s = id_number.strip().replace(" ", "")
    if not is_valid(s):
        return {"valid": False}
    return {
        "valid": True,
        "date_of_birth": parse_dob(s).isoformat(),
        "sex": "female" if int(s[6:10]) < 5000 else "male",
        "citizenship": CITIZENSHIP[s[10]],
    }


def is_synthetic(id_number: str) -> bool:
    """True for IDs produced by fake(): A digit (index 11) is 0."""
    s = id_number.strip().replace(" ", "")
    return len(s) == 13 and s[11] == "0"


def mask(id_number: str, keep_last: int = 3) -> str:
    s = id_number.strip().replace(" ", "")
    if len(s) <= keep_last:
        return "*" * len(s)
    return "*" * (len(s) - keep_last) + s[-keep_last:]


def fake(n: int = 1, seed: Optional[int] = None) -> list:
    """Synthetic IDs that pass validation, for tests and fixtures only.
    Marked synthetic by a 0 in position 12 (the 'A' digit). Current-format IDs use 8 or 9
    there, so popia_scan treats an A digit of 0 as test data (see is_synthetic)."""
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        d = date(1950, 1, 1).toordinal() + rng.randint(0, 18000)
        dob = date.fromordinal(d)
        first12 = f"{dob:%y%m%d}{rng.randint(0, 9999):04d}00"
        candidate = first12 + luhn_check_digit(first12)
        if is_valid(candidate):
            out.append(candidate)
    return out


def _main(argv):
    if len(argv) < 2 or argv[1] not in {"validate", "parse", "mask", "fake"}:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "fake":
        for x in fake(int(argv[2]) if len(argv) > 2 else 1):
            print(x)
        return 0
    if len(argv) < 3:
        print("usage: sa_id.py", cmd, "<id>")
        return 2
    if cmd == "validate":
        ok = is_valid(argv[2])
        print("valid" if ok else "invalid")
        return 0 if ok else 1
    if cmd == "parse":
        print(parse(argv[2]))
        return 0
    if cmd == "mask":
        print(mask(argv[2]))
        return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
