from flask import Flask, render_template, session, request, redirect, url_for, flash, send_from_directory, jsonify
from functools import wraps
from datetime import datetime
import sqlite3
import hashlib
import uuid
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import Flask, render_template, request, send_file
from io import BytesIO
from fpdf import FPDF

# Flask App Initialization
app = Flask(__name__)

DATABASE = os.path.join(os.path.dirname(__file__), "students.db")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your_fallback_key")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

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
            tenth_pass_year TEXT,
            student_photo TEXT,
            student_signature TEXT
        );

        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            book_id TEXT UNIQUE NOT NULL,
            quantity INTEGER NOT NULL
        );
            
          CREATE TABLE IF NOT EXISTS issue_books (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            issue_date DATE NOT NULL DEFAULT (DATE('now')),
            due_date DATE NOT NULL DEFAULT (DATE('now', '+14 days')),
            return_date DATE DEFAULT NULL,
            available_copies INTEGER NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS return_books (
            return_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            return_date DATE NOT NULL DEFAULT (DATE('now')),
            condition TEXT CHECK(condition IN ('Good', 'Damaged', 'Lost')),
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
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

def save_image(file):
    """Save the uploaded image and return the filename stored in the database."""
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{ext}"  # Generate unique filename
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        file.save(file_path)
        return unique_filename  # Store only filename in DB
    return None

# Route to serve images dynamically
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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
        total_return_books = conn.execute("SELECT COUNT(*) FROM return_books").fetchone()[0]
    return render_template("dashboard.html", total_students=total_students,
                           total_books=total_books, total_issue_books=total_issue_books,
                           total_returned_books=total_returned_books, total_return_books=total_return_books)

@app.route("/add_student", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        try:
            # Handle file uploads
            student_photo = request.files.get("student_photo")
            student_signature = request.files.get("student_signature")

            photo_filename = save_image(student_photo) if student_photo else None
            signature_filename = save_image(student_signature) if student_signature else None

            # Prepare data for insertion
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
                "student_photo": photo_filename,
                "student_signature": signature_filename
            }

            # Insert into database
            with get_db_connection() as conn:
                conn.execute("""
                    INSERT INTO students (
                        student_id, name, admission_no, sats_number, pen_number, apaar_number, aadhar_number,
                        gender, dob, father_name, mother_name, parents_occupation, annual_income,
                        number_of_defendant, nationality, religion, caste, mother_tongue, parents_address,
                        mobile_number, email_id, prev_school, prev_class, admission_date, admission_sought_for,
                        enrolled_school, admission_year, last_attended_date, last_attended_year, passed_class,
                        student_address, eighth_pass_year, ninth_pass_year, tenth_pass_year, student_photo, student_signature
                    ) VALUES (
                        :student_id, :name, :admission_no, :sats_number, :pen_number, :apaar_number, :aadhar_number,
                        :gender, :dob, :father_name, :mother_name, :parents_occupation, :annual_income,
                        :number_of_defendant, :nationality, :religion, :caste, :mother_tongue, :parents_address,
                        :mobile_number, :email_id, :prev_school, :prev_class, :admission_date, :admission_sought_for,
                        :enrolled_school, :admission_year, :last_attended_date, :last_attended_year, :passed_class,
                        :student_address, :eighth_pass_year, :ninth_pass_year, :tenth_pass_year, :student_photo, :student_signature
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
def view_student(student_id):
    with get_db_connection() as conn:
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()

    if student:
        return render_template("view_student.html", student=student)
    else:
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
                    SET name = ?, gender = ?, dob = ?, mobile_number = ?, email_id = ?, admission_no = ?, parents_address = ?
                    WHERE id = ?
                """, (
                    request.form["name"], request.form["gender"], request.form["dob"],
                    request.form["mobile_number"], request.form["email_id"],
                    request.form["admission_no"], request.form["parents_address"], student_id
                ))
                conn.commit()
                flash("✅ Student updated successfully!", "success")
                return redirect(url_for("manage_students"))
            except Exception as e:
                flash(f"❌ Error: {e}", "danger")
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









# Library Management Routes
@app.route("/manage_library", methods=["GET", "POST"])
@login_required
def manage_library():
    with get_db_connection() as conn:
        books = conn.execute("SELECT * FROM books").fetchall()
    
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        book_id = request.form["book_id"]
        quantity = int(request.form["quantity"])

        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO books (title, author, book_id, quantity) VALUES (?, ?, ?, ?)",
                (title, author, book_id, quantity),
            )
            conn.commit()
            flash("Book added successfully!", "success")

        return redirect(url_for("manage_library"))

    return render_template("manage_library.html", books=books)

@app.route("/delete_book/<int:book_id>", methods=["POST"])
@login_required
def delete_book(book_id):
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
    
@app.route("/issue_book", methods=["POST"])
@login_required
def issue_book():
    student_id = request.form.get("student_id")
    book_id = request.form.get("book_id")

    if not student_id or not book_id:
        return jsonify({"success": False, "error": "Student ID and Book ID are required!"})

    with get_db_connection() as conn:
        student = conn.execute("SELECT id FROM students WHERE student_id = ?", (student_id,)).fetchone()
        if not student:
            return jsonify({"success": False, "error": "Student not found in the database!"})

        book = conn.execute("SELECT id, quantity FROM books WHERE book_id = ?", (book_id,)).fetchone()
        if not book:
            return jsonify({"success": False, "error": "Book not found in the database!"})

        if book["quantity"] <= 0:
            return jsonify({"success": False, "error": "No copies of this book are available for issue!"})

        try:
            conn.execute("""
            INSERT INTO issue_books (student_id, book_id, issue_date, due_date, available_copies) 
            VALUES (?, ?, DATE('now'), DATE('now', '+14 days'), ?)
            """, (student["id"], book["id"], book["quantity"] - 1))  # ❌ Problem: book["quantity"] - 1 is incorrect


            conn.execute("UPDATE books SET quantity = quantity - 1 WHERE id = ?", (book["id"],))
            conn.commit()

            return jsonify({"success": True, "message": "Book issued successfully!"})

        except sqlite3.IntegrityError as e:
            return jsonify({"success": False, "error": f"Database Error: {e}"})
        except Exception as e:
            return jsonify({"success": False, "error": f"Unexpected Error: {e}"})

@app.route("/return_book", methods=["POST"])
@login_required
def return_book():
    student_id = request.form.get("student_id")
    book_id = request.form.get("book_id")
    book_condition = request.form.get("condition", "Good")  # Default condition to 'Good'

    if not student_id or not book_id:
        return jsonify({"success": False, "error": "Student ID and Book ID are required!"})

    with get_db_connection() as conn:
        student = conn.execute("SELECT id FROM students WHERE student_id = ?", (student_id,)).fetchone()
        if not student:
            return jsonify({"success": False, "error": "Student not found in the database!"})

        book = conn.execute("SELECT id FROM books WHERE book_id = ?", (book_id,)).fetchone()
        if not book:
            return jsonify({"success": False, "error": "Book not found in the database!"})

        issue_record = conn.execute("""
            SELECT issue_id FROM issue_books 
            WHERE student_id = ? AND book_id = ? AND return_date IS NULL
        """, (student["id"], book["id"])).fetchone()

        if not issue_record:
            return jsonify({"success": False, "error": "No active issue record found for this book!"})

        conn.execute("UPDATE issue_books SET return_date = DATE('now') WHERE issue_id = ?", (issue_record["issue_id"],))
        conn.execute("UPDATE books SET quantity = quantity + 1 WHERE id = ?", (book["id"],))
        
        conn.execute("""
            INSERT INTO return_books (student_id, book_id, return_date, condition)
            VALUES (?, ?, DATE('now'), ?)
        """, (student["id"], book["id"], book_condition))

        conn.commit()
        return jsonify({"success": True, "message": "Book returned successfully!"})
    
    
@app.route("/generate_certificate/<int:student_id>")
@login_required
def generate_certificate(student_id):
    with get_db_connection() as conn:
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if not student:
            flash("Student not found!", "danger")
            return redirect(url_for("manage_students"))

    certificate_path = f"certificates/{student['admission_no']}_study_certificate.pdf"
    
  # Create a PDF in memory
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

 # **Header: Logo & Title**
    logo_path = "static/img/logo.png"  # Change to correct logo path
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=90, y=10, w=20 )  # Centered logo
    pdf.ln(20)  # Space below logo

  

    # **Institution Details**
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "GOVERNMENT GIRLS HIGH SCHOOL, MALKHED", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(200, 10, "Malkhed, Karnataka - 585317 | UDISE No. 29040906727", ln=True, align="C")
    
    pdf.ln(8)  # Line break
    
    

    # Certificate Body
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(0, 10, "STUDY CERTIFICATE", align="C")  
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, f"This is to certify that Sri/Kum {student['name']}, "
                          f"S/o / D/o {student['father_name']} & {student['mother_name']}, "
                          f"has studied from {student['prev_class']} standard to {student['admission_sought_for']} "
                          f"standard in our Institution from {student['admission_date']} to {student['last_attended_date']} academic years."

                          f"The mother tongue of the candidate is {student['mother_tongue']} as per the "
                          f"Admission register of the institution."

                          f"The above details are true and correct to the best of my knowledge.")
    

    pdf.ln(6)
    pdf.multi_cell(0, 8, "This certificate is issued upon the request of the student and the "
                          "above details are true and correct to the best of my knowledge.", align="J")

    pdf.ln(20)





    # **Signature & Seal Section (Right-Aligned)**
    pdf.set_font("Arial", "B", 12)
    pdf.cell(120, 10, "", 0, 0)  # Empty space to push content to the right
    pdf.cell(70, 10, "Signature of Headmaster", ln=True, align="R")

   
    pdf.cell(120, 10, "", 0, 0)
    pdf.cell(70, 10, "(School Seal & Signature)", ln=True, align="R")
    pdf.cell(200, 8, f"Date: {datetime.today().strftime('%d-%m-%Y')}", ln=True)


    

   
    pdf.output(certificate_path)
    
    return send_file(certificate_path, as_attachment=True)

    
  

from flask import render_template
from datetime import datetime

@app.route("/study_certificate/<int:student_id>")
@login_required
def study_certificate(student_id):
    with get_db_connection() as conn:
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if not student:
            flash("Student not found!", "danger")
            return redirect(url_for("manage_students"))

    return render_template("study_certificate.html", student=student, current_date=datetime.today().strftime("%d-%m-%Y"))

if __name__ == "__main__":
    create_schema()
    app.run(host='127.0.0.1', port=5000, debug=False)
