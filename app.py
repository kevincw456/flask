import datetime
import random
from flask import Flask, flash
from flask import request, redirect, url_for, session
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "your-secret-key"

def get_db_connection():
    conn = psycopg2.connect(host='containers-us-west-47.railway.app',
                            database='railway',
                            user=os.environ['postgres'],
                            password=os.environ['TBhriWSdWLhEUtPo2kIj'])
    return conn


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))


@app.route('/home')
def home():
    if 'user_id' in session:
        user_id = session['user_id']

        cur = db_connection.cursor()

        cur.execute('SELECT COUNT(*) FROM tweets')
        total_tweets = cur.fetchone()[0]

        random_tweets = []
        if total_tweets > 0:
            random_tweet_ids = random.sample(range(1, total_tweets + 1), min(10, total_tweets))

            for tweet_id in random_tweet_ids:
                cur.execute('SELECT content, timestamp, user_id FROM tweets WHERE id=%s', (tweet_id,))
                tweet_data = cur.fetchone()
                if tweet_data:
                    tweet_content, tweet_timestamp, tweet_user_id = tweet_data
                    cur.execute('SELECT username FROM users WHERE id=%s', (tweet_user_id,))
                    tweet_username = cur.fetchone()[0]
                    random_tweets.append((tweet_content, tweet_timestamp, tweet_user_id, tweet_username))

        cur.close()
        return render_template('home.html', tweets=random_tweets)
    return redirect(url_for('login'))



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = db_connection.cursor()

        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()

        if user:
            return render_template('register.html', error_message="The username has been registered!")

        else:
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            db_connection.commit()
            cur.close()
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = ''

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = db_connection.cursor()

        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()

        if user:
            session['user_id'] = user[0]
            cur.close()
            return redirect(url_for('home'))
        else:
            error_message = 'Invalid username or password.'
            cur.close()

    return render_template('login.html', error_message=error_message)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))



@app.route('/tweet', methods=['POST'])
def tweet():
    if 'user_id' in session:
        content = request.form['content']
        user_id = session['user_id']

        cur = db_connection.cursor()

        timestamp = datetime.datetime.now()

        cur.execute("INSERT INTO tweets (content, user_id, timestamp) VALUES (%s, %s, %s)",
                    (content, user_id, timestamp))
        db_connection.commit()
        cur.close()

    return redirect(url_for('home'))



@app.route('/edit_tweet/<int:tweet_id>', methods=['GET', 'POST'])
def edit_tweet(tweet_id):
    if 'user_id' in session:
        user_id = session['user_id']
        if request.method == 'POST':
            content = request.form['content']

            cur = db_connection.cursor()

            cur.execute("UPDATE tweets SET content = %s WHERE id = %s AND user_id = %s", (content, tweet_id, user_id))
            db_connection.commit()
            cur.close()

            return redirect(url_for('profile'))
        else:
            cur = db_connection.cursor()

            cur.execute("SELECT content FROM tweets WHERE id = %s AND user_id = %s", (tweet_id, user_id))
            tweet_data = cur.fetchone()
            cur.close()

            if tweet_data:
                return render_template('edit_tweet.html', tweet_id=tweet_id, content=tweet_data[0])
            else:
                flash('You are not authorized to edit this tweet.')
                return redirect(url_for('profile'))
    else:
        return redirect(url_for('login'))




@app.route('/delete_tweet/<int:tweet_id>', methods=['GET', 'POST'])
def delete_tweet(tweet_id):
    if 'user_id' in session:
        user_id = session['user_id']

        cur = db_connection.cursor()

        cur.execute('DELETE FROM comments WHERE tweet_id=%s', (tweet_id,))
        cur.execute("DELETE FROM tweets WHERE id = %s AND user_id = %s", (tweet_id, user_id))

        db_connection.commit()
        cur.close()

        return redirect(url_for('profile'))
    else:
        return redirect(url_for('login'))


# app.py
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' in session:
        user_id = session['user_id']

        cur = db_connection.cursor()

        cur.execute('SELECT username, registration_time, bio FROM users WHERE id=%s', (user_id,))
        user_data = cur.fetchone()

        cur.execute('SELECT id, content, timestamp FROM tweets WHERE user_id=%s', (user_id,))
        tweets = cur.fetchall()

        tweet_data = []
        for tweet in tweets:
            tweet_id = tweet[0]
            cur.execute('SELECT COUNT(*) FROM comments WHERE tweet_id=%s', (tweet_id,))
            comment_count = cur.fetchone()[0]
            cur.execute('SELECT c.content, u.username, c.user_id FROM comments c LEFT JOIN users u ON c.user_id = u.id WHERE c.tweet_id=%s', (tweet_id,))
            comments = cur.fetchall()

            comments_with_username = []
            for comment in comments:
                comments_with_username.append((comment[0], comment[1], comment[2]))  # Store user_id as well

            cur.execute('SELECT id FROM likes WHERE tweet_id=%s AND user_id=%s', (tweet_id, user_id))
            liked = cur.fetchone() is not None

            tweet_data.append((tweet[0], tweet[1], tweet[2], comment_count, comments_with_username, liked))

        cur.execute('SELECT u.id, u.username FROM users u INNER JOIN follows f ON u.id = f.following_id WHERE f.follower_id=%s', (user_id,))
        following_users = cur.fetchall()

        cur.execute('SELECT t.id, t.content, t.timestamp FROM tweets t INNER JOIN likes l ON t.id = l.tweet_id WHERE l.user_id=%s', (user_id,))
        liked_tweets = cur.fetchall()

        if request.method == 'POST':
            new_bio = request.form['bio']
            cur.execute('UPDATE users SET bio=%s WHERE id=%s', (new_bio, user_id))
            db_connection.commit()
            user_data = list(user_data)
            user_data[2] = new_bio

        cur.close()
        return render_template('profile.html', username=user_data[0], registration_time=user_data[1],
                               bio=user_data[2], tweets=tweet_data, following_users=following_users,
                               liked_tweets=liked_tweets, user_id=user_id)
    return redirect(url_for('login'))



@app.route('/edit_bio', methods=['GET', 'POST'])
def edit_bio():
    if 'user_id' in session:
        user_id = session['user_id']
        cur = db_connection.cursor()

        cur.execute('SELECT bio FROM users WHERE id=%s', (user_id,))
        bio = cur.fetchone()[0]

        if request.method == 'POST':
            new_bio = request.form['bio']
            cur.execute('UPDATE users SET bio=%s WHERE id=%s', (new_bio, user_id))
            db_connection.commit()
            cur.close()
            return redirect(url_for('profile'))

        cur.close()
        return render_template('edit_bio.html', bio=bio)
    return redirect(url_for('login'))


@app.route('/user_profile/<int:user_id>', methods=['GET', 'POST'])
def user_profile(user_id):
    if 'user_id' in session:
        current_user_id = session['user_id']
        cur = db_connection.cursor()

        cur.execute('SELECT COUNT(*) FROM follows WHERE follower_id=%s AND following_id=%s',
                    (current_user_id, user_id))
        is_following = cur.fetchone()[0] > 0

        cur.execute('SELECT username, registration_time, bio FROM users WHERE id=%s', (user_id,))
        user_data = cur.fetchone()

        cur.execute('SELECT id, content, timestamp FROM tweets WHERE user_id=%s', (user_id,))
        tweets = cur.fetchall()

        if request.method == 'POST':
            if 'content' in request.form:
                content = request.form['content']
                cur.execute("INSERT INTO tweets (content, user_id) VALUES (%s, %s)", (content, current_user_id))
                db_connection.commit()
            elif 'comment' in request.form and 'tweet_id' in request.form and 'user_id' in request.form:
                tweet_id = request.form['tweet_id']
                comment_content = request.form['comment']
                user_id = request.form['user_id']
                cur.execute('INSERT INTO comments (tweet_id, content, user_id) VALUES (%s, %s, %s)',
                            (tweet_id, comment_content, user_id))
                db_connection.commit()
            elif 'like' in request.form:
                tweet_id = request.form.get('like')
                cur.execute('SELECT COUNT(*) FROM likes WHERE tweet_id=%s AND user_id=%s', (tweet_id, current_user_id))
                like_count = cur.fetchone()[0]

                if like_count == 0:
                    cur.execute('INSERT INTO likes (tweet_id, user_id) VALUES (%s, %s)', (tweet_id, current_user_id))
                else:
                    cur.execute('DELETE FROM likes WHERE tweet_id=%s AND user_id=%s', (tweet_id, current_user_id))

                db_connection.commit()

        tweet_data = []
        for tweet in tweets:
            tweet_id = tweet[0]
            cur.execute('SELECT COUNT(*) FROM comments WHERE tweet_id=%s', (tweet_id,))
            comment_count = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM likes WHERE tweet_id=%s AND user_id=%s', (tweet_id, current_user_id))
            like_count = cur.fetchone()[0]
            cur.execute('SELECT content, user_id, id FROM comments WHERE tweet_id=%s', (tweet_id,))
            comments = cur.fetchall()

            comments_with_username = []
            for comment in comments:
                cur.execute('SELECT username FROM users WHERE id=%s', (comment[1],))
                username = cur.fetchone()[0]
                comments_with_username.append((comment[0], username, comment[2]))

            tweet_data.append((tweet[0], tweet[1], tweet[2], comment_count, like_count, comments_with_username))

        cur.close()

        return render_template('user_profile.html', username=user_data[0], registration_time=user_data[1],
                               bio=user_data[2], tweets=tweet_data, user_id=user_id,
                               current_user_id=current_user_id, is_following=is_following)

    return redirect(url_for('login'))




@app.route('/follow/<int:user_id>', methods=['POST'])
def follow_user(user_id):
    if 'user_id' in session:
        current_user_id = session['user_id']

        cur = db_connection.cursor()

        cur.execute('SELECT COUNT(*) FROM follows WHERE follower_id=%s AND following_id=%s',
                    (current_user_id, user_id))
        relationship_exists = cur.fetchone()[0]

        if not relationship_exists:
            cur.execute('INSERT INTO follows (follower_id, following_id) VALUES (%s, %s)',
                        (current_user_id, user_id))
            db_connection.commit()
        else:
            cur.execute('DELETE FROM follows WHERE follower_id=%s AND following_id=%s',
                        (current_user_id, user_id))
            db_connection.commit()

        cur.execute('SELECT COUNT(*) FROM follows WHERE follower_id=%s AND following_id=%s',
                    (current_user_id, user_id))
        is_following = cur.fetchone()[0] > 0

        cur.close()

        return redirect(url_for('user_profile', user_id=user_id, is_following=is_following))

    return redirect(url_for('login'))



# @app.route('/delete_comment/<int:user_id>/<int:tweet_id>/<int:comment_id>', methods=['POST'])
# def delete_comment(user_id, tweet_id, comment_id):
#     if 'user_id' in session:
#         current_user_id = session['user_id']
#         if current_user_id == user_id:
#             conn = sqlite3.connect('db/database.db')
#             cur = conn.cursor()
#             cur.execute('DELETE FROM comments WHERE id=?', (comment_id,))
#             conn.commit()
#             conn.close()
#     return redirect(url_for('user_profile', user_id=user_id))

from flask import jsonify, render_template

@app.route('/search', methods=['GET'])
def search_results():
    query = request.args.get('query')

    cur = db_connection.cursor()
    cur.execute("SELECT id, username FROM users WHERE username LIKE %s", ('%' + query + '%',))
    results = cur.fetchall()
    cur.close()

    return jsonify({'results': [{'id': result[0], 'username': result[1]} for result in results]})

@app.route('/render_search', methods=['GET'])
def render_search_results():
    query = request.args.get('query')

    cur = db_connection.cursor()
    cur.execute("SELECT id, username FROM users WHERE username LIKE %s", ('%' + query + '%',))
    results = cur.fetchall()
    cur.close()

    return render_template('search_results.html', query=query, results=results)



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

