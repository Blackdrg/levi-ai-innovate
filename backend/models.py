# DEPRECATED: Legacy SQL Models
# This application is now Firestore-native.
# Use firestore_db.py and the document logic in logic files instead.

try:
    from backend.db import Base # type: ignore
except ImportError:
    from db import Base # type: ignore

class Quote(Base): pass
class Users(Base): pass
class ChatHistory(Base): pass
class UserMemory(Base): pass
class UserMemoryLog(Base): pass
class FeedItem(Base): pass
class Analytics(Base): pass
class PushSubscription(Base): pass
class PaymentEvent(Base): pass
class Persona(Base): pass