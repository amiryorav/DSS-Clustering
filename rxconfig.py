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
                appearance="light",
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
