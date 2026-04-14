from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from models.db import db
from models.user import User
from models.event import Event
from models.comment import Comment
from datetime import datetime
from flask_migrate import Migrate

import os

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///databaseTemProject.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.secret_key = 'super_secret_key' #for session

migrate = Migrate(app, db)
db.init_app(app)
#with app.app_context():
    #db.create_all()


def login_required(func): #перевірка чи залогинився користувач
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return func(*args, **kwargs)
    return wrapper


from sqlalchemy import func

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    search_text = request.args.get('search', '').strip()
    date_val = request.args.get('date', '').strip()

    all_events = Event.query.order_by(Event.event_date.asc()).all()
    events = []

    if search_text:
        search_text = search_text.lower()
        for event in all_events:
            if search_text in event.title.lower():
                if date_val:
                    if event.event_date.strftime('%Y-%m-%d') == date_val:
                        events.append(event)
                else:
                    events.append(event)
    elif date_val:
        for event in all_events:
            if event.event_date.strftime('%Y-%m-%d') == date_val:
                events.append(event)
    else:
        events = all_events
    
    return render_template('index.html', events=events)


@login_required
@app.route('/add-event', methods=['GET', 'POST'])
def add_event():
    if request.method =='POST':
        title = request.form.get('title')
        description = request.form.get('description')
        date_str = request.form.get('event_date')
        date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')

        new_event = Event(title=title, description=description, event_date=date_obj, author_id=session['user_id']) #додав автора
        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_event.html')

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template('event.html', event=event)



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        user_class = request.form['class']
        password = request.form['password']

        existing_user = User.query.filter_by(name=name).first()
        if existing_user:
            return "User already exists"

        hashed_password = generate_password_hash(password) #додаткова безпека пароля

        new_user = User(
            name=name,
            user_class=user_class,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        user = User.query.filter_by(name=name).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            return redirect('/')

        return "Invalid login or password"

    return render_template('login.html')

@login_required
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')



def is_author(event):  #перевірка чи є користувач автором події
    return 'user_id' in session and event.author_id == session['user_id'] 


@login_required
@app.route('/event/<int:event_id>/edit', methods=['GET', 'POST'])
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)

    if not is_author(event):  #додатковий захист якщо буде баг з кнопками
        return "У тебе немає прав редагувати цю подію"  

    if request.method == 'POST':
        event.title = request.form.get('title')
        event.description = request.form.get('description')

        date_str = request.form.get('event_date')
        event.event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')

        db.session.commit()
        return redirect(url_for('event_detail', event_id=event.id))

    return render_template('edit_event.html', event=event)


@login_required
@app.route('/event/<int:event_id>/delete', methods=['POST'])
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)

    if not is_author(event):   #додатковий захист якщо буде баг з кнопками
        return "У тебе немає прав видаляти цю подію"

    db.session.delete(event)
    db.session.commit()

    return redirect(url_for('index'))


@login_required
@app.route('/event/<int:event_id>/register', methods=['POST'])
def register_for_event(event_id):
    event = Event.query.get_or_404(event_id)
    user = User.query.get(session['user_id'])

    # щоб не можна було записатися двічі
    if user not in event.participants:
        event.participants.append(user)
        db.session.commit()

    return redirect(url_for('event_detail', event_id=event_id))


@login_required
@app.route('/event/<int:event_id>/leave', methods=['POST'])
def leave_event(event_id):
    event = Event.query.get_or_404(event_id)
    user = User.query.get(session['user_id'])

    if user in event.participants:
        event.participants.remove(user)
        db.session.commit()

    return redirect(url_for('event_detail', event_id=event_id))


@login_required
@app.route('/event/<int:event_id>/comment', methods=['POST'])
def add_comment(event_id):
    text = request.form.get('text')

    comment = Comment(
        text=text,
        user_id=session['user_id'],
        event_id=event_id
    )

    db.session.add(comment)
    db.session.commit()

    return redirect(url_for('event_detail', event_id=event_id))


@app.route('/api/events', methods=['GET'])
def api_get_events():
    events = Event.query.all()

    result = []
    for event in events:
        result.append({
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "event_date": event.event_date.isoformat(),
            "created_at": event.created_at.isoformat(),
            "author": event.author.name if event.author else None,
            "participants": [user.name for user in event.participants],
            "comments": [
                {
                    "id": comment.id,
                    "text": comment.text,
                    "user": comment.user.name if comment.user else None
                }
                for comment in event.comments
            ]
        })

    return jsonify(result)

port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    app.run(debug=True)