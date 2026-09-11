import os
import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "change-this-in-production"
)

app.config["DATABASE"] = os.environ.get(
    "DATABASE",
    "/opt/uta-attendance/data/attendance.db"
)


def get_db():
    if "db" not in g:

        database_directory = os.path.dirname(app.config["DATABASE"])

        if database_directory:
            os.makedirs(database_directory, exist_ok=True)

        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row

    return g.db


@app.teardown_appcontext
def close_db(error=None):

    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():

    db = get_db()

    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student'
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            check_in_time TEXT NOT NULL,

            UNIQUE(user_id, attendance_date),

            FOREIGN KEY(user_id)
                REFERENCES users(id)
        );
        """
    )

    db.commit()


def login_required(view):

    @wraps(view)
    def wrapped_view(**kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return view(**kwargs)

    return wrapped_view


@app.route("/health")
def health():

    return {"status": "ok"}, 200


@app.route("/")
def index():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not full_name or not email or not password:

            flash("All fields are required.")

            return redirect(url_for("register"))

        try:

            db = get_db()

            db.execute(
                """
                INSERT INTO users (
                    full_name,
                    email,
                    password_hash
                )
                VALUES (?, ?, ?)
                """,
                (
                    full_name,
                    email,
                    generate_password_hash(password),
                ),
            )

            db.commit()

            flash("Registration successful. Please log in.")

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            flash("That email is already registered.")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = get_db().execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session.clear()

            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():

    today = date.today().isoformat()

    record = get_db().execute(
        """
        SELECT *
        FROM attendance
        WHERE user_id = ?
        AND attendance_date = ?
        """,
        (
            session["user_id"],
            today,
        ),
    ).fetchone()

    return render_template(
        "dashboard.html",
        record=record,
        today=today,
    )


@app.route("/attendance", methods=["POST"])
@login_required
def mark_attendance():

    today = date.today().isoformat()
    now = datetime.now().strftime("%H:%M:%S")

    try:

        db = get_db()

        db.execute(
            """
            INSERT INTO attendance (
                user_id,
                attendance_date,
                check_in_time
            )
            VALUES (?, ?, ?)
            """,
            (
                session["user_id"],
                today,
                now,
            ),
        )

        db.commit()

        flash("Attendance recorded successfully.")

    except sqlite3.IntegrityError:

        flash(
            "Attendance has already been recorded for today."
        )

    return redirect(url_for("dashboard"))


@app.route("/admin")
@login_required
def admin():

    if session.get("role") != "admin":

        flash("Administrator access is required.")

        return redirect(url_for("dashboard"))

    rows = get_db().execute(
        """
        SELECT
            u.full_name,
            u.email,
            a.attendance_date,
            a.check_in_time

        FROM attendance a

        JOIN users u
            ON u.id = a.user_id

        ORDER BY
            a.attendance_date DESC,
            a.check_in_time DESC
        """
    ).fetchall()

    return render_template(
        "admin.html",
        rows=rows,
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


if __name__ == "__main__":

    with app.app_context():
        init_db()

    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True,
    )
