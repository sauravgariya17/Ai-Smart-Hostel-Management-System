"""
app/rooms/services.py
------------------------
Business logic for allocating, vacating, and transferring students
between rooms. Kept separate from routes.py so the same logic can be
reused by both the direct-allocation endpoint and the transfer-approval
endpoint without duplication.
"""

from datetime import datetime

from app.extensions import db
from app.models import Room, RoomAllocation, AllocationStatusEnum, RoomStatusEnum
from app.utils.notify import notify_user


class RoomAllocationError(Exception):
    """Raised when a requested room allocation cannot be performed."""


def get_active_allocation(student_id: int):
    return RoomAllocation.query.filter_by(student_id=student_id, status=AllocationStatusEnum.ACTIVE).first()


def allocate_room(student, room: Room, allocated_by_user_id: int, remarks: str = None) -> RoomAllocation:
    if room.status == RoomStatusEnum.MAINTENANCE:
        raise RoomAllocationError("This room is under maintenance and cannot be allocated.")

    if room.available_beds <= 0:
        raise RoomAllocationError("This room has no available beds.")

    existing = get_active_allocation(student.id)
    if existing:
        raise RoomAllocationError("Student already has an active room allocation. Vacate or transfer first.")

    allocation = RoomAllocation(
        student_id=student.id,
        room_id=room.id,
        allocated_date=datetime.utcnow().date(),
        status=AllocationStatusEnum.ACTIVE,
        allocated_by=allocated_by_user_id,
        remarks=remarks,
    )
    room.occupied_beds += 1
    room.refresh_status()

    db.session.add(allocation)

    notify_user(
        user_id=student.user_id,
        title="Room Allocated",
        message=f"You have been allocated Room {room.room_number}.",
        notif_type="success",
    )

    return allocation


def vacate_room(allocation: RoomAllocation, remarks: str = None) -> RoomAllocation:
    if allocation.status != AllocationStatusEnum.ACTIVE:
        raise RoomAllocationError("This allocation is not active.")

    room = allocation.room
    allocation.status = AllocationStatusEnum.VACATED
    allocation.vacated_date = datetime.utcnow().date()
    if remarks:
        allocation.remarks = remarks

    room.occupied_beds = max(room.occupied_beds - 1, 0)
    room.refresh_status()

    notify_user(
        user_id=allocation.student.user_id,
        title="Room Vacated",
        message=f"Your allocation for Room {room.room_number} has been closed.",
        notif_type="info",
    )

    return allocation


def transfer_room(allocation: RoomAllocation, new_room: Room, processed_by_user_id: int, remarks: str = None) -> RoomAllocation:
    """Vacate the student's current room and allocate them into `new_room`."""
    if new_room.status == RoomStatusEnum.MAINTENANCE:
        raise RoomAllocationError("The requested room is under maintenance.")
    if new_room.available_beds <= 0:
        raise RoomAllocationError("The requested room has no available beds.")

    student = allocation.student
    vacate_room(allocation, remarks="Vacated for room transfer.")

    new_allocation = allocate_room(student, new_room, processed_by_user_id, remarks=remarks or "Transferred room.")
    return new_allocation
