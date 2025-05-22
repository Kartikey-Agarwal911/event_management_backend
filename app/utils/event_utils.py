from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY, YEARLY, MO, TU, WE, TH, FR, SA, SU
from sqlalchemy.orm import Session
from ..models import Event, EventConflict, RecurrenceFrequency, RecurrenceEndType


def ensure_timezone_aware(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware, defaulting to UTC if naive."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def generate_recurring_instances(
    start_time: datetime,
    end_time: datetime,
    frequency: RecurrenceFrequency,
    interval: int = 1,
    days: Optional[List[str]] = None,
    end_type: Optional[RecurrenceEndType] = None,
    end_count: Optional[int] = None,
    end_date: Optional[datetime] = None,
    exceptions: Optional[List[datetime]] = None
) -> List[Dict[str, datetime]]:
    """
    Generate all instances of a recurring event based on the recurrence parameters.
    Returns a list of dictionaries containing start_time and end_time for each instance.
    """
    # Ensure timezone-aware datetimes
    start_time = ensure_timezone_aware(start_time)
    end_time = ensure_timezone_aware(end_time)
    if end_date:
        end_date = ensure_timezone_aware(end_date)
    if exceptions:
        exceptions = [ensure_timezone_aware(dt) for dt in exceptions]
    
    duration = end_time - start_time
    
    # Convert frequency to dateutil constants
    freq_map = {
        RecurrenceFrequency.DAILY: DAILY,
        RecurrenceFrequency.WEEKLY: WEEKLY,
        RecurrenceFrequency.MONTHLY: MONTHLY,
        RecurrenceFrequency.YEARLY: YEARLY
    }
    
    # Convert weekday strings to dateutil weekday objects
    weekday_map = {
        'monday': MO,
        'tuesday': TU,
        'wednesday': WE,
        'thursday': TH,
        'friday': FR,
        'saturday': SA,
        'sunday': SU
    }
    
    # Set up rrule parameters
    rrule_params = {
        'dtstart': start_time,
        'freq': freq_map[frequency],
        'interval': interval
    }
    
    # Add end conditions
    if end_type == RecurrenceEndType.COUNT:
        rrule_params['count'] = end_count
    elif end_type == RecurrenceEndType.UNTIL:
        rrule_params['until'] = end_date
    
    # Add weekly recurrence days if specified
    if frequency == RecurrenceFrequency.WEEKLY and days:
        rrule_params['byweekday'] = [weekday_map[day.lower()] for day in days]
    
    # Generate instances
    instances = []
    for dt in rrule(**rrule_params):
        instance_end = dt + duration
        instances.append({
            'start_time': dt,
            'end_time': instance_end
        })
    
    # Remove exceptions
    if exceptions:
        instances = [
            inst for inst in instances
            if inst['start_time'] not in exceptions
        ]
    
    return instances


def check_event_conflicts(
    db: Session,
    event: Event,
    start_time: datetime,
    end_time: datetime,
    exclude_event_id: Optional[int] = None
) -> List[Event]:
    """
    Check for conflicts with existing events.
    Returns a list of conflicting events.
    """
    # Ensure timezone-aware datetimes
    start_time = ensure_timezone_aware(start_time)
    end_time = ensure_timezone_aware(end_time)
    
    # Base query for potential conflicts
    query = db.query(Event).filter(
        Event.start_time < end_time,
        Event.end_time > start_time
    )
    
    # Exclude the current event if updating
    if exclude_event_id:
        query = query.filter(Event.id != exclude_event_id)
    
    # Get all potential conflicts
    potential_conflicts = query.all()
    conflicts = []
    
    for potential_conflict in potential_conflicts:
        if potential_conflict.is_recurring:
            # Check recurring event instances
            instances = generate_recurring_instances(
                potential_conflict.start_time,
                potential_conflict.end_time,
                potential_conflict.recurrence_frequency,
                potential_conflict.recurrence_interval,
                potential_conflict.recurrence_days,
                potential_conflict.recurrence_end_type,
                potential_conflict.recurrence_end_count,
                potential_conflict.recurrence_end_date,
                potential_conflict.recurrence_exceptions
            )
            for instance in instances:
                if (instance['start_time'] < end_time and
                    instance['end_time'] > start_time):
                    conflicts.append(potential_conflict)
                    break
        else:
            # Non-recurring event, already confirmed conflict
            conflicts.append(potential_conflict)
    
    return conflicts


def create_conflict_record(db: Session, event_id: int, conflicting_event_ids: List[int], user_id: int) -> None:
    """Create conflict records for an event."""
    for conflict_id in conflicting_event_ids:
        conflict = EventConflict(
            event_id=event_id,
            conflicting_event_id=conflict_id,
            conflict_type=1,  # Assuming 1 is the default conflict type
            resolution=None,
            created_at=datetime.utcnow()
        )
        db.add(conflict)
    db.commit()


def resolve_conflict(
    db: Session,
    conflict_id: int,
    resolution: str
) -> EventConflict:
    """
    Resolve an event conflict with the specified resolution.
    """
    conflict = db.query(EventConflict).filter(
        EventConflict.id == conflict_id
    ).first()
    
    if conflict:
        conflict.resolution = resolution
        conflict.resolved_at = datetime.utcnow()
        db.commit()
        db.refresh(conflict)
    
    return conflict 