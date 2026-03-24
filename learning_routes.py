"""
LEVI Learning Routes
Add these routes to backend/main.py
These enable real-time feedback collection and learning system monitoring.
"""

# ─────────────────────────────────────────────
# IMPORTS (add to the top of main.py)
# ─────────────────────────────────────────────
# from learning import (
#     collect_training_sample, UserPreferenceModel,
#     AdaptivePromptManager, get_learning_stats, infer_implicit_feedback
# )
# from trainer import trigger_training_pipeline, get_model_history, get_active_model_id
# from training_models import TrainingData, ResponseFeedback, ModelVersion, TrainingJob

# ─────────────────────────────────────────────
# PYDANTIC SCHEMAS (add to main.py)
# ─────────────────────────────────────────────
# class FeedbackRequest(BaseModel):
#     session_id: str
#     message_hash: str          # sha256 of the user message
#     rating: int                # 1-5
#     feedback_type: str = "star"
#
# class ImplicitFeedbackRequest(BaseModel):
#     session_id: str
#     bot_response: str
#     user_message: str
#     mood: str = "philosophical"

# ─────────────────────────────────────────────
# ROUTE ADDITIONS — copy these into main.py
# ─────────────────────────────────────────────

"""
PASTE THIS INTO main.py after the /chat route:
"""

LEARNING_ROUTES = '''

# ── Learning: Explicit Feedback ──────────────────────────────────────────────
class FeedbackRequest(BaseModel):
    session_id: str
    message_hash: str
    rating: int                 # 1-5
    bot_response: str
    user_message: str
    mood: Optional[str] = "philosophical"
    feedback_type: str = "star"

@app.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional),
):
    """
    User rates a response 1-5.
    Immediately stores the conversation as training data with the given rating.
    High-rated responses are added to the knowledge base in real-time.
    """
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    user_id = current_user.id if current_user else None

    try:
        from learning import collect_training_sample
        from training_models import ResponseFeedback

        # Store training sample
        sample = collect_training_sample(
            db=db,
            user_message=req.user_message,
            bot_response=req.bot_response,
            mood=req.mood or "philosophical",
            rating=req.rating,
            session_id=req.session_id,
            user_id=user_id,
        )

        # Store explicit feedback record
        fb = ResponseFeedback(
            training_data_id=sample.id,
            user_id=user_id,
            session_id=req.session_id,
            message_hash=req.message_hash,
            rating=req.rating,
            feedback_type=req.feedback_type,
        )
        db.add(fb)
        db.commit()

        return {"status": "success", "sample_id": sample.id, "rating": req.rating}

    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(status_code=500, detail="Failed to record feedback")


# ── Learning: Get personalised system prompt preview ─────────────────────────
@app.get("/learning/my_profile")
async def get_my_learning_profile(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Returns the AI's current learned profile for this user."""
    from learning import UserPreferenceModel
    model = UserPreferenceModel(db, current_user.id)
    profile = model.get_profile()
    return {
        "user_id": current_user.id,
        "profile": profile,
        "system_prompt_preview": model.build_system_prompt(
            "You are LEVI, a philosophical AI.", "philosophical"
        )[:200] + "...",
    }


# ── Learning: Admin stats ─────────────────────────────────────────────────────
@app.get("/learning/stats")
async def get_learning_stats_route(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Returns learning system statistics. Admin-level endpoint."""
    from learning import get_learning_stats
    stats = get_learning_stats(db)
    return stats


# ── Training: Model history ───────────────────────────────────────────────────
@app.get("/model/versions")
async def get_model_versions(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Returns all fine-tuned model versions."""
    from trainer import get_model_history, get_active_model_id
    versions = get_model_history(db)
    return {
        "active_model": get_active_model_id() or "groq/llama-3.1-8b-instant (base)",
        "versions": versions,
    }


# ── Training: Manually trigger a training run (admin only) ───────────────────
@app.post("/model/trigger_training")
async def trigger_training_manually(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Manually trigger a fine-tuning run. Admin use only."""
    # Basic admin check: only creator-tier users can trigger training
    if current_user.tier not in ("creator", "admin"):
        raise HTTPException(status_code=403, detail="Requires creator tier")

    from trainer import trigger_training_pipeline
    task = trigger_training_pipeline.delay()
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Training pipeline queued. Check /task_status/{task_id} for progress.",
    }


# ── Training: Current model status ───────────────────────────────────────────
@app.get("/model/status")
async def model_status(db: Session = Depends(get_db)):
    """Public endpoint: returns which model is powering LEVI right now."""
    from trainer import get_active_model_id
    from training_models import TrainingJob
    from learning import get_learning_stats

    active = get_active_model_id()
    stats  = get_learning_stats(db)

    # Latest training job
    latest_job = db.query(TrainingJob).order_by(TrainingJob.created_at.desc()).first()

    return {
        "active_model": active or "groq/llama-3.1-8b-instant",
        "is_fine_tuned": active is not None,
        "training_samples_collected": stats["total_training_samples"],
        "knowledge_base_entries":     stats["learned_quotes"],
        "latest_training_job": {
            "status": latest_job.status if latest_job else "none",
            "created_at": latest_job.created_at.isoformat() if latest_job else None,
        } if latest_job else None,
    }
'''

# ─────────────────────────────────────────────
# UPDATED /chat ROUTE (replace the existing one in main.py)
# This version collects training data on every turn.
# ─────────────────────────────────────────────

UPDATED_CHAT_ROUTE = '''
@app.post("/chat")
@limiter.limit("10/minute")
async def chat(
    request: Request,
    msg: ChatMessage,
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional),
):
    user_id = current_user.id if current_user else None
    logger.info(f"Chat [{msg.session_id}] (User: {user_id}): '{msg.message[:60]}'")

    # Analytics
    today = date.today()
    analytics = db.query(Analytics).filter(Analytics.date == today).first()
    if not analytics:
        analytics = Analytics(date=today, chats_count=1)
        db.add(analytics)
    else:
        analytics.chats_count = (analytics.chats_count or 0) + 1

    # User memory
    user_mem = None
    if user_id:
        user_mem = db.query(UserMemory).filter(UserMemory.user_id == user_id).first()
        if not user_mem:
            user_mem = UserMemory(user_id=user_id, mood_history=[], liked_topics=[], interaction_count=0)
            db.add(user_mem)
        user_mem.interaction_count += 1

    db.commit()

    # Load history
    history = get_conversation(msg.session_id)

    # Infer implicit feedback from previous turn
    try:
        from learning import infer_implicit_feedback, collect_training_sample
        implicit_rating = infer_implicit_feedback(history, msg.message)
        if implicit_rating and len(history) >= 1:
            prev = history[-1]
            collect_training_sample(
                db=db,
                user_message=prev.get("user", ""),
                bot_response=prev.get("bot", ""),
                mood=msg.mood or "philosophical",
                rating=implicit_rating,
                session_id=msg.session_id,
                user_id=user_id,
            )
    except Exception as e:
        logger.warning(f"Implicit feedback collection failed: {e}")

    # Build personalised system prompt for authenticated users
    personalized_system = None
    try:
        if user_id:
            from learning import UserPreferenceModel, AdaptivePromptManager
            pref = UserPreferenceModel(db, user_id)
            base = AdaptivePromptManager(db).get_best_variant(msg.mood or "philosophical")
            personalized_system = pref.build_system_prompt(base, msg.mood or "philosophical")
    except Exception:
        pass  # graceful degradation

    # Use fine-tuned model if available
    try:
        from trainer import generate_with_active_model
        if generate_with_active_model.__module__:  # check it imported
            bot_response = generate_with_active_model(
                prompt=msg.message,
                system_prompt=personalized_system or "You are LEVI, a philosophical AI muse.",
                max_tokens=150,
            )
            if not bot_response:
                raise ValueError("Empty response from active model")
    except Exception:
        # Fall back to standard generation
        bot_response = generate_response(
            msg.message,
            history=history,
            mood=msg.mood or "",
            lang=msg.lang or "en",
            user_memory=user_mem,
        )

    # Store this turn as training data (auto-scored)
    try:
        from learning import collect_training_sample
        collect_training_sample(
            db=db,
            user_message=msg.message,
            bot_response=bot_response,
            mood=msg.mood or "philosophical",
            rating=None,         # will be auto-scored or updated via /feedback
            session_id=msg.session_id,
            user_id=user_id,
        )
    except Exception as e:
        logger.warning(f"Training data collection failed: {e}")

    # Save conversation history
    history.append({"user": msg.message, "bot": bot_response})
    save_conversation(msg.session_id, history)

    return {"response": bot_response}
'''


# ─────────────────────────────────────────────
# MIGRATION SNIPPET
# Run this to add the new tables:
# ─────────────────────────────────────────────
MIGRATION_SNIPPET = """
# In backend/alembic/versions/add_training_tables.py

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('training_data',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_message', sa.Text(), nullable=False),
        sa.Column('bot_response', sa.Text(), nullable=False),
        sa.Column('mood', sa.String(), default='philosophical'),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('fingerprint', sa.String(), unique=True, nullable=True),
        sa.Column('is_exported', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )
    op.create_table('prompt_performance',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('variant_idx', sa.Integer(), unique=True),
        sa.Column('avg_score', sa.Float(), default=3.0),
        sa.Column('sample_count', sa.Integer(), default=0),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )
    op.create_table('model_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.String(), unique=True),
        sa.Column('model_id', sa.String(), unique=True),
        sa.Column('training_samples', sa.Integer(), default=0),
        sa.Column('eval_score', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )
    op.create_table('training_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.String(), unique=True),
        sa.Column('file_id', sa.String(), nullable=True),
        sa.Column('training_samples', sa.Integer(), default=0),
        sa.Column('status', sa.String(), default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table('response_feedback',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('training_data_id', sa.Integer(), sa.ForeignKey('training_data.id'), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('message_hash', sa.String(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('feedback_type', sa.String(), default='star'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )

def downgrade():
    for t in ['response_feedback','training_jobs','model_versions','prompt_performance','training_data']:
        op.drop_table(t)
"""

if __name__ == "__main__":
    print("Learning routes module. Import and paste LEARNING_ROUTES and UPDATED_CHAT_ROUTE into main.py")
    print("Run migration snippet to create new tables.")
