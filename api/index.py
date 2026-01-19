import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime

# --------------------
# App Setup
# --------------------
app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = "doam_online_secret_key"

# Vercel writable dir
BASE_TMP = "/tmp"

app.config.update(
    UPLOAD_FOLDER=f"{BASE_TMP}/images",
    BLOG_UPLOAD_FOLDER=f"{BASE_TMP}/blog_uploads",
    DATA_FILE=f"{BASE_TMP}/data.json",
    BLOG_DATA_FILE=f"{BASE_TMP}/blog_data.json",
    UPLOAD_PASSWORD="Blue!Falcon-72&RiverHorse"
)

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["BLOG_UPLOAD_FOLDER"], exist_ok=True)

# --------------------
# Helpers
# --------------------
def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def handle_uploads(files, folder):
    names = []
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
            file.save(os.path.join(folder, filename))
            names.append(filename)
    return names

# --------------------
# Routes
# --------------------
@app.route("/")
def index():
    games = load_json(app.config["DATA_FILE"])
    top_games = [g for g in games if g.get("is_top")]
    return render_template("index.html", games=games, top_games=top_games)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == app.config["UPLOAD_PASSWORD"]:
            session["logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Invalid password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/admin")
@login_required
def admin_dashboard():
    return render_template(
        "admin.html",
        games=load_json(app.config["DATA_FILE"]),
        blog_posts=load_json(app.config["BLOG_DATA_FILE"])
    )

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    games = load_json(app.config["DATA_FILE"])

    image = request.files.get("image")
    extras = request.files.getlist("extra_images")

    image_name = handle_uploads([image], app.config["UPLOAD_FOLDER"])[0] if image else None
    extra_names = handle_uploads(extras, app.config["UPLOAD_FOLDER"])

    games.append({
        "title": request.form.get("title"),
        "description": request.form.get("description"),
        "download_link": request.form.get("download_link"),
        "video_link": request.form.get("video_link"),
        "rating": float(request.form.get("rating", 5)),
        "is_top": "is_top" in request.form,
        "image": image_name,
        "extra_images": extra_names
    })

    save_json(app.config["DATA_FILE"], games)
    return redirect(url_for("admin_dashboard"))

# --------------------
# Vercel Handler
# --------------------
# Vercel automatically detects this Flask app
app = app
