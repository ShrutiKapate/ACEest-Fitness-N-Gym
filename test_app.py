from app import ACEestApp
import tkinter as tk


def test_home():
    root = tk.Tk()
    root.withdraw()  # prevent UI popup
    app = ACEestApp(root)
    root.update()

    assert "Select a profile to view workout" in app.work_label.cget("text")