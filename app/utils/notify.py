"""
app/utils/notify.py
----------------------
Thin service layer over the Notification model. Other modules
(complaints, fees, room allocation, maintenance, visitors...) call
`notify_user` or `notify_role` to raise in-app notifications instead of
constructing Notification rows directly.
"""

from app.extensions import db
from app.models import Notification, NotificationTypeEnum


def notify_user(user_id: int, title: str, message: str, notif_type: str = NotificationTypeEnum.INFO.value) -> Notification:
    notification = Notification(
        user_id=user_id,
        target_role=None,
        title=title,
        message=message,
        notif_type=notif_type,
    )
    db.session.add(notification)
    return notification


def notify_role(role: str, title: str, message: str, notif_type: str = NotificationTypeEnum.INFO.value) -> Notification:
    """Broadcast a notification to every user with the given role."""
    notification = Notification(
        user_id=None,
        target_role=role,
        title=title,
        message=message,
        notif_type=notif_type,
    )
    db.session.add(notification)
    return notification
