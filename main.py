from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_wtf import FlaskForm
from flask_ckeditor import CKEditor, CKEditorField
from flask_login import LoginManager, login_user, login_required, UserMixin, current_user, logout_user
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired, URL, Length, Email
from werkzeug.security import generate_password_hash, check_password_hash
from flask_gravatar import Gravatar
from functools import wraps
import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap(app)
ckeditor = CKEditor()


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##Flask Gravatar
gravatar = Gravatar(app,
                    size=100,
                    rating='x',
                    default='identicon',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


##CONFIGURE TABLES
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    posts = db.relationship('BlogPost', back_populates='author')
    comments = db.relationship('Comments', back_populates='user')


class BlogPost(db.Model):
    __tablename__ = 'blog_post'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    img_url = db.Column(db.String(250), nullable=False)
    author = db.relationship('User', back_populates='posts')
    comments = db.relationship('Comments', back_populates='blog')



class Comments(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    blog_id = db.Column(db.Integer, db.ForeignKey('blog_post.id'))
    author = db.Column(db.String(250), nullable=False)
    text = db.Column(db.Text, nullable=False)
    user = db.relationship('User', back_populates='comments')
    blog = db.relationship('BlogPost', back_populates='comments')

# main.Comments.query.all()
# main.BlogPost.query.all()
# main.User.query.all()
db.create_all()


##WTForms
class PostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[InputRequired('Please enter a title')])
    subtitle = StringField("Subtitle", validators=[InputRequired('Please enter a subtitle')])
    img_url = StringField("Blog Image URL", validators=[InputRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[InputRequired('Please enter a post')])
    submit = SubmitField("Submit Post")


class loginForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email("Please enter your email address.")])
    password = StringField("Password", validators=[InputRequired('Please enter your a password'), Length(min=6, max=35)])
    submit = SubmitField("Submit Post")


class registerForm(FlaskForm):
    name = StringField("Name", validators=[InputRequired('Please enter your name')])
    email = StringField("Email", validators=[InputRequired(), Email("Please enter your email address.")])
    password = StringField("Password", validators=[InputRequired('Please enter your a password'), Length(min=6, max=35)])
    submit = SubmitField("Submit Post")


login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "please login to create a post"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


#Create admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)        
    return decorated_function


@app.route('/')
def get_all_posts():
    # Query database for all blog post
    posts = db.session.query(BlogPost).all()
    return render_template("index.html", all_posts=posts)


# SHOW AND COMMENT POST
@app.route("/post/<int:index>", methods=['GET', 'POST'])
@login_required
def show_post(index):


    # find the post user clicked on
    posts = db.session.query(BlogPost).all()
    requested_post = None
    for blog_post in posts:
        if blog_post.id == index:
            requested_post = blog_post

    # add a comment to a post
    if request.method == 'POST':
        new_comment = Comments(
            author_id = current_user.id,
            blog_id = requested_post.id,
            author = current_user.name,
            text = request.form.get('ckeditor')
        )
        db.session.add(new_comment)
        db.session.commit()

    # fine comments for blog
    comments = db.session.query(Comments).all()
    blog_comments = [comment for comment in comments \
                    if comment.blog_id == requested_post.id]
    return render_template("post.html",
                            post=requested_post,
                            comments=blog_comments,
                            grav=gravatar)


# NEW POST
@app.route("/new_post", methods=['POST', 'GET'])
@login_required
def new_post():
    print(current_user)
    # create instaance of blog post form 
    form = PostForm()

    # get current date and formate date
    current_date = datetime.datetime.now()
    date_formate = current_date.strftime("%B %d,%Y")


    # create Blog post and store post in BlogPost table
    if request.method == 'POST' and form.validate():
        create_post = BlogPost(
            title = form.title.data,
            subtitle = form.subtitle.data,
            date = date_formate,
            body = form.body.data,
            author_id = current_user.id,
            img_url = form.img_url.data
            )

        # add post to database
        db.session.add(create_post)
        db.session.commit()

        # redirect to home page
        return redirect(url_for('get_all_posts'))
    return render_template("make-post.html", form=form, date=date_formate)


# EDIT POST
@app.route("/edit_post/<int:post_id>", methods=['POST', 'GET'])
@admin_only
def edit_post(post_id):

    post = BlogPost.query.get(post_id)

    # populate post with with current data
    form = PostForm(
        title = post.title,
        subtitle = post.subtitle,
        author = post.author,
        img_url = post.img_url,
        body = post.body
        )
    url = str(request.url_rule).split('/')[1]

    if request.method == 'POST' and form.validate():
        post.title = form.title.data
        post.subtitle = form.subtitle.data
        post.author = form.author.data
        post.img_url = form.img_url.data
        post.body = form.body.data
        db.session.commit()

    return render_template("make-post.html", form=form, url=url)


# DELETE POST
@app.route("/delete/<int:post_id>/<string:tp>")
@admin_only
def delete(post_id, tp):
    if tp == 'post':
        post = BlogPost.query.get(post_id)
        db.session.delete(post)
        db.session.commit()
    elif tp == 'comment':
        comment = Comments.query.get(post_id)
        db.session.delete(comment)
        db.session.commit()        
    return redirect(url_for('get_all_posts'))


# REGISTAR USER
@app.route("/register", methods=['POST', 'GET'])
def register():

    # create instaance of registration form 
    form = registerForm()

    if request.method == 'POST' and form.validate():

        if User.query.filter_by(email=form.email.data).first():

            # send flash messsage
            flash("You've already signed up with that email, \
                log in instead!")
            
            # redirect to /login route.
            return redirect(url_for('login'))

        # create a instance of a new user
        register_user = User(
            name = form.name.data,
            email = form.email.data,
            password = form.password.data
            )

        # add new user to database
        db.session.add(register_user)
        db.session.commit()

        # redirect to login page
        return redirect(url_for('login'))
    return render_template("register.html", form=form)


# LOGIN USER
@app.route("/login", methods=['POST', 'GET'])
def login():
    form = loginForm()
    # If form is login for is valid
    if request.method == 'POST' and form.validate():

        login_password = form.password.data
        print(form.email.data)
        user = User.query.filter_by(email=form.email.data).first()
        print(user)
        if user == None:
            flash('User not found')
            return redirect(url_for('login'))
        else:
            login_user(user)
            flash('You are now login and can create a post')
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form)


# LOGOUT USER
@app.route("/logout")
def logout():
    logout_user()
    flash('You have now been logged out')
    return redirect(url_for('get_all_posts'))


# ABOUT PAGE
@app.route("/about")
def about():
    print(current_user.is_active)
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    login_manager.init_app(app)
    ckeditor.init_app(app)
    app.run(debug=True)
    app.run(host='127.0.0.1', port=5000)









































