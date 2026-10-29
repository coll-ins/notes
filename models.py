from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates

db = SQLAlchemy()
bcrypt = Bcrypt()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    _password_hash = db.Column(db.String(128), nullable=False)

    notes = db.relationship(
        "Note", backref="user", cascade="all, delete-orphan", lazy="dynamic"
    )

    @hybrid_property
    def password_hash(self):
        raise AttributeError("Password hashes may not be viewed.")

    @password_hash.setter
    def password_hash(self, password):
        self._password_hash = bcrypt.generate_password_hash(
            password.encode("utf-8")
        ).decode("utf-8")

    def authenticate(self, password):
        return bcrypt.check_password_hash(self._password_hash, password.encode("utf-8"))

    @validates("username")
    def validate_username(self, key, value):
        value = (value or "").strip()
        if not 3 <= len(value) <= 30:
            raise ValueError("Username must be 3-30 characters.")
        with db.session.no_autoflush:
            taken = User.query.filter(User.username == value, User.id != self.id).first()
        if taken:
            raise ValueError("Username already taken.")
        return value

    def __repr__(self):
        return f"<User {self.id} {self.username}>"


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.String(30), nullable=False, default="general")
    is_pinned = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    @validates("title")
    def validate_title(self, key, value):
        value = (value or "").strip()
        if not 1 <= len(value) <= 100:
            raise ValueError("Title must be 1-100 characters.")
        return value

    def __repr__(self):
        return f"<Note {self.id} {self.title}>"
