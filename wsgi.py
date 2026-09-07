"""Vercel and other WSGI platforms entrypoint."""

from app import create_app


app = create_app()
