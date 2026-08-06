import os
import reflex as rx
from dotenv import load_dotenv

load_dotenv()

config = rx.Config(
    app_name="dss_clustering",
    db_url=os.getenv("DATABASE_URL"),
    plugins=[
        rx.plugins.RadixThemesPlugin(),
    ],
    disable_plugins=[
        rx.plugins.sitemap.SitemapPlugin,
    ],
)
