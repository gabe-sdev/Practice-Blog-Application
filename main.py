from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
import os
from dotenv import load_dotenv


app = Flask(__name__)
load_dotenv()
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login
# Initiate Flask Login Module
login_manager = LoginManager()
login_manager.init_app(app)

# For adding profile images to the comment section
# Initialize gravatar with flask application and default parameters:
gravatar = Gravatar(app, size=100, rating='g', default='retro',
                    force_default=False, force_lower=False, use_ssl=False, base_url=None)


# Create a user_loader callbackqe
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(UserAccts, user_id)


# Create an admin_only decorator
def admin_only(function):
    @wraps(function)
    def wrapper_function(*args, **kwargs):
        if current_user.id != 1:
            # If id is not 1 then return abort with 403 error
            return abort(403)
        # Otherwise continue with the route function
        return function(*args, **kwargs)
    return wrapper_function


# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Create Foreign Key, "user_accts.id" the user_accts refers to the tablename of UserAccts.
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user_accts.id"))
    # Create reference to the UserAccts object. The "posts" refers to the posts property in the UserAccts class.
    author = relationship("UserAccts", back_populates="posts")
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    # "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates="parent_post")


# TODO: Create a User table for all your registered users.
class UserAccts(UserMixin, db.Model):
    __tablename__ = "user_accts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    name: Mapped[str] = mapped_column(String(1000), nullable=False)
    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    # "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")


class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Create Foreign Key, "user_accts.id" the user_accts refers to the tablename of UserAccts.
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user_accts.id"))
    # "comments" refers to the comments property in the User class.
    comment_author = relationship("UserAccts", back_populates="comments")
    # Create Foreign Key, "blog_posts.id" the blog_posts refers to the tablename of BlogPosts.
    post_id: Mapped[str] = mapped_column(Integer, db.ForeignKey("blog_posts.id"))
    # Create reference to the BlogPosts object. The "comments" refers to the comments property in the BlogPosts class.
    parent_post = relationship("BlogPost", back_populates="comments")
    text: Mapped[str] = mapped_column(Text, nullable=False)


with app.app_context():
    db.create_all()


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=['GET', 'POST'])
def register():
    r_form = RegisterForm()
    if r_form.validate_on_submit():
        #Check is users email already exists in the DB
        email = r_form.email.data
        result = db.session.execute(db.select(UserAccts).where(UserAccts.email == email))
        # Note, email in db is unique so will only have one result.
        user = result.scalar()
        if user:
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_pass = generate_password_hash(password=r_form.password.data, method='pbkdf2:sha256', salt_length=8)
        new_user = UserAccts(
            name=r_form.name.data,
            email=r_form.email.data,
            password=hash_pass,
        )
        db.session.add(new_user)
        db.session.commit()
        # This line will authenticate the user with Flask-Login
        login_user(new_user)
        return redirect(url_for('get_all_posts'))

    return render_template("register.html", form=r_form)


# TODO: Retrieve a user from the database based on their email.
@app.route('/login', methods=["GET", "POST"])
def login():
    l_form = LoginForm()
    if l_form.validate_on_submit():
        # Retrieve the data entered by the user
        u_email = l_form.email.data
        u_password = l_form.password.data

        # Construct a query to select from the database. Returns the rows in the database to the 'results' variable
        # use the .scalars() and .all() method to take the elements inside the DB row and add them to a python list
        # named 'u_acct'
        result = db.session.execute(db.select(UserAccts).where(UserAccts.email == u_email))
        u_acct = result.scalar()

        # Email doesn't exist or password incorrect.
        if not u_acct:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(pwhash=u_acct.password, password=u_password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(u_acct)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=l_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    com_form = CommentForm()
    if com_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('You need to Login or register to comment')
            return redirect(url_for("login"))

        new_comment = Comment(
            text=com_form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post,
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, c_form=com_form)


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )

    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True,)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


#Inject a new variable named 'year' automatically into the context of all templates in the app
#to display the current year on the footer of each webpage.
@app.context_processor
def inject_year():
    return dict(year=date.today().year)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
