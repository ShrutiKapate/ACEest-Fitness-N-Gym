"""ACEest Fitness & Gym - Flask web service."""
import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from flask import Flask, jsonify, request, render_template_string

APP_VERSION = os.environ.get("APP_VERSION", "3.2.4")
APP_VARIANT = os.environ.get("APP_VARIANT", "stable")
DB_PATH = os.environ.get("DB_PATH", "aceest_fitness.db")

PROGRAMS = {
    "Fat Loss":    {"factor": 22, "workout": "HIIT, Cardio, Strength"},
    "Muscle Gain": {"factor": 35, "workout": "Push/Pull/Legs Split"},
    "Beginner":    {"factor": 26, "workout": "Full Body, Mobility"},
}


def calculate_calories(weight_kg, program):
    if weight_kg is None or weight_kg <= 0:
        raise ValueError("weight must be positive")
    if program not in PROGRAMS:
        raise ValueError("unknown program: " + str(program))
    return int(weight_kg * PROGRAMS[program]["factor"])


def calculate_bmi(weight_kg, height_cm):
    if weight_kg <= 0 or height_cm <= 0:
        raise ValueError("weight and height must be positive")
    h = height_cm / 100.0
    return round(weight_kg / (h * h), 2)


@contextmanager
def get_conn(db_path=None):
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path=None):
    with get_conn(db_path) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            age INTEGER, height REAL, weight REAL,
            program TEXT, calories INTEGER,
            created TEXT NOT NULL)""")


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DB_PATH
    init_db(app.config["DB_PATH"])

    @app.route("/")
    def home():
        with get_conn(app.config["DB_PATH"]) as conn:
            rows = conn.execute("SELECT name, age, weight, program, calories FROM clients").fetchall()
        return render_template_string(
            "<h1 style=color:#d4af37>ACEest Fitness & Gym v{{v}} ({{var}})</h1>"
            "<p>Endpoints: /health /version /api/clients /api/programs</p>"
            "<table border=1 cellpadding=6>"
            "<tr><th>Name</th><th>Age</th><th>Weight</th><th>Program</th><th>Calories</th></tr>"
            "{% for r in rows %}<tr><td>{{r.name}}</td><td>{{r.age}}</td>"
            "<td>{{r.weight}}</td><td>{{r.program}}</td><td>{{r.calories}}</td></tr>{% endfor %}"
            "</table>", v=APP_VERSION, var=APP_VARIANT, rows=rows)

    @app.route("/health")
    def health():
        return jsonify(status="ok", version=APP_VERSION, variant=APP_VARIANT)

    @app.route("/version")
    def version():
        return jsonify(version=APP_VERSION, variant=APP_VARIANT)

    @app.route("/api/programs")
    def api_programs():
        return jsonify(PROGRAMS)

    @app.route("/api/clients", methods=["GET"])
    def api_list_clients():
        with get_conn(app.config["DB_PATH"]) as conn:
            rows = conn.execute("SELECT * FROM clients").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/clients", methods=["POST"])
    def api_create_client():
        data = request.get_json(silent=True) or {}
        try:
            name = str(data["name"]).strip()
            age = int(data["age"])
            weight = float(data["weight"])
            program = data["program"]
            height = float(data["height"]) if data.get("height") else None
            calories = calculate_calories(weight, program)
        except (KeyError, ValueError, TypeError) as e:
            return jsonify(error=str(e)), 400
        with get_conn(app.config["DB_PATH"]) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO clients "
                "(name, age, height, weight, program, calories, created) "
                "VALUES (?,?,?,?,?,?,?)",
                (name, age, height, weight, program, calories,
                 datetime.utcnow().isoformat(timespec="seconds")))
        return jsonify(name=name, calories=calories, program=program), 201

    @app.route("/api/calories", methods=["POST"])
    def api_calories():
        data = request.get_json(silent=True) or {}
        try:
            kcal = calculate_calories(float(data["weight"]), data["program"])
        except (KeyError, ValueError, TypeError) as e:
            return jsonify(error=str(e)), 400
        return jsonify(calories=kcal)

    @app.route("/api/bmi", methods=["POST"])
    def api_bmi():
        data = request.get_json(silent=True) or {}
        try:
            bmi = calculate_bmi(float(data["weight"]), float(data["height"]))
        except (KeyError, ValueError, TypeError) as e:
            return jsonify(error=str(e)), 400
        return jsonify(bmi=bmi)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
