from flask import Flask, render_template, request, jsonify, url_for, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import qrcode
import os

app = Flask(__name__)

# =========================
# CONFIG
# =========================



DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///queue_system.db"

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# =========================
# Models
# =========================

class QueueType(db.Model):
    __tablename__ = 'queue_types'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(1), nullable=False)
    name = db.Column(db.String(100), nullable=False)

    queues = db.relationship('Queue', backref='queue_type', lazy=True)


class Queue(db.Model):
    __tablename__ = 'queues'
    id = db.Column(db.Integer, primary_key=True)
    queue_number = db.Column(db.Integer, nullable=False)
    queue_code = db.Column(db.String(10), nullable=False)

    queue_type_id = db.Column(
        db.Integer,
        db.ForeignKey('queue_types.id'),
        nullable=False
    )

    counter = db.Column(db.String(20))
    status = db.Column(db.String(20), default='waiting')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    called_at = db.Column(db.DateTime)

# =========================
# LOGIN SYSTEM
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # 🔐 ตัวอย่างแบบง่าย (ยังไม่ใช้ DB)
        if username == "admin" and password == "1234":
            session['staff_logged_in'] = True
            return redirect(url_for('staff'))
        else:
            return render_template('login.html', error="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('staff_logged_in', None)
    return redirect(url_for('login'))

# =========================
# ROUTES
# =========================

@app.route('/')
def index():
    queue_types = QueueType.query.order_by(QueueType.id).all()
    return render_template('index.html', queue_types=queue_types)


# -------- DISPLAY --------

@app.route('/display')
def display():
    return render_template('display.html')


@app.route('/display/current')
def display_current():
    queues = (
        Queue.query
        .filter_by(status='calling')
        .order_by(Queue.called_at.desc())
        .limit(5)
        .all()
    )

    return jsonify([
        {
            "queue_code": q.queue_code,
            "counter": q.counter
        } for q in queues
    ])


# -------- CREATE QUEUE --------

@app.route('/create-queue', methods=['POST'])
def create_queue():
    data = request.get_json()
    queue_type_id = data.get('queue_type_id')

    if not queue_type_id:
        return jsonify({"error": "queue_type_id missing"}), 400

    qt = QueueType.query.get_or_404(int(queue_type_id))

    last_queue = (
        Queue.query
        .filter_by(queue_type_id=qt.id)
        .order_by(Queue.queue_number.desc())
        .first()
    )

    next_number = 1 if not last_queue else last_queue.queue_number + 1
    queue_code = f"{qt.code}{str(next_number).zfill(3)}"

    new_queue = Queue(
        queue_number=next_number,
        queue_code=queue_code,
        queue_type_id=qt.id
    )

    db.session.add(new_queue)
    db.session.commit()

    return jsonify({
        "redirect": url_for('ticket', queue_id=new_queue.id)
    })


# -------- TICKET --------

@app.route('/ticket/<int:queue_id>')
def ticket(queue_id):
    queue = Queue.query.get_or_404(queue_id)

    qr_folder = os.path.join('static', 'qr')
    os.makedirs(qr_folder, exist_ok=True)

    qr_path = os.path.join(qr_folder, f'{queue.id}.png')

    if not os.path.exists(qr_path):
        img = qrcode.make(queue.queue_code)
        img.save(qr_path)

    return render_template(
        'ticket.html',
        queue=queue,
        qr_path=qr_path
    )


# -------- STAFF --------

@app.route('/staff')
def staff():
    if not session.get('staff_logged_in'):
        return redirect(url_for('login'))

    queues = (
        Queue.query
        .filter(Queue.status != 'done')
        .order_by(Queue.created_at)
        .all()
    )

    return render_template('staff.html', queues=queues)


@app.route('/staff/call/<int:id>', methods=['POST'])
def call_queue(id):
    if not session.get('staff_logged_in'):
        return '', 401

    q = Queue.query.get_or_404(id)
    q.status = 'calling'
    q.called_at = datetime.utcnow()
    q.counter = request.json.get('counter')
    db.session.commit()
    return '', 204


@app.route('/staff/finish/<int:id>', methods=['POST'])
def staff_finish(id):
    if not session.get('staff_logged_in'):
        return '', 401

    q = Queue.query.get_or_404(id)
    q.status = 'done'
    db.session.commit()
    return '', 204


# =========================
# START SERVER
# =========================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()