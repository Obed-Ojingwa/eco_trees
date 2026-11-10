from contextlib import contextmanager
from typing import Generator

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

from app.core.config import settings


def _configure_connection(conn) -> None:
    conn.execute(
        "SELECT set_config('ecotrees.min_plot_area_ha', %s, false)",
        (str(settings.min_plot_area_ha),),
    )
    conn.execute(
        "SELECT set_config('ecotrees.max_plot_area_ha', %s, false)",
        (str(settings.max_plot_area_ha),),
    )
    conn.commit()


pool = ConnectionPool(
    conninfo=settings.database_url,
    min_size=1,
    max_size=8,
    kwargs={"row_factory": dict_row},
    configure=_configure_connection,
    open=False,
)


def open_pool() -> None:
    if pool.closed:
        pool.open(wait=True, timeout=10)


def close_pool() -> None:
    if not pool.closed:
        pool.close()


@contextmanager
def connection() -> Generator:
    open_pool()
    with pool.connection() as conn:
        yield conn
