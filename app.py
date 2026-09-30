from flask import Flask, render_template, request, session, redirect
import sqlite3
import uuid
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")


def create_database():
    connection = sqlite3.connect("civicconnect.db")

    connection.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_id TEXT UNIQUE NOT NULL,
            problem_type TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL
        )
    """)

    # Add status column if it doesn't already exist
    columns = connection.execute(
        "PRAGMA table_info(complaints)"
    ).fetchall()

    column_names = [column[1] for column in columns]

    if "status" not in column_names:
        connection.execute(
            "ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT 'Submitted'"
        )

    connection.commit()
    connection.close()

create_database()
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/submit", methods=["GET","POST"])
def submit():
    if request.method == "GET":
        return render_template("report.html")

    problem_type = request.form["problem_type"]
    description = request.form["description"]
    location = request.form["location"]

    tracking_id = "CC-" + uuid.uuid4().hex[:8].upper()

    connection = sqlite3.connect("civicconnect.db")

    connection.execute("""
        INSERT INTO complaints
        (tracking_id, problem_type, description, location, status)
        VALUES (?, ?, ?, ?, ?)
    """, (
        tracking_id,
        problem_type,
        description,
        location,
        "Submitted"
    ))

    connection.commit()
    connection.close()

    return f"""
    <html>
    <head>
        <title>CivicConnect - Complaint Submitted</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>

    <body>

        <div class="container">

            <h1>Complaint Submitted Successfully! 🎉</h1>

            <p>Your Tracking ID is:</p>

            <h2>{tracking_id}</h2>

            <p>Please save this ID to track your complaint.</p>

            <br>

            <a href="/track">Track Complaint</a>
            <br><br>
            <a href="/">Submit another complaint</a>

        </div>

    </body>
    </html>
    """


@app.route("/track", methods=["GET", "POST"])
def track():

    complaint = None
    message = None

    if request.method == "POST":

        tracking_id = request.form["tracking_id"].strip().upper()

        connection = sqlite3.connect("civicconnect.db")
        connection.row_factory = sqlite3.Row

        complaint = connection.execute("""
            SELECT *
            FROM complaints
            WHERE tracking_id = ?
        """, (tracking_id,)).fetchone()

        connection.close()

        if complaint is None:
            message = "Complaint not found. Please check your Tracking ID."

    return render_template(
        "track.html",
        complaint=complaint,
        message=message
    )
@app.route("/authority/login", methods=["GET", "POST"])
def authority_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == os.environ.get("AUTHORITY_USERNAME") and password == os.environ.get("AUTHORITY_PASSWORD"):
            session["authority_logged_in"] = True
            return redirect("/authority")

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template("login.html")
@app.route("/authority")
def authority():
    if not session.get("authority_logged_in"):
        return redirect("/authority/login")
    connection = sqlite3.connect("civicconnect.db")
    connection.row_factory = sqlite3.Row

    complaints = connection.execute("""
        SELECT *
        FROM complaints
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "authority.html",
        complaints=complaints
    )
@app.route("/authority/logout")
def authority_logout():
    session.pop("authority_logged_in", None)
    return redirect("/authority/login")
@app.route("/update_status/<tracking_id>", methods=["POST"])
def update_status(tracking_id):

    new_status = request.form["status"]

    connection = sqlite3.connect("civicconnect.db")

    connection.execute(
        """
        UPDATE complaints
        SET status = ?
        WHERE tracking_id = ?
        """,
        (new_status, tracking_id)
    )

    connection.commit()
    connection.close()

    return redirect("/authority")
if __name__ == "__main__":
    app.run()