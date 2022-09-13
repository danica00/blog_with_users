import errno
import os
import smtplib
from functools import wraps
import flask
from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar
SENDER = 'danicaspiano@gmail.com'
PASSWORD = 'xfutmfrvaurqmoxx'


###############MY FORMS FROM FORMS.PY################
from forms import CreatePostForm
from forms import RegisterForm
from forms import LoginForm
from forms import CommentForm


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
#########ikonice za komentare usera##########################
gravatar = Gravatar(
    app,
    size=100,
    rating='g',
    default='identicon',
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None
)

################LOGIN SETUP##########################
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES
class User(UserMixin,db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25),unique=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(100))
    posts = relationship("BlogPost", back_populates='author') #posts je veza sa blogpostovima, preko autora sto ima tamo
    comments = relationship("Comment", back_populates='commenter')
db.create_all()

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = relationship("User", back_populates="posts") #author je veza sa posts iz druge tabele

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    #**************parent relationship************************
    comments = relationship("Comment", back_populates='parent_post')

db.create_all()

class Comment(db.Model):
    __tablename__="comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    # *******Add child relationship*******#
    # "users.id" The users refers to the tablename of the Users class.
    # "comments" refers to the comments property in the User class.
    commenter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    commenter = relationship("User", back_populates="comments")
    #*********child to blogpost parent*************************
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id")) #u svaki child mora da se doda ovaj foreign key. uzme se naziv tabele pa -.id
    parent_post = relationship("BlogPost", back_populates="comments")

db.create_all()

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET","POST"])
def register():
    form = RegisterForm()
    the_email = form.email.data
    user = User.query.filter_by(email=the_email).first()
    if form.validate_on_submit():
        if user:
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        else:
            new_user = User(
                name=form.name.data,
                email=form.email.data,
                password=generate_password_hash(
                    password=form.password.data,
                    method='pbkdf2:sha256',
                    salt_length=8

                )
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form)



@app.route('/login', methods= ["GET",'POST'])
def login():
    form=LoginForm()
    the_email=form.email.data
    password=form.password.data
    user= User.query.filter_by(email=the_email).first()
    if form.validate_on_submit():
        if not user:
            flash("That email does not exist, please try again. If you haven't registered first, go to register.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['POST','GET'])
def show_post(post_id):
    form=CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                text=form.comment.data,
                commenter = current_user,
                parent_post =requested_post
            )
            db.session.add(new_comment)
            db.session.commit()
        else:
            flash("You are not logged in. Please log in first")
            return redirect(url_for('login'))
        return redirect(url_for('get_all_posts'))

    requested_post = BlogPost.query.get(post_id)
    return render_template("post.html", post=requested_post, form=form, comments=requested_post.comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["POST","GET"])
def contact():
    if request.method == 'POST':
        data = request.form
        send_email(data["name"], data["email"], data["phone"], data["message"])
        return render_template("contact.html", msg_sent=True)
    return render_template("contact.html", msg_sent=False)

def send_email(name, email, phone, message):
    email_message = f"Subject:New Message\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage:{message}"

    with smtplib.SMTP_SSL("smtp.gmail.com", port=465) as connection:
        connection.login(user=SENDER, password=PASSWORD)
        connection.sendmail(
            from_addr=SENDER,
            to_addrs=SENDER,
            msg=email_message
        )
    return render_template('contact.html')

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            abort(404, description="You are not allowed here.")
            # return os.strerror(404) ali ovde pise samo Unknown error
        # Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function

@app.route("/new-post", methods=["GET","POST"])
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


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
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
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))



if __name__ == "__main__":
    app.run(debug=True)
