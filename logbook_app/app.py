# app.py
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, LogEntry
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///logbook.db"
app.config["UPLOAD_FOLDER"] = "static/uploads"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

db.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("list_entries"))
        flash("Invalid username or password")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def list_entries():
    entries = (
        LogEntry.query.filter_by(user_id=current_user.id)
        .order_by(LogEntry.create_date.desc())
        .all()
    )
    print(entries)
    return render_template("list.html", entries=entries)


@app.route("/create", methods=["GET", "POST"])
@login_required
def create_entry():
    if request.method == "POST":
        file = request.files["image"]
        description = request.form.get("description")
        if file:
            filename = secure_filename(file.filename)

            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            if os.path.exists(image_path):
                flash("This image already exists!")
                return redirect(url_for("create_entry"))

            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            entry = LogEntry(
                image_url=filename,
                user_id=current_user.id,
                description=description,
            )
            db.session.add(entry)
            db.session.commit()
            return redirect(url_for("list_entries"))
    return render_template("form.html")


@app.route("/delete/<int:entry_id>", methods=["POST"])
@login_required
def delete_entry(entry_id):
    entry: LogEntry = LogEntry.query.get_or_404(entry_id)

    if entry.user_id == current_user.id:
        if entry.image_url:
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], entry.image_url)
            if os.path.exists(image_path):
                os.remove(image_path)
        db.session.delete(entry)
        db.session.commit()
    return redirect(url_for("list_entries"))


@app.route("/edit/<int:entry_id>", methods=["GET", "POST"])
@login_required
def edit_entry(entry_id):
    entry: LogEntry = LogEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        return redirect(url_for("list_entries"))

    if request.method == "POST":
        description = request.form.get("description")
        file = request.files["image"]

        if file:
            if entry.image_url:
                old_image_path = os.path.join(
                    app.config["UPLOAD_FOLDER"], entry.image_url
                )
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)

            filename = secure_filename(file.filename)

            if os.path.exists(filename):
                flash("This image already exists!")
                return redirect(url_for("create_entry"))

            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            entry.image_url = filename

        entry.description = description
        entry.update_date = datetime.now()
        db.session.commit()
        return redirect(url_for("list_entries"))

    return render_template("edit.html", entry=entry)


if __name__ == "__main__":
    with app.app_context():
        # Create uploads directory if it doesn't exist
        if not os.path.exists("static/uploads"):
            os.makedirs("static/uploads")

        # Create database tables
        db.create_all()

        # Check if test user exists, if not create one
        if not User.query.filter_by(username="test").first():
            test_user = User(
                username="test", password=generate_password_hash("password")
            )
            db.session.add(test_user)
            db.session.commit()
            print("Test user created - Username: test, Password: password")

    app.run(debug=True)
