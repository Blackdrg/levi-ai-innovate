import logging
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from backend.services.compliance import export_audit_logs_csv
from backend.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/compliance", tags=["Sovereign Compliance"])

@router.get("/export")
async def get_audit_export(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns a HIPAA/GDPR-ready audit export in CSV format.
    """
    user_id = current_user.get("uid") or current_user.get("user_id")
    
    try:
        csv_data = await export_audit_logs_csv(user_id, days)
        
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="sovereign_audit_export_{user_id}_{days}d.csv"'
            }
        )
    except Exception as e:
        logger.error(f"[Compliance] Export failure: {e}")
        raise HTTPException(status_code=500, detail="Failed to synthesize audit artifact.")

@router.delete("/data/{user_id}")
async def delete_user_data(
    user_id: str,
    hard_delete: bool = Query(True),
    current_user: dict = Depends(get_current_user)
):
    """
    Sovereign v14.1.0: Permanent Data Scrubbing.
    Triggers physical erasure of all user-linked cognitive trails.
    """
    # Security: Ensure user can only delete their own data unless they are an admin
    requesting_uid = current_user.get("uid") or current_user.get("user_id")
    if requesting_uid != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: You can only purge your own data.")

    from backend.services.compliance import hard_delete_user_data
    success = await hard_delete_user_data(user_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Data erasure failed. Manual intervention logged.")
        
    return {"status": "success", "message": f"Data for {user_id} has been physically scrubbed."}
