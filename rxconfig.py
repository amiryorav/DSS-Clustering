import os
import reflex as rx
from dotenv import load_dotenv

load_dotenv()


def _database_url() -> str | None:
    """Use the psycopg2 driver we install, not SQLAlchemy's default.

    A plain ``postgresql://`` URL follows whatever dialect the installed
    SQLAlchemy treats as default. A fresh Cloud image can pick psycopg 3,
    which is not a dependency, and the book catalog then fails to connect.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    for prefix in ("postgresql+psycopg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix) :]
    return url


config = rx.Config(
    app_name="dss_clustering",
    db_url=_database_url(),
    # Cloud Redis: default 10s lock expires while serializing 3D Plotly grids.
    redis_lock_expiration=120_000,
    redis_lock_warning_threshold=30_000,
    plugins=[
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                # "inherit" follows the color-mode toggle in the header instead of
                # pinning the app to light, so dark mode is actually reachable.
                appearance="inherit",
                accent_color="teal",
                gray_color="slate",
                radius="large",
                # Lift the whole type/spacing scale for a friendlier, less
                # dense "brochure" feel. Controls still need their own bumps
                # since many were pinned to size="1".
                scaling="110%",
            )
        ),
    ],
    disable_plugins=[
        rx.plugins.sitemap.SitemapPlugin,
    ],
)
