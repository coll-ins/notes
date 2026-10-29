import random

from faker import Faker

from app import app
from models import Note, User, db

fake = Faker()
CATEGORIES = ["general", "work", "personal", "ideas", "study"]
USERS = ["demo", "alice", "bob"]
NOTES_PER_USER = 12


def seed():
    Note.query.delete()
    User.query.delete()

    for username in USERS:
        user = User(username=username)
        user.password_hash = "password123"
        db.session.add(user)
        for i in range(NOTES_PER_USER):
            user.notes.append(
                Note(
                    title=fake.sentence(nb_words=4).rstrip("."),
                    content=fake.paragraph(nb_sentences=3),
                    category=random.choice(CATEGORIES),
                    is_pinned=(i == 0),
                )
            )
    db.session.commit()
    print(f"Seeded {User.query.count()} users and {Note.query.count()} notes.")
    print("Log in with demo / password123")


if __name__ == "__main__":
    with app.app_context():
        seed()
