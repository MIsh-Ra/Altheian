"""
Unit test conftest — no ML model mocking.
Loads the real SentenceTransformer model (once, on CPU).
"""
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Unit tests run in isolation without external DB connection."""
    yield
