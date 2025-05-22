from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, auth
from ..database import get_db
from datetime import datetime
import json
from ..utils.event_utils import check_event_conflicts, create_conflict_record, generate_recurring_instances, resolve_conflict
from ..utils.websocket_manager import manager


def serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


router = APIRouter()


@router.post("/", response_model=schemas.Event)
async def create_event(event: schemas.EventCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    conflicts = check_event_conflicts(db, event, event.start_time, event.end_time)
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event conflicts with existing events"
        )
    db_event = models.Event(**event.dict(), owner_id=current_user.id)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    if conflicts:
        create_conflict_record(db, db_event.id, [c.id for c in conflicts], current_user.id)
    
    # Send notification
    await manager.notify_event_created(current_user.id, {
        "id": db_event.id,
        "title": db_event.title,
        "description": db_event.description,
        "start_time": db_event.start_time.isoformat(),
        "end_time": db_event.end_time.isoformat(),
        "location": db_event.location
    })
    
    return db_event


@router.get("/", response_model=List[schemas.Event])
def read_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    events = db.query(models.Event).filter(models.Event.owner_id == current_user.id).offset(skip).limit(limit).all()
    return events


@router.get("/{event_id}", response_model=schemas.Event)
def read_event(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this event")
    return db_event


@router.put("/{event_id}", response_model=schemas.Event)
async def update_event(event_id: int, event: schemas.EventCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this event")
    
    # Check for conflicts
    conflicts = check_event_conflicts(db, event, event.start_time, event.end_time, exclude_event_id=event_id)
    if conflicts:
        # Create conflict records
        for conflict in conflicts:
            create_conflict_record(
                db,
                event_id,
                conflict.id,
                "OVERLAP"
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event conflicts with existing events"
        )
    
    # Get the current version before updating
    current_version = db.query(models.EventVersion).filter(models.EventVersion.event_id == event_id).order_by(models.EventVersion.version_number.desc()).first()
    
    # Update the event
    for key, value in event.dict().items():
        setattr(db_event, key, value)
    db.commit()
    db.refresh(db_event)
    
    # Create new version
    new_version_number = 1 if current_version is None else current_version.version_number + 1
    event_data = event.dict()
    # Convert datetime objects to ISO format strings
    event_data['start_time'] = event_data['start_time'].isoformat()
    event_data['end_time'] = event_data['end_time'].isoformat()
    
    db_version = models.EventVersion(
        event_id=event_id,
        version_number=new_version_number,
        data=event_data,
        changed_by=current_user.id
    )
    db.add(db_version)
    db.commit()
    
    # Create changelog entry if there was a previous version
    if current_version is not None:
        # Calculate diff
        diff = {
            "type": "UPDATE",
            "changes": {
                field: {
                    "old": current_version.data.get(field),
                    "new": event_data.get(field)
                }
                for field in set(current_version.data.keys()) | set(event_data.keys())
                if current_version.data.get(field) != event_data.get(field)
            }
        }
        
        # Create changelog entry
        db_changelog = models.Changelog(
            event_id=event_id,
            version_from=current_version.version_number,
            version_to=new_version_number,
            diff=diff
        )
        db.add(db_changelog)
        db.commit()
    
    return db_event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this event")
    db.delete(db_event)
    db.commit()
    return None


@router.post("/batch", response_model=List[schemas.Event])
def create_events(events: List[schemas.EventCreate], db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_events = []
    for event in events:
        db_event = models.Event(**event.dict(), owner_id=current_user.id)
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        db_events.append(db_event)
        # Create initial version
        event_data = event.dict()
        # Convert datetime objects to ISO format strings
        event_data['start_time'] = event_data['start_time'].isoformat()
        event_data['end_time'] = event_data['end_time'].isoformat()
        db_version = models.EventVersion(
            event_id=db_event.id,
            version_number=1,
            data=event_data,
            changed_by=current_user.id
        )
        db.add(db_version)
        db.commit()
    return db_events


@router.post("/{event_id}/share", response_model=schemas.EventPermission)
async def share_event(event_id: int, permission: schemas.EventPermissionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to share this event")
    
    db_permission = models.EventPermission(**permission.dict(), event_id=event_id)
    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)
    
    # Send notification
    await manager.notify_event_shared(current_user.id, event_id)
    
    return db_permission


@router.get("/{event_id}/permissions", response_model=List[schemas.EventPermission])
def read_permissions(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view permissions")
    permissions = db.query(models.EventPermission).filter(models.EventPermission.event_id == event_id).all()
    return permissions


@router.put("/{event_id}/permissions/{user_id}", response_model=schemas.EventPermission)
def update_permission(event_id: int, user_id: int, permission: schemas.EventPermissionBase, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update permissions")
    db_permission = db.query(models.EventPermission).filter(models.EventPermission.event_id == event_id, models.EventPermission.user_id == user_id).first()
    if db_permission is None:
        raise HTTPException(status_code=404, detail="Permission not found")
    for key, value in permission.dict().items():
        setattr(db_permission, key, value)
    db.commit()
    db.refresh(db_permission)
    return db_permission


@router.delete("/{event_id}/permissions/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(event_id: int, user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete permissions")
    db_permission = db.query(models.EventPermission).filter(models.EventPermission.event_id == event_id, models.EventPermission.user_id == user_id).first()
    if db_permission is None:
        raise HTTPException(status_code=404, detail="Permission not found")
    db.delete(db_permission)
    db.commit()
    return None


@router.get("/{event_id}/history/{version_id}", response_model=schemas.EventVersion)
def read_version(event_id: int, version_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view version history")
    db_version = db.query(models.EventVersion).filter(models.EventVersion.event_id == event_id, models.EventVersion.version_number == version_id).first()
    if db_version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return db_version


@router.post("/{event_id}/rollback/{version_id}", response_model=schemas.Event)
def rollback_version(event_id: int, version_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to rollback")
    db_version = db.query(models.EventVersion).filter(models.EventVersion.event_id == event_id, models.EventVersion.version_number == version_id).first()
    if db_version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    for key, value in db_version.data.items():
        setattr(db_event, key, value)
    db.commit()
    db.refresh(db_event)
    # Create new version
    latest_version = db.query(models.EventVersion).filter(models.EventVersion.event_id == event_id).order_by(models.EventVersion.version_number.desc()).first()
    new_version_number = latest_version.version_number + 1
    db_new_version = models.EventVersion(
        event_id=event_id,
        version_number=new_version_number,
        data=db_version.data,
        changed_by=current_user.id
    )
    db.add(db_new_version)
    db.commit()
    return db_event


@router.get("/{event_id}/changelog", response_model=List[schemas.Changelog])
def read_changelog(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view changelog")
    changelog = db.query(models.Changelog).filter(models.Changelog.event_id == event_id).all()
    return changelog


@router.get("/{event_id}/diff/{version_id1}/{version_id2}", response_model=schemas.Changelog)
def read_diff(event_id: int, version_id1: int, version_id2: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view diff")
    db_version1 = db.query(models.EventVersion).filter(models.EventVersion.event_id == event_id, models.EventVersion.version_number == version_id1).first()
    if db_version1 is None:
        raise HTTPException(status_code=404, detail="Version 1 not found")
    db_version2 = db.query(models.EventVersion).filter(models.EventVersion.event_id == event_id, models.EventVersion.version_number == version_id2).first()
    if db_version2 is None:
        raise HTTPException(status_code=404, detail="Version 2 not found")
    # Calculate diff
    diff = {}
    for key in db_version1.data:
        if key in db_version2.data:
            if db_version1.data[key] != db_version2.data[key]:
                diff[key] = {"from": db_version1.data[key], "to": db_version2.data[key]}
    db_changelog = models.Changelog(
        event_id=event_id,
        version_from=version_id1,
        version_to=version_id2,
        diff=diff
    )
    db.add(db_changelog)
    db.commit()
    db.refresh(db_changelog)
    return db_changelog


@router.get("/{event_id}/versions", response_model=List[schemas.EventVersion])
def get_event_versions(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    versions = db.query(models.EventVersion).filter(models.EventVersion.event_id == event_id).order_by(models.EventVersion.version_number).all()
    return versions


@router.get("/{event_id}/conflicts", response_model=List[schemas.EventConflict])
def get_event_conflicts(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    conflicts = db.query(models.EventConflict).filter(models.EventConflict.event_id == event_id).all()
    return conflicts


@router.post("/{event_id}/conflicts/{conflict_id}/resolve", response_model=schemas.EventConflict)
def resolve_event_conflict(event_id: int, conflict_id: int, resolution: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to resolve conflicts for this event")
    
    conflict = db.query(models.EventConflict).filter(
        models.EventConflict.id == conflict_id,
        models.EventConflict.event_id == event_id
    ).first()
    
    if conflict is None:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    if conflict.resolution is not None:
        raise HTTPException(status_code=400, detail="Conflict already resolved")
    
    # Update the conflict record
    conflict.resolution = resolution
    conflict.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(conflict)
    
    # If resolution is "reschedule", we should update the event times
    if resolution == "reschedule":
        # Get the conflicting event
        conflicting_event = db.query(models.Event).filter(models.Event.id == conflict.conflicting_event_id).first()
        if conflicting_event:
            # Move the current event to start after the conflicting event
            db_event.start_time = conflicting_event.end_time
            db_event.end_time = datetime.fromtimestamp(
                conflicting_event.end_time.timestamp() + 
                (db_event.end_time.timestamp() - db_event.start_time.timestamp())
            )
            db.commit()
            db.refresh(db_event)
    
    return conflict 