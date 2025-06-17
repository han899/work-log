from flask import Flask, g, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'change-me'
DATABASE = 'database.db'

# Pre-defined users and hour limits
INITIAL_USERS = [
    {'username': 'tseng', 'password': 'pass', 'name': '曾台隆', 'role': 'user', 'hour_limit': 48},
    {'username': 'chang', 'password': 'pass', 'name': '張中漢', 'role': 'admin', 'hour_limit': 40},
    {'username': 'chenwt', 'password': 'pass', 'name': '陳瑋廷', 'role': 'user', 'hour_limit': 20},
    {'username': 'wang', 'password': 'pass', 'name': '王冠權', 'role': 'user', 'hour_limit': 48},
    {'username': 'chenwh', 'password': 'pass', 'name': '陳煒函', 'role': 'user', 'hour_limit': 16},
    {'username': 'lu', 'password': 'pass', 'name': '呂若瑄', 'role': 'user', 'hour_limit': 100},
    {'username': 'chencj', 'password': 'pass', 'name': '陳佳境', 'role': 'user', 'hour_limit': 48},
    {'username': 'youn', 'password': 'pass', 'name': '游俊南', 'role': 'user', 'hour_limit': 40},
]


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        need_init = not os.path.exists(DATABASE)
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        if need_init:
            with app.open_resource('schema.sql') as f:
                db.executescript(f.read().decode('utf8'))
            for u in INITIAL_USERS:
                db.execute(
                    'INSERT INTO users (username, password, name, role, hour_limit) VALUES (?,?,?,?,?)',
                    (u['username'], generate_password_hash(u['password']), u['name'], u['role'], u['hour_limit'])
                )
            db.commit()
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def get_user(user_id):
    return query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user(session['user_id'])
    db = get_db()
    if user['role'] == 'admin':
        entries = query_db('''SELECT e.*, u.name FROM entries e JOIN users u ON e.user_id = u.id ORDER BY e.start_time DESC''')
    else:
        entries = query_db('''SELECT e.*, u.name FROM entries e JOIN users u ON e.user_id = u.id WHERE u.id=? ORDER BY e.start_time DESC''',
                           [user['id']])
    return render_template('index.html', user=user, entries=entries)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = query_db('SELECT * FROM users WHERE username=?', [username], one=True)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/record', methods=['GET', 'POST'])
def record():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user(session['user_id'])
    if request.method == 'POST':
        work_type = request.form['work_type']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        description = request.form['description']
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        hours = (end_dt - start_dt).total_seconds() / 3600
        total_hours = query_db('SELECT SUM(hours) as total FROM entries WHERE user_id=?', [user['id']], one=True)['total']
        total_hours = total_hours or 0
        if total_hours + hours > user['hour_limit']:
            flash('Hour limit exceeded')
            return redirect(url_for('record'))
        db = get_db()
        db.execute('INSERT INTO entries (user_id, work_type, start_time, end_time, description, hours) VALUES (?,?,?,?,?,?)',
                   (user['id'], work_type, start_time, end_time, description, hours))
        db.commit()
        return redirect(url_for('index'))
    return render_template('record.html')

if __name__ == '__main__':
    app.run(debug=True)
