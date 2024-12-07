from flask import Flask, jsonify, request
import requests
import sqlite3

app = Flask(__name__)

DB_FILE = "coomer_kemono.db"

def db_connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/<platform>/<username>', methods=['GET'])
def get_user_data(platform, username):
    """
    Fetch user details and posts.
    """
    offset = request.args.get('offset', 0)
    platform_url = f"https://{platform}.su/api/v1/user/{username}?o={offset}"
    
    try:
        response = requests.get(platform_url)
        response.raise_for_status()
        data = response.json()
        
        # Store in database
        conn = db_connect()
        cur = conn.cursor()
        user = data.get("user", {})
        posts = data.get("posts", [])
        
        # Insert user if not exists
        cur.execute("INSERT OR IGNORE INTO users (id, username, total_posts) VALUES (?, ?, ?)",
                    (user['id'], username, len(posts)))
        
        # Insert posts
        for post in posts:
            cur.execute("INSERT OR IGNORE INTO posts (id, user_id, media_urls) VALUES (?, ?, ?)",
                        (post['id'], user['id'], str(post.get('media_urls', []))))
        
        conn.commit()
        return jsonify(data), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cdn/<platform>/<path:media_path>', methods=['GET'])
def get_cdn_media(platform, media_path):
    """
    Fetch media from CDN.
    """
    cdn_prefixes = [f"c{i}.{platform}.su" for i in range(1, 6)]
    for cdn in cdn_prefixes:
        url = f"https://{cdn}/{media_path}"
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                return jsonify({"cdn": cdn, "url": url}), 200
        except requests.exceptions.RequestException:
            continue
    return jsonify({"error": "Media not found on any CDN"}), 404

if __name__ == "__main__":
    app.run(debug=True)
