import os
import pdb

from flask import Flask, render_template, request, flash, redirect, session, g, url_for, request
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, UserEditForm
from models import db, connect_db, User, Message, Likes

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """
    
    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    # IMPLEMENT THIS

    session.pop(CURR_USER_KEY)
    flash('Goodbye!', 'info')
    
    return redirect('/login')


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/login")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/login")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    user = User.query.get_or_404(g.user.id)

    form = UserEditForm(obj=g.user)

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/login")
    
    warbles_count = user.warbles_count
    
    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
        
            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data
            user.header_image_url = form.header_image_url.data
            user.bio = form.bio.data

            db.session.commit()
            flash('Profile updated!', 'success')
            return redirect(f"/users/{g.user.id}")
        else:
            flash('Invalid password. Please try again', 'danger')
    
    return render_template('users/edit.html', form=form, warbles_count=warbles_count)
    
@app.route('/users/add_like/<int:message_id>', methods=["POST"])
def add_like(message_id):
    """Add a like to a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/login")

    msg = Message.query.get(message_id)

    if not msg:
        flash('Message not found.', 'danger')
        return redirect('/')

    if msg.user_id == g.user.id:
        flash("You can't like your own message.", "danger")
        return redirect(request.referrer)

    if msg in g.user.likes:
        g.user.likes.remove(msg)
        db.session.commit()
        flash('Message unliked.', 'danger')
    else:
        g.user.likes.append(msg)
        db.session.commit()
        flash('Message liked!', 'success')

    return redirect(request.referrer)


@app.route('/users/<int:id>/liked')
def liked(id):
    user = User.query.get_or_404(id)
    liked_messages = user.likes

    return render_template('messages/liked.html', liked_messages=liked_messages, liked_user=user)



@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    Message.query.filter_by(user_id=g.user.id).delete()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f'/users/{g.user.id}')

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/login")

    msg = Message.query.get(message_id)

    liked = False

    if g.user:
        liked = g.user.has_liked_message(msg)

    if not msg:
        return render_template('404.html'), 404
    
    like_count = len(msg.likes)

    return render_template('messages/show.html', message=msg, liked=liked, like_count=like_count)


@app.route('/messages/<int:message_id>/like', methods=["POST"])
def messages_like(message_id):
    """Like or unlike a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/login")

    msg = Message.query.get(message_id)

    if not msg:
        flash('Message not found.', 'danger')
        return redirect('/')

    if msg.user_id == g.user.id:
        flash("You can't like your own message.", "danger")
        return redirect(f'/messages/{message_id}')

    if msg in g.user.likes:
        g.user.likes.remove(msg)
        db.session.commit()
        flash('Message unliked.', 'danger')
    else:
        g.user.likes.append(msg)
        db.session.commit()
        flash('Message liked!', 'success')

    return redirect(url_for('messages_show', message_id=message_id))


@app.route('/messages/<int:message_id>/likes', methods=["GET"])
def message_likes(message_id):
    """Show the users who liked a message."""
    msg = Message.query.get(message_id)

    if not msg:
        flash('Message not found.', 'danger')
        return redirect('/')

    liked_users = User.query.join(Likes).filter(Likes.message_id == message_id).all()

    return render_template('messages/liked.html', liked_users=liked_users, message=msg)



@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)
    
    db.session.delete(msg)
    db.session.commit()

    return redirect(f'/users/{g.user.id}')



##############################################################################
# Warble Likes?

@app.route('/warble_like', methods=["POST"])
def like_warble():
    user_id = request.form.get('user_id')
    warble_id = request.form.get('warble_id')

    user = User.query.get(user_id)
    user.liked_warble_count += 1
    db.session.commit()

    like = Like(user_id=user_id, warble_id=warble_id)
    db.session.add(like)
    db.session.commit()

    return 'Warble Liked'

@app.route('/unlike_warble', methods=['POST'])
def unlike_warble():
    user_id = request.form.get('user_id')
    warble_id = request.form.get('warble_id')

    user = User.query.get(user_id)
    user.liked_warbles_count -= 1
    db.session.commit()

    like = Like.query.filter_by(user_id=user_id, warble_id=warble_id).first()
    db.session.delete(like)
    db.session.commit()

    return 'Warble unliked!'


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        messages = (Message
                    .query
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        liked_messages = [msg.id for msg in g.user.likes]

        return render_template('home.html', messages=messages, liked_messages=liked_messages)

    else:
        return render_template('home-anon.html')


@app.errorhandler(404)
def page_not_found(e):
    """Show 404 NOT FOUND page."""

    return render_template('404.html'), 404

##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
