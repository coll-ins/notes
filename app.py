from functools import wraps

from flask import Flask, request, send_from_directory, session
from flask_migrate import Migrate
from flask_restful import Api, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from config import Config
from models import Note, User, bcrypt, db
from schemas import CredentialsSchema, NoteSchema, UserSchema

migrate = Migrate()
MAX_PER_PAGE = 50


def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return {"error": "Unauthorized"}, 401
        return fn(*args, **kwargs)

    return wrapper


def find_own_note(note_id):
    """Only ever look notes up through the logged-in user's id."""
    return Note.query.filter_by(id=note_id, user_id=session["user_id"]).first()


class Signup(Resource):
    def post(self):
        try:
            data = CredentialsSchema().load(request.get_json(silent=True) or {})
            user = User(username=data["username"])
            user.password_hash = data["password"]
            db.session.add(user)
            db.session.commit()
        except ValidationError as err:
            return {"errors": err.messages}, 422
        except ValueError as err:
            db.session.rollback()
            return {"errors": {"username": [str(err)]}}, 422
        except IntegrityError:
            db.session.rollback()
            return {"errors": {"username": ["Username already taken."]}}, 422
        session["user_id"] = user.id
        return UserSchema().dump(user), 201


class Login(Resource):
    def post(self):
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        user = User.query.filter_by(username=username).first()
        if user and user.authenticate(password):
            session["user_id"] = user.id
            return UserSchema().dump(user), 200
        return {"error": "Invalid username or password"}, 401


class Logout(Resource):
    def delete(self):
        session.pop("user_id", None)
        return "", 204


class CheckSession(Resource):
    def get(self):
        user = current_user()
        if user is None:
            return {"error": "Unauthorized"}, 401
        return UserSchema().dump(user), 200


class NoteIndex(Resource):
    method_decorators = [login_required]

    def get(self):
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = min(max(request.args.get("per_page", 10, type=int), 1), MAX_PER_PAGE)
        pagination = (
            Note.query.filter_by(user_id=session["user_id"])
            .order_by(Note.is_pinned.desc(), Note.created_at.desc(), Note.id.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )
        return {
            "items": NoteSchema(many=True).dump(pagination.items),
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }, 200

    def post(self):
        try:
            data = NoteSchema().load(request.get_json(silent=True) or {})
            note = Note(user_id=session["user_id"], **data)
            db.session.add(note)
            db.session.commit()
        except ValidationError as err:
            return {"errors": err.messages}, 422
        except ValueError as err:
            db.session.rollback()
            return {"errors": {"title": [str(err)]}}, 422
        return NoteSchema().dump(note), 201


class NoteDetail(Resource):
    method_decorators = [login_required]

    def get(self, note_id):
        note = find_own_note(note_id)
        if note is None:
            return {"error": "Note not found"}, 404
        return NoteSchema().dump(note), 200

    def patch(self, note_id):
        note = find_own_note(note_id)
        if note is None:
            return {"error": "Note not found"}, 404
        try:
            data = NoteSchema().load(request.get_json(silent=True) or {}, partial=True)
            for key, value in data.items():
                setattr(note, key, value)
            db.session.commit()
        except ValidationError as err:
            return {"errors": err.messages}, 422
        except ValueError as err:
            db.session.rollback()
            return {"errors": {"title": [str(err)]}}, 422
        return NoteSchema().dump(note), 200

    def delete(self, note_id):
        note = find_own_note(note_id)
        if note is None:
            return {"error": "Note not found"}, 404
        db.session.delete(note)
        db.session.commit()
        return "", 204


def create_app(config_object=Config):
    app = Flask(__name__, static_folder="static")
    app.config.from_object(config_object)

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    api = Api(app)
    api.add_resource(Signup, "/signup")
    api.add_resource(Login, "/login")
    api.add_resource(Logout, "/logout")
    api.add_resource(CheckSession, "/check_session")
    api.add_resource(NoteIndex, "/notes")
    api.add_resource(NoteDetail, "/notes/<int:note_id>")

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(port=5555, debug=True)
