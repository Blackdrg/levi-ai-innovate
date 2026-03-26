# DEPRECATED: Legacy Training Models
# This application is now Firestore-native.

try:
    from backend.db import Base # type: ignore
except ImportError:
    from db import Base # type: ignore

class TrainingData(Base): pass
class PromptPerformance(Base): pass
class ModelVersion(Base): pass
class TrainingJob(Base): pass
class ResponseFeedback(Base): pass
