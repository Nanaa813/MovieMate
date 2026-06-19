import os
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "moviemate-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///moviemate.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Silakan login terlebih dahulu."
login_manager.init_app(app)

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    movie_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    poster_path = db.Column(db.String(255))
    release_date = db.Column(db.String(50))
    vote_average = db.Column(db.Float)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def tmdb_get(endpoint, params=None):
    if params is None:
        params = {}

    params["api_key"] = TMDB_API_KEY
    params["language"] = "en-US"

    response = requests.get(f"{TMDB_BASE_URL}{endpoint}", params=params, timeout=10)

    if response.status_code != 200:
        return {}

    return response.json()


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Semua field wajib diisi.")
            return redirect(url_for("register"))

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash("Username atau email sudah digunakan.")
            return redirect(url_for("register"))

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )

        db.session.add(user)
        db.session.commit()

        flash("Registrasi berhasil. Silakan login.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Email atau password salah.")
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("landing"))


@app.route("/dashboard")
@login_required
def dashboard():
    query = request.args.get("q", "").strip()

    if query:
        data = tmdb_get("/search/movie", {"query": query, "page": 1})
        title = f"Hasil pencarian: {query}"
    else:
        data = tmdb_get("/movie/popular", {"page": 1})
        title = "Film Populer Hari Ini"

    movies = data.get("results", [])
    return render_template(
        "dashboard.html",
        movies=movies,
        title=title,
        image_url=TMDB_IMAGE_URL,
        query=query
    )


@app.route("/movie/<int:movie_id>")
@login_required
def detail(movie_id):
    movie = tmdb_get(f"/movie/{movie_id}")
    return render_template("detail.html", movie=movie, image_url=TMDB_IMAGE_URL)


@app.route("/watchlist/add/<int:movie_id>")
@login_required
def add_watchlist(movie_id):
    existing = Watchlist.query.filter_by(
        user_id=current_user.id,
        movie_id=movie_id
    ).first()

    if existing:
        flash("Film sudah ada di watchlist.")
        return redirect(url_for("watchlist"))

    movie = tmdb_get(f"/movie/{movie_id}")

    item = Watchlist(
        user_id=current_user.id,
        movie_id=movie_id,
        title=movie.get("title", "Unknown Title"),
        poster_path=movie.get("poster_path"),
        release_date=movie.get("release_date"),
        vote_average=movie.get("vote_average")
    )

    db.session.add(item)
    db.session.commit()

    flash("Film berhasil ditambahkan ke watchlist.")
    return redirect(url_for("watchlist"))


@app.route("/watchlist")
@login_required
def watchlist():
    movies = Watchlist.query.filter_by(user_id=current_user.id).all()
    return render_template("watchlist.html", movies=movies, image_url=TMDB_IMAGE_URL)


@app.route("/watchlist/delete/<int:item_id>")
@login_required
def delete_watchlist(item_id):
    item = Watchlist.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()

    flash("Film berhasil dihapus dari watchlist.")
    return redirect(url_for("watchlist"))


@app.errorhandler(404)
def not_found(error):
    return render_template("base.html", error_message="Halaman tidak ditemukan."), 404


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)