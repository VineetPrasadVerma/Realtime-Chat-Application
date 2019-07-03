from flask import Flask, render_template, request, session, logging, url_for, redirect, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from passlib.hash import sha256_crypt
from flask_socketio import SocketIO, send, emit
from aylienapiclient import textapi
import emoji

engine = create_engine("mysql+pymysql://root:root@localhost/register")
db = scoped_session(sessionmaker(bind=engine))
app = Flask('__name__')
app.config['SECRET_KEY'] = 'mysecret'
socketio = SocketIO(app)
client = textapi.Client("c2e91675", "c7a5903ceb7a1958a6e59b9ad5bda019")

# logged_in_users = set() # TODO: Make it work with set
logged_in_users = []


@app.route("/")
def home():
    return render_template("home.html")

#register form
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        secure_password = sha256_crypt.encrypt(str(password))

        new_value = db.execute("SELECT username from users where username = :username", {"username": username}).fetchone()
        if new_value is not None:
            flash("Username already exist !!", "danger")
            return redirect(url_for('login'))
        elif password == confirm:
            db.execute("INSERT INTO USERS(name, username, password) VALUES(:name, :username, :password)",
                       {"name": name, "username": username, "password": secure_password})
            db.commit()
            flash("You are registered and can login", "success")
            return redirect(url_for('login'))
        else:
            flash("Password does not match", "danger")
            return render_template("register.html")

    return render_template("register.html")

#login form
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("name")
        password = request.form.get("password")

        usernamedata = db.execute("SELECT username FROM users WHERE username=:username", {"username": username}).fetchone()
        passworddata = db.execute("SELECT password FROM users WHERE username=:username", {"username": username}).fetchone()

        if usernamedata is None:
            flash("No username found", "danger")
            return render_template("login.html")
        else:
            for password_data in passworddata:
                if sha256_crypt.verify(password, password_data):
                    session["log"] = True
                    user_name = usernamedata[0]
                    session["user_name"] = user_name
                    flash("You are now logged in", "success")
                    messages = username
                    #logged_in_users.add(user_name)
                    #logged_in_users.append(user_name)
                    print(logged_in_users)
                    return redirect(url_for('photo', messages=messages))
                else:
                    flash("Incorrect password", "danger")
                    return render_template("login.html")
    return render_template("login.html")

#photo
@app.route("/photo")
def photo():
    messages = request.args['messages']
    return render_template("photo.html", messages=messages)

#logout
@app.route("/logout")
def logout():
    #print("logout funvtion")
    user_name = session.get("user_name")
    if user_name in logged_in_users:
        logged_in_users.remove(user_name)
    session.clear()
    socketio.emit('online', logged_in_users)
    flash("You are now logged out !!", "success")
    #print(logged_in_users)
    return redirect(url_for('login'))


@socketio.on('message')
def handle_message(msg):
    emoji_image = emoji.emojize(":neutral face:")
    sentiment = client.Sentiment({'text': msg})
    print(sentiment)
    value_for_emoji = sentiment.get('polarity')
    print('Message: ' + msg)
    if value_for_emoji == 'positive':
        emoji_image = emoji.emojize(":grinning_face_with_big_eyes:")
    elif value_for_emoji == 'negative':
        emoji_image = emoji.emojize(":frowning_face:")
    elif value_for_emoji == 'neutral':
        emoji_image = emoji.emojize(":neutral_face:")
    else:
        emoji_image = emoji.emojize(":neutral face:")
    send(msg+" "+emoji_image, broadcast=True)


@socketio.on('connect')
def handle_connect():
    user_name = session.get("user_name")
    logged_in_users.append(user_name)
    emit('online', logged_in_users, broadcast=True)


if __name__ == "__main__":
    app.secret_key = "captainjacksparrow"
    socketio.run(app)
    app.run(debug=True)