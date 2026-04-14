from .db import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_class = db.Column(db.String(20))
    password = db.Column(db.String(200))
    created_events = db.relationship('Event', backref='author')
    comments = db.relationship('Comment', backref='user')