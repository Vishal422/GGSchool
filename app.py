from flask import Flask, render_template, session, request, redirect, url_for, flash
from functools import wraps
from datetime import datetime, timedelta
import sqlite3
import hashlib
import os


# Flask App Initialization
app = Flask(__name__)
DATABASE = os.path.join(os.path.dirname(__file__), "students.db")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your_fallback_key")

# Helper Functions
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_schema():
    with get_db_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            name TEXT NOT NULL,
            admission_no TEXT UNIQUE NOT NULL,
            sats_number TEXT,
            pen_number TEXT,
            apaar_number TEXT,
            aadhar_number TEXT,
            gender TEXT,
            dob DATE,
            father_name TEXT,
            mother_name TEXT,
            parents_occupation TEXT,
            annual_income INTEGER,
            number_of_defendant INTEGER,
            nationality TEXT,
            religion TEXT,
            caste TEXT,
            mother_tongue TEXT,
            parents_address TEXT,
            mobile_number TEXT,
            email_id TEXT,
            prev_school TEXT,
            prev_class TEXT,
            admission_date DATE,
            admission_sought_for TEXT,
            enrolled_school TEXT,
            admission_year TEXT,
            last_attended_date DATE,
            last_attended_year TEXT,
            passed_class TEXT,
            student_address TEXT,
            eighth_pass_year TEXT,
            ninth_pass_year TEXT,
            tenth_pass_year TEXT
        );

        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT,
            publication_year INTEGER,
            isbn TEXT UNIQUE NOT NULL,
            book_id TEXT UNIQUE NOT NULL,
            quantity INTEGER NOT NULL,
            available_copies INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS issue_books (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            issue_date DATE NOT NULL,
            due_date DATE NOT NULL,
            return_date DATE,
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (book_id) REFERENCES books (id)
        );
        """)

        # Add a default admin user
        try:
            conn.execute("INSERT INTO admin (username, password) VALUES (?, ?)", 
                         ("admin", hash_password("admin123")))
            conn.commit()
        except sqlite3.IntegrityError:
            pass

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}")

# Routes
@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        with get_db_connection() as conn:
            admin = conn.execute("SELECT * FROM admin WHERE username = ?", (username,)).fetchone()
            if admin and admin["password"] == hash_password(password):
                session["logged_in"] = True
                session["username"] = username
                flash("Login successful.", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    with get_db_connection() as conn:
        total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        total_issue_books = conn.execute("SELECT COUNT(*) FROM issue_books").fetchone()[0]
        total_returned_books = conn.execute("SELECT COUNT(*) FROM issue_books WHERE return_date IS NOT NULL").fetchone()[0]
    return render_template("dashboard.html", total_students=total_students,
                           total_books=total_books, total_issue_books=total_issue_books,
                           total_returned_books=total_returned_books)

@app.route("/add_student", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        try:
            data = {
                "student_id": request.form["student_id"],
                "name": request.form["name"],
                "admission_no": request.form["admission_no"],
                "sats_number": request.form.get("sats_number"),
                "pen_number": request.form.get("pen_number"),
                "apaar_number": request.form.get("apaar_number"),
                "aadhar_number": request.form.get("aadhar_number"),
                "gender": request.form["gender"],
                "dob": parse_date(request.form.get("dob")),
                "father_name": request.form.get("father_name"),
                "mother_name": request.form.get("mother_name"),
                "parents_occupation": request.form.get("parents_occupation"),
                "annual_income": int(request.form.get("annual_income", 0)),
                "number_of_defendant": int(request.form.get("number_of_defendant", 0)),
                "nationality": request.form.get("nationality"),
                "religion": request.form.get("religion"),
                "caste": request.form.get("caste"),
                "mother_tongue": request.form.get("mother_tongue"),
                "parents_address": request.form.get("parents_address"),
                "mobile_number": request.form.get("mobile_number"),
                "email_id": request.form.get("email_id"),
                "prev_school": request.form.get("prev_school"),
                "prev_class": request.form.get("prev_class"),
                "admission_date": parse_date(request.form.get("admission_date")),
                "admission_sought_for": request.form.get("admission_sought_for"),
                "enrolled_school": request.form.get("enrolled_school"),
                "admission_year": request.form.get("admission_year"),
                "last_attended_date": parse_date(request.form.get("last_attended_date")),
                "last_attended_year": request.form.get("last_attended_year"),
                "passed_class": request.form.get("passed_class"),
                "student_address": request.form.get("student_address"),
                "eighth_pass_year": request.form.get("eighth_pass_year"),
                "ninth_pass_year": request.form.get("ninth_pass_year"),
                "tenth_pass_year": request.form.get("tenth_pass_year"),
            }

            with get_db_connection() as conn:
                conn.execute("""
                    INSERT INTO students (
                        student_id, name, admission_no, sats_number, pen_number, apaar_number, aadhar_number,
                        gender, dob, father_name, mother_name, parents_occupation, annual_income,
                        number_of_defendant, nationality, religion, caste, mother_tongue, parents_address,
                        mobile_number, email_id, prev_school, prev_class, admission_date, admission_sought_for,
                        enrolled_school, admission_year, last_attended_date, last_attended_year, passed_class,
                        student_address, eighth_pass_year, ninth_pass_year, tenth_pass_year
                    ) VALUES (
                        :student_id, :name, :admission_no, :sats_number, :pen_number, :apaar_number, :aadhar_number,
                        :gender, :dob, :father_name, :mother_name, :parents_occupation, :annual_income,
                        :number_of_defendant, :nationality, :religion, :caste, :mother_tongue, :parents_address,
                        :mobile_number, :email_id, :prev_school, :prev_class, :admission_date, :admission_sought_for,
                        :enrolled_school, :admission_year, :last_attended_date, :last_attended_year, :passed_class,
                        :student_address, :eighth_pass_year, :ninth_pass_year, :tenth_pass_year
                    )
                """, data)
                conn.commit()
                flash("Student added successfully!", "success")
        except sqlite3.IntegrityError as e:
            flash(f"Database error: {str(e)}", "danger")
        except ValueError as ve:
            flash(f"Value error: {ve}", "danger")
        except Exception as e:
            flash(f"Unexpected error: {e}", "danger")
        return redirect(url_for("manage_students"))

    return render_template("add_student.html")

@app.route("/manage_students")
@login_required
def manage_students():
    with get_db_connection() as conn:
        students = conn.execute("SELECT * FROM students").fetchall()
    return render_template("manage_students.html", students=students)

@app.route("/view_student/<int:student_id>")
@login_required
def view_student(student_id):
    with get_db_connection() as conn:
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if student:
        return render_template("view_student.html", student=student)
    flash("Student not found.", "danger")
    return redirect(url_for("manage_students"))

@app.route("/edit_student/<int:student_id>", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    with get_db_connection() as conn:
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if request.method == "POST":
            try:
                conn.execute("""
                    UPDATE students
                    SET name = ?, gender = ?, dob = ?, mobile_number = ?, email_id = ?, admission_no = ?, admission_date = ?
                    WHERE id = ?
                """, (
                    request.form["name"], request.form["gender"], parse_date(request.form["dob"]),
                    request.form["mobile_number"], request.form["email_id"],
                    request.form["admission_no"], parse_date(request.form["admission_date"]), student_id
                ))
                conn.commit()
                flash("Student updated successfully!", "success")
                return redirect(url_for("manage_students"))
            except Exception as e:
                flash(f"Error: {e}", "danger")
        return render_template("edit_student.html", student=student)

@app.route("/delete_student/<int:student_id>", methods=["POST"])
@login_required
def delete_student(student_id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
    flash("Student deleted successfully.", "info")
    return redirect(url_for("manage_students"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# Library Management
@app.route("/manage_library", methods=["GET", "POST"])
@login_required
def manage_library():
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        genre = request.form["genre"]
        isbn = request.form["isbn"]
        quantity = int(request.form["quantity"])
        try:
            with get_db_connection() as conn:
                conn.execute("""
                    INSERT INTO books (title, author, genre, isbn, quantity, available_copies)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (title, author, genre, isbn, quantity, quantity))
                conn.commit()
                flash("Book added successfully!", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
    with get_db_connection() as conn:
        books = conn.execute("SELECT * FROM books").fetchall()
    return render_template("manage_library.html", books=books)

@app.route("/issue_return", methods=["POST"])
@login_required
def issue_return():
    student_id = request.form.get("student_id")
    book_id = request.form.get("book_id")
    issue_date = request.form.get("issue_date", datetime.now().date())
    action = request.form.get("action")

    loan_period_days = 14
    due_date = datetime.strptime(str(issue_date), "%Y-%m-%d") + timedelta(days=loan_period_days)

    try:
        with get_db_connection() as conn:
            if action == "issue":
                book = conn.execute("SELECT available_copies FROM books WHERE id = ?", (book_id,)).fetchone()
                if book and book["available_copies"] > 0:
                    conn.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = ?", (book_id,))
                    conn.execute("""
                        INSERT INTO issue_books (student_id, book_id, issue_date, due_date)
                        VALUES (?, ?, ?, ?)
                    """, (student_id, book_id, issue_date, due_date))
                    conn.commit()
                    flash("Book issued successfully!", "success")
                else:
                    flash("Book is not available.", "danger")
            elif action == "return":
                issue = conn.execute("""
                    SELECT * FROM issue_books 
                    WHERE student_id = ? AND book_id = ? AND return_date IS NULL
                """, (student_id, book_id)).fetchone()
                if issue:
                    conn.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = ?", (book_id,))
                    conn.execute("""
                        UPDATE issue_books 
                        SET return_date = ? 
                        WHERE issue_id = ?
                    """, (datetime.now().date(), issue["issue_id"]))
                    conn.commit()
                    flash("Book returned successfully!", "success")
                else:
                    flash("No such issue record found.", "danger")
            else:
                flash("Invalid action provided.", "danger")
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")

    return redirect(url_for("manage_library"))

# # Main Entry
if __name__ == "__main__":
    create_schema()
    app.run(debug=True)

