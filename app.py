from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'rahasia-sangat-rahasia'

# Konfigurasi MySQL
app.config['MYSQL_HOST'] = '100.96.165.28'
app.config['MYSQL_USER'] = 'iqbal'
app.config['MYSQL_PASSWORD'] = 'iqbal'
app.config['MYSQL_DB'] = 'flask_db'  # Gunakan satu nama database saja
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['MYSQL_AUTOCOMMIT'] = True  # Tambahkan ini

mysql = MySQL(app)

# Fungsi inisialisasi database yang lebih robust
def init_db():
    try:
        conn = mysql.connect
        cur = conn.cursor()
        
        # Buat database jika belum ada
        cur.execute("CREATE DATABASE IF NOT EXISTS flask_db")
        cur.execute("USE flask_db")
        
        # Nonaktifkan foreign key check sementara
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        
        # Buat tabel users
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        ) ENGINE=InnoDB
        """)
        
        # Hapus tabel tasks jika sudah ada (untuk menghindari konflik skema)
        cur.execute("DROP TABLE IF EXISTS tasks")
        
        # Buat tabel tasks dengan foreign key
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            task VARCHAR(255) NOT NULL,
            done BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE
        ) ENGINE=InnoDB
        """)
        
        # Aktifkan kembali foreign key check
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
        
        conn.commit()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise
    finally:
        cur.close()

# Panggil inisialisasi database dalam app context
with app.app_context():
    init_db()

# Decorator untuk memeriksa login
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Route untuk halaman utama
@app.route('/')
@login_required
def home():
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
        SELECT t.* 
        FROM tasks t
        JOIN users u ON t.user_id = u.id
        WHERE t.user_id = %s
        """, (session['user_id'],))
        tasks = cur.fetchall()
        return render_template('index.html', tasks=tasks)
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        flash('Gagal memuat tasks', 'danger')
        return render_template('index.html', tasks=[])
    finally:
        cur.close()

# Route untuk login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username dan password harus diisi', 'danger')
            return redirect(url_for('login'))
        
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Login berhasil!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Username atau password salah', 'danger')
        except Exception as e:
            print(f"Login error: {e}")
            flash('Terjadi kesalahan saat login', 'danger')
        finally:
            cur.close()
    
    return render_template('login.html')

# Route untuk register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([username, password, confirm_password]):
            flash('Semua field harus diisi', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Password tidak cocok', 'danger')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('Password minimal 6 karakter', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed_password)
            )
            mysql.connection.commit()
            flash('Registrasi berhasil! Silakan login', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Registration error: {e}")
            flash('Username sudah digunakan', 'danger')
        finally:
            cur.close()
    
    return render_template('register.html')

# Route untuk logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout', 'info')
    return redirect(url_for('login'))

# CRUD untuk tasks
@app.route('/add', methods=['POST'])
@login_required
def add_task():
    task = request.form.get('task')
    if not task or not task.strip():
        flash('Task tidak boleh kosong!', 'danger')
        return redirect(url_for('home'))
    
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO tasks (user_id, task) VALUES (%s, %s)",
            (session['user_id'], task.strip())
        )
        mysql.connection.commit()
        flash('Task berhasil ditambahkan!', 'success')
    except Exception as e:
        print(f"Error adding task: {e}")
        flash('Gagal menambahkan task', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('home'))

@app.route('/complete/<int:task_id>')
@login_required
def complete_task(task_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE tasks SET done = NOT done WHERE id = %s AND user_id = %s",
            (task_id, session['user_id'])
        )
        mysql.connection.commit()
    except Exception as e:
        print(f"Error completing task: {e}")
        flash('Gagal mengupdate task', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('home'))

@app.route('/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "DELETE FROM tasks WHERE id = %s AND user_id = %s",
            (task_id, session['user_id'])
        )
        mysql.connection.commit()
        flash('Task dihapus!', 'success')
    except Exception as e:
        print(f"Error deleting task: {e}")
        flash('Gagal menghapus task', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)