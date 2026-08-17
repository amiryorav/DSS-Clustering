import os
import reflex as rx
from dotenv import load_dotenv

load_dotenv()

config = rx.Config(
    app_name="dss_clustering",
    db_url=os.getenv("DATABASE_URL"),
    plugins=[
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                # "inherit" follows the color-mode toggle in the header instead of
                # pinning the app to light, so dark mode is actually reachable.
                appearance="inherit",
                accent_color="teal",
                gray_color="slate",
                radius="medium",
            )
        ),
    ],
    disable_plugins=[
        rx.plugins.sitemap.SitemapPlugin,
    ],
)
