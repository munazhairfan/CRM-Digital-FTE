# production/clients/session_store.py
"""
Persistent SessionStore singleton.
Unlike the prototype.py SessionStore which gets fresh state on reimport,
this module-level singleton survives across HTTP requests in the FastAPI app.
"""
from production.prompts import SessionStore

# Global singleton — survives across HTTP requests
session_store = SessionStore()
