"""SQLAlchemy models for Warbler."""

from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()


class Follows(db.Model):
    """Connection of a follower <-> followed_user."""

    __tablename__ = 'follows'

    user_being_followed_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True,
    )

    user_following_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True,
    )


class Likes(db.Model):
    """Mapping user likes to warbles."""

    __tablename__ = 'likes'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade')
    )

    message_id = db.Column(
        db.Integer,
        db.ForeignKey('messages.id', ondelete='cascade')
    )

    likes_count = db.Column(db.Integer, default=0)
    liked_count = db.Column(db.Integer, default=0)

    def __init__(self, user_id=None, message_id=None, message=None):
        self.user_id = user_id
        self.message_id = message_id
        self.message = message
        self.liked_count = 0
        self.likes_count = 0


    def increment_likes(self, user):
        if user and self.message:
            if user.id == self.message.user_id:
                return

        self.likes_count += 1

        if self.message:
            self.message.likes_count += 1

        db.session.commit()


    def increment_liked(self):

        self.liked_count += 1

    
class User(db.Model):
    """User in the system."""

    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    email = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    username = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    image_url = db.Column(
        db.Text,
        default="/static/images/default-pic.png",
    )

    header_image_url = db.Column(
        db.Text,
        default="/static/images/warbler-hero.jpg"
    )

    bio = db.Column(
        db.Text,
        nullable=True
    )

    location = db.Column(
        db.Text,
        nullable=False
    )

    password = db.Column(
        db.Text,
        nullable=False,
    )

    messages = db.relationship('Message')

    followers = db.relationship(
        "User",
        secondary="follows",
        primaryjoin=(Follows.user_being_followed_id == id),
        secondaryjoin=(Follows.user_following_id == id)
    )

    following = db.relationship(
        "User",
        secondary="follows",
        primaryjoin=(Follows.user_following_id == id),
        secondaryjoin=(Follows.user_being_followed_id == id)
    )

    likes = db.relationship(
        'Message',
        secondary="likes"
    )

    liked = db.relationship(
        'Message',
        secondary="likes",
        backref=db.backref('liked_by')
    )

    warbles_count = db.Column(db.Integer, default=0)


    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"

    def is_followed_by(self, other_user):
        found_user_list = [user for user in self.followers if user == other_user]
        return len(found_user_list) == 1

    def is_following(self, other_user):
        found_user_list = [user for user in self.following if user == other_user]
        return len(found_user_list) == 1

    def has_liked_message(self, message):
        return Likes.query.filter_by(user_id=self.id, message_id=message.id).first() is not None

    def update_warbles_count(self):
        self.warbles_count = Message.query.filter_by(user_id=self.id).count()
        db.session.commit()

    def increment_warbles_count(self):
        self.warbles_count += 1
        db.session.commit()

    def decrement_warbles_count(self):
        self.warbles_count -= 1
        db.session.commit()

    @classmethod
    def signup(cls, username, email, password, image_url):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
            image_url=image_url,
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.

        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If can't find matching user (or if password is wrong), returns False.
        """

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False


class Message(db.Model):
    """An individual message ("warble")."""

    __tablename__ = 'messages'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    text = db.Column(
        db.String(140),
        nullable=False,
    )

    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow(),
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )

    original_message_id = db.Column(
        db.Integer,
        db.ForeignKey('messages.id', ondelete='CASCADE'),
        nullable=True
    )


    user = db.relationship('User')

    likes = db.relationship('Likes', backref='message')

    def __init__(self, text):
        self.text = text
    

def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    db.app = app
    db.init_app(app)