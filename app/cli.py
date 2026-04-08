"""Flask CLI commands."""

import sqlite3

import click
from flask import Flask

from app.importer import sync_all


def register_cli(app: Flask) -> None:
    @app.cli.command("sync-data")
    def sync_data() -> None:
        """Import classes/vocabs and classes/verbs into SQLite."""
        path = app.config["DB_PATH"]
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        try:
            v, b = sync_all(conn, app.config["CLASSES_VOCABS"], app.config["CLASSES_VERBS"])
            click.echo(f"Imported {v} vocabulary rows and {b} verb rows.")
        finally:
            conn.close()
