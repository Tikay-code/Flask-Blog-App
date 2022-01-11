from flask import Flask, redirect, render_template, request, session, url_for, abort, escape
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy
import sqlite3
import os
from datetime import datetime
import PIL
from PIL import Image


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SECRET_KEY"] = "secretkey"
app.config['UPLOAD_FOLDER'] = "static"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


#veriables
success = ""




db = SQLAlchemy(app)


class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(100), unique=True, nullable=False)
	password = db.Column(db.String(100), nullable=False)
	image = db.Column(db.String(100), nullable=False, default="default.png")


	def __repr__(self):
		return "<User {}>".format(self.username)


class Posts(db.Model):
	post_id = db.Column(db.Integer, primary_key=True)
	author = db.Column(db.String(100), nullable=False)
	author_image = db.Column(db.String(100), nullable=False)
	title = db.Column(db.String(100), nullable=False)
	description = db.Column(db.String(800), nullable=False)
	post_image = db.Column(db.String(100), nullable=True)
	date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
	text = db.Column(db.Text, nullable=False)
	# need to do a relationship so I can access to the user image
	def __repr__(self):
		return "<Post ('{}', '{}')>".format(self.author, self.title)


class Comment(db.Model):
	comment_id = db.Column(db.Integer, primary_key=True)
	post_id = db.Column(db.Integer, nullable=False)
	writer = db.Column(db.String(100), nullable=False)
	text = db.Column(db.String(100), nullable=False)
	date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
	# need to do a relationship so I can access to the user image
	def __repr__(self):
		return "<Comment ('{}', '{}')>".format(self.writer, self.date_posted)



# fucntions
def resize_image(imagePath, file):
	try:
		image = Image.open(imagePath)
		width = image.size[0]
		newHeight = width
		newImg = image.resize((400, 400))
		newImg.save("static/users_pic/{}.{}".format(file, image.format))
		os.remove(imagePath)
		return image.format
	except PIL.UnidentifiedImageError:
		return ""


# maybe add a link to the post and there will be comments or something?
@app.route("/")
def home():
	global success
	page = request.args.get('page', 1, type=int)
	posts = Posts.query.paginate(page=page, per_page=5)
	if "user" in session:
		user = session["user"]
		mysuccess = success
		success = ""
		return render_template("home.html", user=user, posts=posts, logged=True, success=mysuccess)

	else:
		return render_template("home.html", posts=posts, logged=False)


# login - note: vulnerable to sqli (well, depends of what u consider to vulnerable..)
@app.route("/login", methods=["POST", "GET"])
def login():
	global data
	if "user" not in session:
		if request.method == "POST":
			if "user" not in session:
				username = request.form['username']
				password = request.form["password"]
				user_logged = User.query.filter_by(username=username).first()
				if user_logged != None:
					if username == user_logged.username and password == user_logged.password:
						#if user_logged.username == username and user_logged.password == password:
						session['user'] = user_logged.username
						return redirect("/")
					else:
						return render_template("login.html", errors="1")
				else:
					return render_template("login.html", errors="1")

			else:
				return redirect("/")

		else:
			return render_template("login.html")
	else:
		return redirect("/")


# need to check if user can register an existed username.
@app.route("/register", methods=["POST", "GET"])
def register():
	if "user" not in session:
		if request.method == "POST":
			username = request.form["username"]
			password = request.form["password"]

			# vaildation
			if " " not in username and len(username) > 1 and " " not in password and len(password) > 1:
				conf_password = request.form["password_confirm"]
				if password != conf_password:
					return render_template("register.html", errors="6")
				newUser = User(username=username, password=password)
				try: 
					db.session.add(newUser)
					db.session.commit()
					return redirect('/login')

				except sqlalchemy.exc.IntegrityError:
					return render_template('register.html', errors="5")
				except Exception as e:
					return str(e)
			else:
				if len(username) < 2:
					return render_template("register.html", errors="1")
				elif " " in username:
					return render_template("register.html", errors="2")
				elif len(password) < 2:
					return render_template("register.html", errors="3")
				elif " " in password:
					return render_template("register.html", errors="4")
				else:
					return "<h1>Report this?</h1>"

		else:
			return render_template("register.html")
	else:
		return redirect("/login")


@app.route("/logout")
def logout():
	session.pop("user", None)
	return redirect("/")


@app.route("/account", methods=["POST", "GET"])
def account():
	if "user" in session:
		if request.method == "GET":
				user = session["user"]
				user_info = User.query.filter_by(username=user).first()
				user_image = user_info.image
				image_path = url_for("static", filename=f"users_pic/{user_image}")
				return render_template("account.html", user=user, image_path=image_path)
		else:
			newUsername = request.form["username"]
			oldUsername = User.query.filter_by(username=session['user']).first()
			image_path = url_for("static", filename=f"users_pic/{oldUsername.image}")
			if len(newUsername) < 2:
				return render_template("account.html", errors="2", user=session['user'], image_path=image_path)
			elif " " in newUsername:
				return render_template("account.html", errors="3", user=session['user'], image_path=image_path)

			# validation

			if User.query.filter_by(username=newUsername).first() == None:
				postsUsernameUpdate = Posts.query.filter_by(author=oldUsername.username).all()
				commentsUsernameUpdate = Comment.query.filter_by(writer=oldUsername.username).all()
				for post in postsUsernameUpdate:
					post.author = newUsername
				for comment in commentsUsernameUpdate:
					comment.writer = newUsername

				user = User.query.filter_by(username=session['user']).first()
				user.username = newUsername
				session['user'] = newUsername
				image_path = url_for("static", filename=f"users_pic/{user.image}")
				db.session.commit()

				return render_template("account.html", user=session['user'], image_path=image_path, success="1")
			else:
				if session['user'] != newUsername:
					user_info = User.query.filter_by(username=session['user']).first()
					image_path = url_for("static", filename=f"users_pic/{user_info.image}")
					return render_template("account.html", user=session['user'], image_path=image_path, errors="1")
				else:
					return redirect("/account")
	else:
		return redirect("/login")


# handle the error if user submit and there is no files - fixed
# edit user image and cut it with PIL otherwise the image will looks ugly
@app.route("/upload", methods=["POST"])
def upload():
	if "user" in session:
		userId = User.query.filter_by(username=session["user"]).first().id
		current_user = User.query.get_or_404(userId)
		postsImageUpdate = Posts.query.filter_by(author=current_user.username).all()

		newImage = request.files['image_file']
		if newImage.filename != '':
			sub = str(current_user.username)
			image_path = "static/users_pic/" + sub + "_" + newImage.filename
			newImage.save(image_path)
			extension = resize_image(image_path, sub)
			current_user.image = f"{sub}.{extension}"
			for post in postsImageUpdate:
				post.author_image = f"static/users_pic/{sub}.{extension}"

			db.session.commit()
			return redirect("/account")
		else:
			return redirect("/account")
	else:
		return redirect("/login")


# add options to remove the post image
@app.route("/newpost", methods=["POST", "GET"])
def new_post():
	global success
	if "user" in session:
		if request.method == "GET":
			return render_template("create_post.html", logged=True)
		else:
			author = session['user']
			title = request.form['title']
			description = request.form['description']
			description = str(escape(description)).replace('\n', '<br/>')
			content = request.form['content']
			content = str(escape(content)).replace('\n', '<br/>')
			image = request.files['image_file']

			if len(title) == 0:
				return render_template("create_post.html", errors="1")
			if len(description) == 0:
				return render_template("create_post.html", errors="2")
			if len(description) >= 500:
				return render_template("create_post.html", errors="3")
			elif len(content) == 0:
				return render_template("create_post.html", errors="4")

			else:
				user_image = str(User.query.filter_by(username=author).first().image)
				image_path = url_for("static", filename=f"users_pic/{user_image}")
				if image.filename == '':
					newPost = Posts(author=author, author_image=image_path, title=title, description=description, text=content)
				else:
					post_image = "static/posts_pic/" + str(author) + "_" + str(image.filename)
					image.save(post_image)
					newPost = Posts(author=author, author_image=image_path, title=title, text=content, description=description, post_image=post_image)

				db.session.add(newPost)
				db.session.commit()
				success = "3"
				return redirect("/")
	else:
		return redirect("/login")


@app.route("/delete/<int:id>", methods=["GET"])
def delete(id):
	global success
	if "user" in session:
		author = Posts.query.filter_by(post_id=id).first().author
		if session['user'] == author:
			postId = Posts.query.get_or_404(id)			
			try:
				commentsOfPost = Comment.query.filter_by(post_id=postId.post_id).all()
				ImageOfPost = postId.post_image
				if ImageOfPost != None:
					os.remove(ImageOfPost)
				for comment in commentsOfPost:
					db.session.delete(comment)
					db.session.commit()

				db.session.delete(postId)
				db.session.commit()
				success = "2"
				return redirect("/")

			except Exception as e:
				return str(e)
		else:
			return abort(403)

	else:
		return redirect("/login")


@app.route("/update/<int:id>", methods=["POST", "GET"])
def update(id):
	global success
	if 'user' in session:
		current_user = session['user']
		postAuthor = Posts.query.filter_by(post_id=id).first().author

		if current_user ==  postAuthor:
			if request.method == "GET":
				current_title = Posts.query.filter_by(post_id=id).first().title
				current_description = Posts.query.filter_by(post_id=id).first().description
				current_description = str(current_description).replace('<br/>', '\n')
				current_description = str(current_description).replace('&#39;', "'")
				current_description = str(current_description).replace('&#34;', '"')

				current_text = Posts.query.filter_by(post_id=id).first().text
				current_text = str(current_text).replace('<br/>', '\n')
				current_text = str(current_text).replace('&#39;', "'")
				current_text = str(current_text).replace('&#34;', '"')
				current_image = Posts.query.filter_by(post_id=id).first().post_image

				return render_template("update.html", title=current_title, text=current_text, description=current_description,\
				 image=current_image, id=id)

			else:
				newtitle = request.form['title']
				newdescription = request.form['description']
				newdescription = str(escape(newdescription)).replace('\n', '<br/>')
				newtext = request.form['content']
				newtext = str(escape(newtext)).replace('\n', '<br/>')
				newImage = request.files['image_file']

				if len(newtitle) == 0:
					return render_template("update.html", errors="1", id=id)
				if len(newdescription) == 0:
					return render_template("update.html", errors="2", id=id)
				if len(newdescription) >= 500:
					return render_template("update.html", errors="3", id=id)
				elif len(newtext) == 0:
					return render_template("update.html", errors="4", id=id)


				postToUpdate = Posts.query.get_or_404(id)

				if newImage.filename == '':
					image_path = Posts.query.get_or_404(id).post_image
				else:
					image_path = "static/posts_pic/" + str(session['user']) + "_" + str(newImage.filename)
					newImage.save(image_path)

				postToUpdate.title = newtitle
				postToUpdate.description = newdescription
				postToUpdate.text = newtext
				postToUpdate.post_image = image_path
				db.session.commit()
				posts = Posts.query.all()

				success = "1"
				return redirect("/")
				#return render_template("home.html", success="1", posts=posts, logged=True, user=session['user'])
		else:
			return abort(403)

	else:
		return redirect("/login")
# make an update function


#make to see other users posts!!
#maybe add an option to add as a friend or char with him
@app.route("/user/<name>", methods=["GET"])
def see_users(name):
	userToWatch = User.query.filter_by(username=name).first_or_404()
	usersPost = Posts.query.filter_by(author=userToWatch.username).all()
	postsNumber = Posts.query.filter_by(author=userToWatch.username).count()
	if "user" in session:
		return render_template("see_users.html", current_user=session['user'], seeUser=userToWatch, posts=usersPost, postsNumber=postsNumber, logged=True)
	else:
		return render_template("see_users.html", seeUser=userToWatch, logged=False, posts=usersPost, postsNumber=postsNumber)


@app.route("/post/<int:id>", methods=["POST", "GET"])
def post(id):
	if "user" in session:
		if request.method == "GET":
				post = Posts.query.get_or_404(id)
				comments = Comment.query.filter_by(post_id=id).all()
				return render_template("post.html", user=session['user'], post=post, comments=comments, logged=True)
		else:
			post = Posts.query.get_or_404(id)
			comments = Comment.query.filter_by(post_id=id).all()
			writer = session['user']
			text = request.form['awsometext']
			if len(text) < 1:
				return render_template("post.html", logged=True, user=session['user'], post=post, comments=comments, errors="1")
			text = str(escape(text)).replace('\n', '<br/>')
			newComment = Comment(post_id=id, writer=writer, text=text)
			db.session.add(newComment)
			db.session.commit()
			return redirect(f"/post/{id}")

	else:
		if request.method == "GET":
				post = Posts.query.get_or_404(id)
				comments = Comment.query.filter_by(post_id=id).all()
				return render_template("post.html", post=post, comments=comments, logged=False)

		else:
			return redirect("/login")


@app.route("/post/<int:id>/delete/<int:comment_id>", methods=['GET'])
def delete_comment(id, comment_id):
	if "user" in session:
			commentToDelete = Comment.query.get_or_404(comment_id)
			db.session.delete(commentToDelete)
			db.session.commit()
			return redirect(f"/post/{id}")
	else:
		return redirect("/login")


@app.route("/post/<int:id>/update/<int:comment_id>", methods=['POST', 'GET'])
def update_comment(id, comment_id):
	if "user" in session:
		if request.method == "GET":
			post = Posts.query.get_or_404(id)
			comments = Comment.query.filter_by(post_id=post.post_id).all()
			commentToUpdate = Comment.query.get_or_404(comment_id)
			current_text = str(commentToUpdate.text).replace('<br/>', '\n')
			current_text = str(current_text).replace('&#39;', "'")
			return render_template("post.html", logged=True, post=post, comments=comments, user=session["user"],\
				commentId=commentToUpdate, commentContent=current_text,type="update")

		else:
			post = Posts.query.get_or_404(id)
			comments = Comment.query.filter_by(post_id=post.post_id).all()
			commentToUpdate = Comment.query.get_or_404(comment_id)
			newText = request.form['awsometext']
			if len(newText) < 1:
				return render_template("post.html", logged=True, post=post, user=session['user'], comments=comments, errors="1")
			newText = str(escape(newText)).replace('\n', '<br/>')
			commentToUpdate.text = newText
			db.session.commit()
			return redirect(f"/post/{id}")

	else:
		return redirect("/login")




# handle 404 page
@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    if "user" in session:
    	return render_template('404.html', logged=True), 200

    else:
    	return render_template('404.html', logged=False), 200

# damn god it's starting to be a big app somehow :P


if __name__ == "__main__":
	app.run(debug=True)