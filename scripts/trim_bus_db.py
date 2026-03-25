"""Trim GAIA bus SQLite to cap row count and optionally VACUUM when huge."""
import os
import pathlib
import sqlite3

_ROOT = pathlib.Path(__file__).resolve().parent.parent
DB_PATH = _ROOT / "runtime" / "bus" / "bus.db"
MAX_ROWS = 500_000
MAX_AGE_DAYS = 7  # reserved for future age-based retention


def trim() -> None:
    if not DB_PATH.exists():
        print("bus.db not found")
        return

    size_before = DB_PATH.stat().st_size / 1e6
    conn = sqlite3.connect(str(DB_PATH), timeout=60)

    try:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        print(f"bus.db: {size_before:.0f}MB, {count:,} rows")

        if count > MAX_ROWS:
            # Keep newest MAX_ROWS by seq (same as rowid for INTEGER PRIMARY KEY)
            conn.execute(
                f"""
                DELETE FROM events WHERE seq NOT IN (
                    SELECT seq FROM events
                    ORDER BY seq DESC
                    LIMIT {MAX_ROWS}
                )
                """
            )
            deleted = conn.execute("SELECT changes()").fetchone()[0]
            print(f"Deleted {deleted:,} old rows")

        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()

        size_after = DB_PATH.stat().st_size / 1e6
        print(f"After trim: {size_after:.0f}MB")

        if size_after > 2000:
            print("Running VACUUM (may take time)...")
            conn.execute("VACUUM")
            size_final = DB_PATH.stat().st_size / 1e6
            print(f"After VACUUM: {size_final:.0f}MB")
    finally:
        conn.close()


if __name__ == "__main__":
    trim()
