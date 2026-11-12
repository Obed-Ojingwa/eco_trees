import hashlib

from app.db.migrate import _migration_checksum, _migration_checksum_matches


def test_migration_checksum_is_stable_across_line_endings() -> None:
    sql_lf = b"CREATE TABLE example (\n    id integer\n);\n"
    sql_crlf = sql_lf.replace(b"\n", b"\r\n")

    assert _migration_checksum(sql_lf) == _migration_checksum(sql_crlf)
    legacy_windows_checksum = hashlib.sha256(sql_crlf).hexdigest()
    assert _migration_checksum_matches(legacy_windows_checksum, sql_lf)


def test_migration_checksum_still_detects_sql_changes() -> None:
    original = b"CREATE TABLE example (id integer);\n"
    changed = b"CREATE TABLE example (id bigint);\n"

    assert not _migration_checksum_matches(
        _migration_checksum(original),
        changed,
    )
