"""
app/ai/services/room_recommender.py
----------------------------------------
Smart Room Recommendation.

Reuses the existing Room model directly (no separate dataset/training
step needed — the "training data" here IS the live, currently-available
room inventory). For each request we build a small feature matrix from
the currently available rooms, fit a fresh scikit-learn NearestNeighbors
index (k-NN — a genuine ML/content-based-filtering technique) against
the student's stated preferences, and return the closest matches.

Because the candidate set is small (a hostel's available rooms, not
millions of items) refitting per-request is cheap and always reflects
live occupancy — no stale recommendations.
"""

import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from app.models import Room, RoomStatusEnum, RoomTypeEnum

ROOM_TYPE_ORDER = [e.value for e in RoomTypeEnum]  # single, double, triple, dormitory


def _room_type_index(room_type: str) -> int:
    try:
        return ROOM_TYPE_ORDER.index(room_type)
    except ValueError:
        return len(ROOM_TYPE_ORDER)  # unknown type sorts last


def _build_feature_vector(monthly_rent: float, floor: int, room_type: str, available_beds: int) -> list:
    return [
        float(monthly_rent or 0),
        float(floor or 0),
        float(_room_type_index(room_type)),
        float(available_beds or 0),
    ]


def recommend_rooms(preferences: dict, top_n: int = 5) -> dict:
    """
    preferences: {
        "hostel_id": int | None,
        "room_type": "single"|"double"|"triple"|"dormitory" | None,
        "max_rent": float | None,
        "preferred_floor": int | None,
    }

    Returns: {"recommendations": [...], "candidates_considered": int}
    """
    query = Room.query.filter(
        Room.status != RoomStatusEnum.MAINTENANCE,
        Room.occupied_beds < Room.capacity,
    )

    hostel_id = preferences.get("hostel_id")
    if hostel_id:
        query = query.filter(Room.hostel_id == hostel_id)

    max_rent = preferences.get("max_rent")
    if max_rent:
        # Soft budget: keep a little headroom above the stated max so a
        # near-miss room can still be suggested and ranked lower, rather
        # than disappearing entirely.
        query = query.filter(Room.monthly_rent <= float(max_rent) * 1.15)

    candidate_rooms = query.all()
    if not candidate_rooms:
        return {"recommendations": [], "candidates_considered": 0}

    feature_matrix = np.array([
        _build_feature_vector(r.monthly_rent, r.floor, r.room_type.value if r.room_type else None, r.available_beds)
        for r in candidate_rooms
    ])

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(feature_matrix)

    preferred_room_type = preferences.get("room_type")
    query_vector = _build_feature_vector(
        monthly_rent=preferences.get("max_rent") or float(np.median(feature_matrix[:, 0])),
        floor=preferences.get("preferred_floor") or float(np.median(feature_matrix[:, 1])),
        room_type=preferred_room_type or ROOM_TYPE_ORDER[int(round(np.median(feature_matrix[:, 2])))],
        available_beds=float(np.max(feature_matrix[:, 3])) if feature_matrix.size else 1,
    )
    scaled_query = scaler.transform([query_vector])

    n_neighbors = min(top_n, len(candidate_rooms))
    knn = NearestNeighbors(n_neighbors=n_neighbors, metric="euclidean")
    knn.fit(scaled_features)

    distances, indices = knn.kneighbors(scaled_query)

    max_distance = float(np.max(distances)) if distances.size else 1.0
    recommendations = []
    for rank, (idx, dist) in enumerate(zip(indices[0], distances[0]), start=1):
        room = candidate_rooms[idx]
        # Convert distance to an intuitive 0-100 "match score" (closer = higher).
        match_score = round(100 * (1 - (dist / max_distance)) if max_distance > 0 else 100, 1)
        match_score = max(match_score, 5.0)  # never show a 0% match for a returned suggestion

        room_dict = room.to_dict()
        room_dict["match_score"] = match_score
        room_dict["match_rank"] = rank
        recommendations.append(room_dict)

    recommendations.sort(key=lambda r: r["match_score"], reverse=True)

    return {"recommendations": recommendations, "candidates_considered": len(candidate_rooms)}
