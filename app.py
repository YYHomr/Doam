import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'doam_online_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['BLOG_UPLOAD_FOLDER'] = 'static/blog_uploads'
app.config['DATA_FILE'] = 'data.json'
app.config['BLOG_DATA_FILE'] = 'blog_data.json'
app.config['UPLOAD_PASSWORD'] = 'Blue!Falcon-72&RiverHorse'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['BLOG_UPLOAD_FOLDER'], exist_ok=True)

def load_data():
    if not os.path.exists(app.config['DATA_FILE']):
        return []
    with open(app.config['DATA_FILE'], 'r') as f:
        try:
            data = json.load(f)
            for entry in data:
                if 'is_top' not in entry: entry['is_top'] = False
                if 'rating' not in entry: entry['rating'] = 5.0
                if 'extra_images' not in entry: entry['extra_images'] = []
            return data
        except json.JSONDecodeError:
            return []

def save_data(data):
    with open(app.config['DATA_FILE'], 'w') as f:
        json.dump(data, f, indent=4)

def load_blog_data():
    if not os.path.exists(app.config['BLOG_DATA_FILE']):
        return []
    with open(app.config['BLOG_DATA_FILE'], 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_blog_data(data):
    with open(app.config['BLOG_DATA_FILE'], 'w') as f:
        json.dump(data, f, indent=4)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    games = load_data()
    top_games = [g for g in games if g.get('is_top')]
    return render_template('index.html', games=games, top_games=top_games)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == app.config['UPLOAD_PASSWORD']:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid password!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    games = load_data()
    blog_posts = load_blog_data()
    return render_template('admin.html', games=games, blog_posts=blog_posts)

def handle_uploads(files, folder=None):
    if folder is None:
        folder = app.config['UPLOAD_FOLDER']
    filenames = []
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            # Add timestamp to avoid collisions
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
            file.save(os.path.join(folder, filename))
            filenames.append(filename)
    return filenames

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        download_link = request.form.get('download_link')
        video_link = request.form.get('video_link')
        rating = float(request.form.get('rating', 5.0))
        is_top = 'is_top' in request.form
        
        image = request.files.get('image')
        extra_images = request.files.getlist('extra_images')
        
        if title and download_link:
            image_filename = None
            if image and image.filename:
                image_filename = handle_uploads([image])[0]
            
            extra_filenames = handle_uploads(extra_images)
            
            games = load_data()
            games.append({
                'title': title,
                'description': description,
                'download_link': download_link,
                'video_link': video_link,
                'image': image_filename,
                'extra_images': extra_filenames,
                'rating': rating,
                'is_top': is_top
            })
            save_data(games)
            flash(f'Game "{title}" added successfully!')
            return redirect(url_for('admin_dashboard'))
            
    return render_template('upload.html')

@app.route('/edit/<int:index>', methods=['GET', 'POST'])
@login_required
def edit_game(index):
    games = load_data()
    if index < 0 or index >= len(games):
        flash('Game not found!')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        games[index]['title'] = request.form.get('title')
        games[index]['description'] = request.form.get('description')
        games[index]['download_link'] = request.form.get('download_link')
        games[index]['video_link'] = request.form.get('video_link')
        games[index]['rating'] = float(request.form.get('rating', 5.0))
        games[index]['is_top'] = 'is_top' in request.form
        
        image = request.files.get('image')
        if image and image.filename:
            games[index]['image'] = handle_uploads([image])[0]
            
        extra_images = request.files.getlist('extra_images')
        new_extras = handle_uploads(extra_images)
        if new_extras:
            if 'extra_images' not in games[index]:
                games[index]['extra_images'] = []
            games[index]['extra_images'].extend(new_extras)
            
        save_data(games)
        flash(f'Game "{games[index]["title"]}" updated successfully!')
        return redirect(url_for('admin_dashboard'))
            
    return render_template('edit_game.html', game=games[index], index=index)

@app.route('/delete/<int:index>', methods=['POST'])
@login_required
def delete_game(index):
    games = load_data()
    if 0 <= index < len(games):
        deleted_game = games.pop(index)
        save_data(games)
        flash(f'Game "{deleted_game["title"]}" deleted successfully!')
    else:
        flash('Game not found!')
    return redirect(url_for('admin_dashboard'))

@app.route('/game/<int:index>')
def game_detail(index):
    games = load_data()
    if index < 0 or index >= len(games):
        flash('Game not found!')
        return redirect(url_for('index'))
    game = games[index]
    return render_template('game_detail.html', game=game, index=index, games=games)

# Blog Routes
@app.route('/blog')
def blog():
    posts = load_blog_data()
    # Sort posts by date descending
    posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return render_template('blog.html', posts=posts)

@app.route('/blog/<int:index>')
def blog_post(index):
    posts = load_blog_data()
    if 0 <= index < len(posts):
        post = posts[index]
        return render_template('blog_post.html', post=post, index=index)
    flash('Post not found!')
    return redirect(url_for('blog'))

@app.route('/admin/blog/add', methods=['GET', 'POST'])
@login_required
def add_blog_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        links = request.form.getlist('links')
        
        images = request.files.getlist('images')
        videos = request.files.getlist('videos')
        files = request.files.getlist('files')
        
        image_filenames = handle_uploads(images, app.config['BLOG_UPLOAD_FOLDER'])
        video_filenames = handle_uploads(videos, app.config['BLOG_UPLOAD_FOLDER'])
        file_filenames = handle_uploads(files, app.config['BLOG_UPLOAD_FOLDER'])
        
        posts = load_blog_data()
        posts.append({
            'title': title,
            'content': content,
            'links': [l for l in links if l],
            'images': image_filenames,
            'videos': video_filenames,
            'files': file_filenames,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        save_blog_data(posts)
        flash('Blog post added successfully!')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_blog_post.html')

@app.route('/admin/blog/edit/<int:index>', methods=['GET', 'POST'])
@login_required
def edit_blog_post(index):
    posts = load_blog_data()
    if index < 0 or index >= len(posts):
        flash('Post not found!')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        posts[index]['title'] = request.form.get('title')
        posts[index]['content'] = request.form.get('content')
        links = request.form.getlist('links')
        posts[index]['links'] = [l for l in links if l]
        
        images = request.files.getlist('images')
        videos = request.files.getlist('videos')
        files = request.files.getlist('files')
        
        posts[index]['images'].extend(handle_uploads(images, app.config['BLOG_UPLOAD_FOLDER']))
        posts[index]['videos'].extend(handle_uploads(videos, app.config['BLOG_UPLOAD_FOLDER']))
        posts[index]['files'].extend(handle_uploads(files, app.config['BLOG_UPLOAD_FOLDER']))
        
        save_blog_data(posts)
        flash('Blog post updated successfully!')
        return redirect(url_for('admin_dashboard'))
        
    return render_template('edit_blog_post.html', post=posts[index], index=index)

@app.route('/admin/blog/delete/<int:index>', methods=['POST'])
@login_required
def delete_blog_post(index):
    posts = load_blog_data()
    if 0 <= index < len(posts):
        posts.pop(index)
        save_blog_data(posts)
        flash('Blog post deleted successfully!')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5100)
