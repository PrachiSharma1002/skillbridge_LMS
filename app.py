from flask import Flask, render_template, request, redirect, session
import pymysql

app = Flask(__name__)
app.secret_key = 'skillbridge123'

def get_db():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='#PrachiSQL123',
        database='skillbridge'
    )

# ─── HOME ───────────────────────────────────────────
@app.route('/')
def home():
    return render_template('home.html')

# ─── REGISTER (students only) ───────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO students (name, email, password) VALUES (%s, %s, %s)",
                       (name, email, password))
        db.commit()
        db.close()
        return redirect('/login')
    return render_template('register.html')

# ─── LOGIN ──────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()

        # Check admins table
        cursor.execute("SELECT * FROM admins WHERE email=%s AND password=%s",
                       (email, password))
        admin = cursor.fetchone()
        if admin:
            session['user_id'] = admin[0]
            session['user_name'] = admin[1]
            session['role'] = 'admin'
            db.close()
            return redirect('/admin')

        # Check teachers table
        cursor.execute("SELECT * FROM teachers WHERE email=%s AND password=%s",
                       (email, password))
        teacher = cursor.fetchone()
        if teacher:
            session['user_id'] = teacher[0]
            session['user_name'] = teacher[1]
            session['role'] = 'teacher'
            db.close()
            return redirect('/teacher')

        # Check students table
        cursor.execute("SELECT * FROM students WHERE email=%s AND password=%s",
                       (email, password))
        student = cursor.fetchone()
        if student:
            session['user_id'] = student[0]
            session['user_name'] = student[1]
            session['role'] = 'student'
            db.close()
            return redirect('/dashboard')

        db.close()
        return render_template('login.html', error='Wrong email or password!')
    return render_template('login.html')

# ─── LOGOUT ─────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ─── STUDENT DASHBOARD ──────────────────────────────
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect('/login')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT courses.title, enrollments.progress, enrollments.course_id
        FROM enrollments
        JOIN courses ON enrollments.course_id = courses.id
        WHERE enrollments.user_id = %s
    """, (session['user_id'],))
    enrolled = cursor.fetchall()
    db.close()
    return render_template('dashboard.html', name=session['user_name'], courses=enrolled)

# ─── COURSES ────────────────────────────────────────
@app.route('/courses')
def courses():
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM courses")
    all_courses = cursor.fetchall()
    db.close()
    return render_template('courses.html', courses=all_courses)

# ─── ENROLL ─────────────────────────────────────────
@app.route('/enroll/<int:course_id>')
def enroll(course_id):
    if 'user_id' not in session or session['role'] != 'student':
        return redirect('/login')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM enrollments WHERE user_id=%s AND course_id=%s",
                   (session['user_id'], course_id))
    already = cursor.fetchone()
    if not already:
        cursor.execute("INSERT INTO enrollments (user_id, course_id) VALUES (%s, %s)",
                       (session['user_id'], course_id))
        db.commit()
    db.close()
    return redirect('/dashboard')

# ─── UNENROLL ───────────────────────────────────────
@app.route('/unenroll/<int:course_id>')
def unenroll(course_id):
    if 'user_id' not in session or session['role'] != 'student':
        return redirect('/login')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM enrollments WHERE user_id=%s AND course_id=%s",
                   (session['user_id'], course_id))
    db.commit()
    db.close()
    return redirect('/dashboard')

# ─── COURSE DETAIL & LESSONS ────────────────────────
@app.route('/course/<int:course_id>')
def course_detail(course_id):
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM courses WHERE id=%s", (course_id,))
    course = cursor.fetchone()
    cursor.execute("SELECT * FROM lessons WHERE course_id=%s", (course_id,))
    lessons = cursor.fetchall()
    cursor.execute("SELECT lesson_id FROM lesson_progress WHERE user_id=%s",
                   (session['user_id'],))
    completed = [row[0] for row in cursor.fetchall()]
    db.close()
    return render_template('course_detail.html', course=course,
                           lessons=lessons, completed=completed)

# ─── COMPLETE LESSON ────────────────────────────────
@app.route('/complete_lesson/<int:lesson_id>')
def complete_lesson(lesson_id):
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM lesson_progress WHERE user_id=%s AND lesson_id=%s",
                   (session['user_id'], lesson_id))
    already = cursor.fetchone()
    if not already:
        cursor.execute("INSERT INTO lesson_progress (user_id, lesson_id, completed) VALUES (%s, %s, 1)",
                       (session['user_id'], lesson_id))
        cursor.execute("SELECT course_id FROM lessons WHERE id=%s", (lesson_id,))
        course = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM lessons WHERE course_id=%s", (course[0],))
        total = cursor.fetchone()[0]
        cursor.execute("""SELECT COUNT(*) FROM lesson_progress lp
                         JOIN lessons l ON lp.lesson_id = l.id
                         WHERE lp.user_id=%s AND l.course_id=%s AND lp.completed=1""",
                       (session['user_id'], course[0]))
        done = cursor.fetchone()[0]
        progress = int((done / total) * 100) if total > 0 else 0
        cursor.execute("UPDATE enrollments SET progress=%s WHERE user_id=%s AND course_id=%s",
                       (progress, session['user_id'], course[0]))
        db.commit()
    db.close()
    return redirect(f'/course/{lesson_id}')

# ─── QUIZ ───────────────────────────────────────────
@app.route('/quiz/<int:lesson_id>', methods=['GET', 'POST'])
def take_quiz(lesson_id):
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        score = 0
        total = 0
        for key, value in request.form.items():
            if key.startswith('quiz_'):
                quiz_id = int(key.split('_')[1])
                cursor.execute("SELECT correct_answer FROM quizzes WHERE id=%s", (quiz_id,))
                correct = cursor.fetchone()[0]
                is_correct = 1 if value == correct else 0
                if is_correct:
                    score += 1
                total += 1
                cursor.execute("""INSERT INTO quiz_attempts
                                 (user_id, quiz_id, selected_answer, is_correct)
                                 VALUES (%s, %s, %s, %s)""",
                               (session['user_id'], quiz_id, value, is_correct))
        db.commit()
        db.close()
        return render_template('quiz_result.html', score=score, total=total)
    cursor.execute("SELECT * FROM quizzes WHERE lesson_id=%s", (lesson_id,))
    questions = cursor.fetchall()
    cursor.execute("SELECT * FROM lessons WHERE id=%s", (lesson_id,))
    lesson = cursor.fetchone()
    db.close()
    return render_template('take_quiz.html', questions=questions, lesson=lesson)

# ─── ADMIN PANEL ────────────────────────────────────
@app.route('/admin')
def admin():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM courses")
    all_courses = cursor.fetchall()
    cursor.execute("SELECT id, name, email FROM students")
    all_students = cursor.fetchall()
    cursor.execute("SELECT id, name, email, subject FROM teachers")
    all_teachers = cursor.fetchall()
    cursor.execute("""
        SELECT students.name, courses.title, enrollments.progress
        FROM enrollments
        JOIN students ON enrollments.user_id = students.id
        JOIN courses ON enrollments.course_id = courses.id
        ORDER BY students.name
    """)
    progress_data = cursor.fetchall()
    db.close()
    return render_template('admin.html', courses=all_courses,
                       students=all_students, all_teachers=all_teachers,
                       progress_data=progress_data)

@app.route('/admin/add_course', methods=['POST'])
def admin_add_course():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/')
    title = request.form['title']
    description = request.form['description']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO courses (title, description) VALUES (%s, %s)",
                   (title, description))
    db.commit()
    db.close()
    return redirect('/admin')

@app.route('/admin/delete_course/<int:course_id>')
def delete_course(course_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM courses WHERE id=%s", (course_id,))
    db.commit()
    db.close()
    return redirect('/admin')

# ─── TEACHER PANEL ──────────────────────────────────
@app.route('/teacher')
def teacher():
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect('/')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM courses WHERE created_by=%s",
                   (session['user_id'],))
    all_courses = cursor.fetchall()
    cursor.execute("""
        SELECT students.name, courses.title, enrollments.progress
        FROM enrollments
        JOIN students ON enrollments.user_id = students.id
        JOIN courses ON enrollments.course_id = courses.id
        WHERE courses.created_by = %s
        ORDER BY students.name
    """, (session['user_id'],))
    my_students = cursor.fetchall()
    db.close()
    return render_template('teacher.html', courses=all_courses,
                           my_students=my_students)

@app.route('/teacher/add_course', methods=['POST'])
def teacher_add_course():
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect('/')
    title = request.form['title']
    description = request.form['description']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO courses (title, description, created_by) VALUES (%s, %s, %s)",
                   (title, description, session['user_id']))
    db.commit()
    db.close()
    return redirect('/teacher')

@app.route('/teacher/edit_course/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect('/')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM courses WHERE id=%s AND created_by=%s",
                   (course_id, session['user_id']))
    course = cursor.fetchone()
    if not course:
        db.close()
        return redirect('/teacher')
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        cursor.execute("UPDATE courses SET title=%s, description=%s WHERE id=%s",
                       (title, description, course_id))
        db.commit()
        db.close()
        return redirect('/teacher')
    db.close()
    return render_template('edit_course.html', course=course)

@app.route('/teacher/add_lesson/<int:course_id>', methods=['GET', 'POST'])
def add_lesson(course_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect('/')
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cursor.execute("INSERT INTO lessons (course_id, title, content, created_by) VALUES (%s, %s, %s, %s)",
                       (course_id, title, content, session['user_id']))
        db.commit()
        db.close()
        return redirect('/teacher')
    cursor.execute("SELECT * FROM courses WHERE id=%s", (course_id,))
    course = cursor.fetchone()
    db.close()
    return render_template('add_lesson.html', course=course)

@app.route('/teacher/add_quiz/<int:course_id>', methods=['GET', 'POST'])
def add_quiz(course_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect('/')
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        question = request.form['question']
        option_a = request.form['option_a']
        option_b = request.form['option_b']
        option_c = request.form['option_c']
        option_d = request.form['option_d']
        correct = request.form['correct_answer']
        cursor.execute("""INSERT INTO quizzes
                         (lesson_id, question, option_a, option_b, option_c, option_d, correct_answer)
                         VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                       (course_id, question, option_a, option_b,
                        option_c, option_d, correct))
        db.commit()
        db.close()
        return redirect('/teacher')
    cursor.execute("SELECT * FROM courses WHERE id=%s", (course_id,))
    course = cursor.fetchone()
    db.close()
    return render_template('add_quiz.html', lesson=course)

@app.route('/teacher/add_material/<int:lesson_id>', methods=['GET', 'POST'])
def add_material(lesson_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect('/')
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cursor.execute("INSERT INTO materials (lesson_id, title, content, created_by) VALUES (%s, %s, %s, %s)",
                       (lesson_id, title, content, session['user_id']))
        db.commit()
        db.close()
        return redirect('/teacher')
    cursor.execute("SELECT * FROM lessons WHERE id=%s", (lesson_id,))
    lesson = cursor.fetchone()
    db.close()
    return render_template('add_material.html', lesson=lesson)

# ─── ADMIN EDIT COURSE ──────────────────────────────
@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
def admin_edit_course(course_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/')
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        cursor.execute("UPDATE courses SET title=%s, description=%s WHERE id=%s",
                       (title, description, course_id))
        db.commit()
        db.close()
        return redirect('/admin')
    cursor.execute("SELECT * FROM courses WHERE id=%s", (course_id,))
    course = cursor.fetchone()
    db.close()
    return render_template('admin_edit_course.html', course=course)

# ─── ADMIN ADD TEACHER ──────────────────────────────
@app.route('/admin/add_teacher', methods=['POST'])
def add_teacher():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/')
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    subject = request.form['subject']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO teachers (name, email, password, subject) VALUES (%s, %s, %s, %s)",
                   (name, email, password, subject))
    db.commit()
    db.close()
    return redirect('/admin')

# ─── ADMIN EDIT TEACHER ─────────────────────────────
@app.route('/admin/edit_teacher/<int:teacher_id>', methods=['GET', 'POST'])
def edit_teacher(teacher_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/')
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        cursor.execute("UPDATE teachers SET name=%s, email=%s, subject=%s WHERE id=%s",
                       (name, email, subject, teacher_id))
        db.commit()
        db.close()
        return redirect('/admin')
    cursor.execute("SELECT * FROM teachers WHERE id=%s", (teacher_id,))
    teacher = cursor.fetchone()
    db.close()
    return render_template('admin_edit_teacher.html', teacher=teacher)

# ─── ADMIN DELETE TEACHER ───────────────────────────
@app.route('/admin/delete_teacher/<int:teacher_id>')
def delete_teacher(teacher_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM teachers WHERE id=%s", (teacher_id,))
    db.commit()
    db.close()
    return redirect('/admin')

# ─── ADMIN DELETE STUDENT ───────────────────────────
@app.route('/admin/delete_student/<int:student_id>')
def delete_student(student_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM students WHERE id=%s", (student_id,))
    db.commit()
    db.close()
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)