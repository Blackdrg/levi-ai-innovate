# DEPRECATED: Legacy SQL Models
# This application is now Firestore-native.
# Use firestore_db.py and the document logic in logic files instead.

try:
    from backend.db import Base # type: ignore
except ImportError:
    from db import Base # type: ignore

class Quote(Base):
    __tablename__ = 'quotes'
class Users(Base):
    __tablename__ = 'users'
class ChatHistory(Base):
    __tablename__ = 'chat_history'
class UserMemory(Base):
    __tablename__ = 'user_memory'
class UserMemoryLog(Base):
    __tablename__ = 'user_memory_log'
class FeedItem(Base):
    __tablename__ = 'feed_items'
class Analytics(Base):
    __tablename__ = 'analytics'
class PushSubscription(Base):
    __tablename__ = 'push_subscriptions'
class PaymentEvent(Base):
    __tablename__ = 'payment_events'
class Persona(Base):
    __tablename__ = 'personas'