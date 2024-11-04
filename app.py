import os
import json
import shutil
import threading
import webbrowser
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'uploads'
GAMES_METADATA_FILE = 'games.json'

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Max file size set to 32MB
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB

# Allowed file types
ALLOWED_EXTENSIONS = {'zip'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Load games metadata from JSON file
if os.path.exists(GAMES_METADATA_FILE):
    with open(GAMES_METADATA_FILE, 'r') as file:
        games_list = json.load(file)
else:
    games_list = []

@app.route('/')
def index():
    # Serve index.html from the current directory
    return send_from_directory(os.getcwd(), 'index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_game():
    if request.method == 'POST':
        game_title = request.form.get('title', '').strip()
        game_description = request.form.get('description', '').strip()
        game_file = request.files.get('game_file')

        if not game_title or not game_description:
            flash('Please provide a game title and description.')
            return redirect(url_for('upload_game'))

        # Check if file is selected and is a valid zip file
        if game_file and allowed_file(game_file.filename):
            game_id = len(games_list) + 1
            game_folder = os.path.join(UPLOAD_FOLDER, f'game_{game_id}')
            os.makedirs(game_folder, exist_ok=True)

            zip_path = os.path.join(game_folder, secure_filename(game_file.filename))

            try:
                # Save the zip file
                game_file.save(zip_path)
                
                # Extract the zip file contents
                shutil.unpack_archive(zip_path, game_folder)
                os.remove(zip_path)  # Remove the zip file after extraction

                # Check if index.html exists
                if not os.path.exists(os.path.join(game_folder, 'index.html')):
                    shutil.rmtree(game_folder)
                    flash('No index.html file found in the uploaded zip. Please include it.')
                    return redirect(url_for('upload_game'))

                # Add the game metadata
                game_entry = {
                    'id': game_id,
                    'title': game_title,
                    'description': game_description,
                    'file_path': f'/uploads/game_{game_id}/index.html'
                }
                games_list.append(game_entry)

                # Save metadata to JSON file
                with open(GAMES_METADATA_FILE, 'w') as file:
                    json.dump(games_list, file)

                flash(f'Game "{game_title}" uploaded successfully!')
                return redirect(url_for('list_games'))
            except Exception as e:
                shutil.rmtree(game_folder)
                flash(f'Error extracting the zip file: {str(e)}')
                return redirect(url_for('upload_game'))
        else:
            flash('Please upload a valid .zip file.')
            return redirect(url_for('upload_game'))

    return render_template('upload.html')

@app.route('/games')
def list_games():
    return render_template('games.html', games=games_list)

@app.route('/delete/<int:game_id>', methods=['POST'])
def delete_game(game_id):
    global games_list
    game = next((g for g in games_list if g['id'] == game_id), None)

    if not game:
        flash('Game not found')
        return redirect(url_for('list_games'))

    game_dir = os.path.join(UPLOAD_FOLDER, f'game_{game_id}')
    if os.path.exists(game_dir):
        shutil.rmtree(game_dir)

    games_list = [g for g in games_list if g['id'] != game_id]

    with open(GAMES_METADATA_FILE, 'w') as file:
        json.dump(games_list, file)

    flash(f'Game "{game["title"]}" deleted successfully!')
    return redirect(url_for('list_games'))

@app.route('/uploads/<path:filename>')
def serve_game(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    def open_browser():
        webbrowser.open('http://localhost:5000/')
    
    # Start the browser in a separate thread, without repeating the call
    threading.Timer(1, open_browser).start()
    
    # Run the Flask application
    app.run(debug=True)
