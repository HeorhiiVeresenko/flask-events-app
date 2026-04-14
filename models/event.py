from .db import db
from datetime import datetime

event_participants = db.Table(
    'event_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('event_id', db.Integer, db.ForeignKey('events.id'))
)

class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    participants = db.relationship(
        'User',
        secondary=event_participants,
        backref='joined_events'
    )
    comments = db.relationship(
        'Comment',
        backref='event',
        cascade="all, delete"
    )