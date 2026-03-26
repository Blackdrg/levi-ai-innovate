# DEPRECATED: Legacy Training Models
# This application is now Firestore-native.

try:
    from backend.db import Base # type: ignore
except ImportError:
    from db import Base # type: ignore

class TrainingData(Base):
    __tablename__ = 'training_data'
class PromptPerformance(Base):
    __tablename__ = 'prompt_performance'
class ModelVersion(Base):
    __tablename__ = 'model_versions'
class TrainingJob(Base):
    __tablename__ = 'training_jobs'
class ResponseFeedback(Base):
    __tablename__ = 'response_feedback'
