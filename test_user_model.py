"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD",
            location='testlocation'
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)


    def test_repr(self):
        user = User(id=1, username='testuser', email='test@email.com', location='testlocation')

        expected_repr = '<User #1: testuser, test@email.com>'

        self.assertEqual(repr(user), expected_repr)


    def test_is_following(self):
        self.user1 = User()
        self.user2 = User()

        self.user2.followers.append(self.user1)
        db.session.commit()

        self.assertTrue(self.user1.is_following(self.user2))

        
    def test_followed_by(self):
        self.user1 = User()
        self.user2 = User()

        self.user1.following.append(self.user2)
        self.user2.following.append(self.user1)

        self.user1.following.append(self.user2)
        self.user2.following.append(self.user1)

    def test_user_signup(self):
        u = User.signup(
            username="testuser",
            email="test@test.com",
            password="HASHED_PASSWORD"
        )

        db.session.commit()

        self.assertIsNotNone(u)
        self.assertEqual(u.username, 'testuser')
        self.assertEqual(u.email, 'test@test.com')

    def tearDown(self) -> None:
        return super().tearDown()