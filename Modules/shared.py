import re as _re
import math as _math
import random as _rng
import hashlib as _hs
import datetime as _dt

COLUMN_TYPES = [
    "TEXT", "INTEGER", "REAL", "NUMERIC", "MONEY",
    "BOOLEAN", "VARCHAR(255)", "TIMESTAMP", "DATE", "BYTEA",
]

_SCHEMA_TYPE_MAP = {
    "text": "TEXT",
    "integer": "INTEGER",
    "bigint": "INTEGER",
    "smallint": "INTEGER",
    "real": "REAL",
    "double precision": "REAL",
    "numeric": "NUMERIC",
    "decimal": "NUMERIC",
    "money": "MONEY",
    "boolean": "BOOLEAN",
    "character varying": "VARCHAR(255)",
    "timestamp without time zone": "TIMESTAMP",
    "timestamp with time zone": "TIMESTAMP",
    "date": "DATE",
    "bytea": "BYTEA",
}


def _rand_default_sql(col_type: str, length: str) -> str:
    """Return a PostgreSQL DEFAULT expression producing exactly `length` chars/digits."""
    try:
        n = max(1, int(length))
    except (ValueError, TypeError):
        n = 6
    text_types  = {"TEXT", "VARCHAR(255)"}
    int_types   = {"INTEGER"}
    float_types = {"REAL", "NUMERIC", "MONEY"}
    bool_types  = {"BOOLEAN"}
    date_types  = {"DATE"}
    ts_types    = {"TIMESTAMP"}
    if col_type in text_types:
        return f"substring(md5(random()::text) from 1 for {min(n, 32)})"
    if col_type in int_types:
        low  = 10 ** (n - 1)
        high = 9 * (10 ** (n - 1))
        return f"(floor(random() * {high}) + {low})::integer"
    if col_type in float_types:
        low  = 10 ** (n - 1)
        high = 9 * (10 ** (n - 1))
        return f"round((random() * {high} + {low})::numeric, 2)"
    if col_type in bool_types:
        return "(random() > 0.5)"
    if col_type in date_types:
        return f"(current_date - (random() * {n * 30})::integer)"
    if col_type in ts_types:
        return f"(now() - (random() * interval '{n * 30} days'))"
    return f"substring(md5(random()::text) from 1 for {min(n, 32)})"


def _parse_rand_max(col_default: str, col_type: str) -> str:
    """Recover the length number from a rand DEFAULT expression."""
    if not col_default:
        return "6"
    m = _re.search(r"for (\d+)\)", col_default)
    if m:
        return m.group(1)
    m = _re.search(r"\) \+ (\d+)\)", col_default)
    if m:
        try:
            low = int(m.group(1))
            return str(int(_math.floor(_math.log10(low))) + 1) if low > 0 else "6"
        except Exception:
            return "6"
    m = _re.search(r"random\(\) \* (\d+)", col_default)
    if m:
        try:
            n = int(m.group(1))
            return str(int(round(_math.log10(n)))) if n > 1 else "1"
        except Exception:
            return "6"
    return "6"


def _generate_rand_value_py(col_default: str) -> str:
    """Generate a Python-side random value matching a DB DEFAULT expression."""
    if not col_default:
        return ""
    d = col_default.lower()
    if "current_timestamp" in d or "now()" in d:
        return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "random()" not in d:
        return col_default
    m = _re.search(r"for (\d+)\)", col_default, _re.IGNORECASE)
    if m:
        n = int(m.group(1))
        return _hs.md5(str(_rng.random()).encode()).hexdigest()[:n]
    m = _re.search(r"random\(\) \* (\d+)\) \+ (\d+)", col_default)
    if m:
        high, low = int(m.group(1)), int(m.group(2))
        return str(_rng.randint(low, low + high - 1))
    m = _re.search(r"random\(\) \* (\d+) \+ (\d+)", col_default)
    if m:
        high, low = int(m.group(1)), int(m.group(2))
        return str(round(_rng.uniform(low, low + high), 2))
    if "random() > 0.5" in d:
        return str(_rng.random() > 0.5)
    m = _re.search(r"random\(\) \* (\d+)", col_default)
    if m:
        days = int(m.group(1))
        offset = _rng.randint(0, days)
        return (_dt.date.today() - _dt.timedelta(days=offset)).strftime("%Y-%m-%d")
    return ""
