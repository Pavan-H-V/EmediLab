from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "secretkey"

# MySQL connection (XAMPP)
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # XAMPP default has no password
        database="labdb"
    )

# Home route - login page
@app.route('/')
def home():
    return render_template("login.html")

# Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
            conn.commit()
            return redirect(url_for('home'))
        except mysql.connector.errors.IntegrityError:
            return "Username already exists!"
        finally:
            cursor.close()
            conn.close()
    return render_template("register.html")


@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/log', methods=['POST'])
def log():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    # Static admin credentials
    if role == 'admin':
        if username == 'admin' and password == 'Emedilab@9636':
            session['username'] = 'admin'
            session['role'] = 'admin'
            session['user_id'] = 0  # Static ID
            return redirect(url_for('dashboard'))
        else:
            return "Invalid admin credentials!"

    # Static lab technician credentials
    if role == 'labtech':
        if username == 'labtech' and password == 'labtech@9636':
            session['username'] = 'labtech'
            session['role'] = 'labtech'
            session['user_id'] = 0  # Static ID
            return redirect(url_for('dashboard'))
        else:
            return "Invalid lab technician credentials!"
    # static doctor credentials
    if role == 'doctor':
        if username == 'doctor' and password == 'doctor@9636':
            session['username'] = 'doctor'
            session['role'] = 'doctor'
            session['user_id'] = 0  # Static ID
            return redirect(url_for('dashboard'))
        else:
            return "Invalid lab technician credentials!"

    # Patient login from database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s AND role=%s", (username, password, role))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        session['username'] = username
        session['role'] = role
        session['user_id'] = user[0]  # Assuming 'id' is the first column in users table
        return redirect(url_for('dashboard'))

    return "Invalid login credentials!"


# Dashboard route - redirects based on role
@app.route('/dashboard')
def dashboard():
    if 'username' in session and 'role' in session:
        role = session['role']
        if role == 'admin':
            return render_template("admin.html", user=session['username'])
        elif role == 'labtech':
            return redirect(url_for('labtech_appointments'))
        elif role == 'doctor':
            return render_template("doctor.html", user=session['username'])
        elif role == 'patient':
            return render_template("patient.html", user=session['username'])
    return redirect(url_for('home'))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Lab test booking page
@app.route('/book')
def book():
    return render_template('book.html')


@app.route('/blood')
def blood():
    return render_template('blood.html')

# View test results for logged-in user
@app.route('/tests')
def tests():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('home'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM appointments WHERE user_id = %s", (user_id,))
    appointments = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('tests.html', appointments=appointments)



# Testuser login page (optional alternate login)
@app.route('/testuser', methods=['GET', 'POST'])
def testuser():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user['id']
            return redirect(url_for('tests'))
        else:
            return "Invalid credentials"

    return render_template('testuser.html')


@app.route('/download/<int:test_id>')
def download_report(test_id):
    # Example PDF filename logic
    file_path = f"static/reports/report_{test_id}.pdf"
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found"



@app.route('/testregister', methods=['GET', 'POST'])
def testregister():
    if request.method == 'POST':
        if 'user_id' not in session:
            return redirect(url_for('home'))  # Or login page

        user_id = session['user_id']
        fullname = request.form['fullname']
        age = request.form['age']
        gender = request.form['gender']
        test_name = request.form['test_name']
        appointment_date = request.form['appointment_date']
        status = request.form['status']  # Always 'Pending'

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO appointments (user_id, fullname, age, gender, test_name, appointment_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, fullname, age, gender, test_name, appointment_date, status))
        conn.commit()
        cursor.close()
        conn.close()

        return "<script>alert('Appointment Booked Successfully!'); window.location='/dashboard';</script>"

    return render_template('testregister.html')


@app.route('/labtech/appointments')
def labtech_appointments():
    if session.get('role') != 'labtech':
        return redirect(url_for('home'))

    test_type = request.args.get('test')
    appointments = []

    if test_type:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM appointments WHERE test_name = %s", (test_type,))
        appointments = cursor.fetchall()
        cursor.close()
        conn.close()

    return render_template('labtech.html', user=session.get('username'), appointments=appointments, test_type=test_type)



@app.route('/update_status', methods=['POST'])
def update_status():
    if 'role' not in session or session['role'] != 'labtech':
        return redirect(url_for('home'))

    appointment_id = request.form['appointment_id']
    new_status = request.form['new_status']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = %s WHERE id = %s", (new_status, appointment_id))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('labtech_appointments'))

@app.route('/doctor_appointments')
def doctor_appointments():
    if 'username' not in session or session.get('role') != 'doctor':
        return redirect(url_for('home'))

    test_name = request.args.get('test_name')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT fullname, age, gender, appointment_date 
        FROM appointments 
        WHERE test_name = %s AND status = 'Approved'
    """, (test_name,))
    appointments = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('doctor.html', user=session['username'], appointments=appointments, selected_test=test_name)


if __name__ == '__main__':
    app.run(debug=True)
