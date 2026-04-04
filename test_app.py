import pytest
import sqlite3
import tkinter as tk
from unittest.mock import patch
from app import ACEestApp  # Make sure your app file is named app.py

# -----------------------------
# Fixture: initialize app instance
# -----------------------------
@pytest.fixture
def app_instance(tmp_path):
    """
    Create a fresh ACEestApp instance with a temporary SQLite DB for testing.
    """
    db_file = tmp_path / "test_clients.db"

    root = tk.Tk()
    root.withdraw()  # Hide the main Tkinter window

    app = ACEestApp(root, db_path=str(db_file))  # Pass temp DB path
    yield app, root

    # Cleanup
    root.destroy()


# -----------------------------
# Test 1: Add client logic
# -----------------------------
def test_add_client_logic(app_instance):
    """
    Test adding a new client with mocked simpledialog input.
    """
    app, _ = app_instance

    # Mock simpledialog.askstring to return a test client name
    with patch("app.simpledialog.askstring", return_value="Iron Man"):
        app.add_save_client()

    # Verify client was inserted into the DB
    app.cur.execute("SELECT name, membership_status FROM clients WHERE name=?", ("Iron Man",))
    client = app.cur.fetchone()
    assert client is not None
    assert client["name"] == "Iron Man"
    assert client["membership_status"] == "Active"


# -----------------------------
# Test 2: Prevent adding empty client
# -----------------------------
def test_add_client_empty_input(app_instance):
    app, _ = app_instance
    with patch("app.simpledialog.askstring", return_value=None):
        app.add_save_client()

    # DB should still be empty
    app.cur.execute("SELECT * FROM clients")
    clients = app.cur.fetchall()
    assert len(clients) == 0


# -----------------------------
# Test 3: AI program generation
# -----------------------------
def test_ai_program_generation(app_instance):
    app, _ = app_instance

    # Add a test client first
    app.cur.execute(
        "INSERT INTO clients (name, membership_status) VALUES (?, ?)",
        ("Tony Stark", "Active")
    )
    app.conn.commit()
    app.current_client = "Tony Stark"

    # Generate program
    app.generate_program()

    # Verify program column is populated
    app.cur.execute("SELECT program FROM clients WHERE name=?", ("Tony Stark",))
    program = app.cur.fetchone()["program"]
    assert program is not None
    assert len(program) > 0


# -----------------------------
# Test 4: Refresh summary
# -----------------------------
def test_refresh_summary(app_instance):
    app, _ = app_instance

    # Add a client
    app.cur.execute(
        "INSERT INTO clients (name, membership_status, calories, program) VALUES (?, ?, ?, ?)",
        ("Bruce Banner", "Active", 500, "Strength Program")
    )
    app.conn.commit()
    app.current_client = "Bruce Banner"

    # Refresh summary (should not raise errors)
    app.refresh_summary()


# -----------------------------
# Test 5: Database integrity
# -----------------------------
def test_database_integrity(app_instance):
    app, _ = app_instance
    # Ensure columns exist
    app.cur.execute("PRAGMA table_info(clients)")
    columns = [col["name"] for col in app.cur.fetchall()]
    expected_columns = ["id", "name", "membership_status", "membership_end", "program", "calories"]
    for col in expected_columns:
        assert col in columns