from flask import Flask, render_template, request, jsonify, url_for, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import qrcode
import os

app = Flask(__name__)

# =========================
# CONFIG
# =========================

app.secret_key = "supersecretkey123"

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///queue_system.db"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

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

# ✅ สร้างตารางหลังจาก model ถูกประกาศแล้ว
with app.app_context():
    db.create_all()