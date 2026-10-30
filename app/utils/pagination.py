"""
app/utils/pagination.py
--------------------------
Generic pagination helper shared by every list endpoint across all
modules (students, rooms, fees, complaints, etc.) so pagination behaves
identically everywhere.
"""

from flask import request


def get_pagination_params(default_per_page: int = 10, max_per_page: int = 100):
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except (TypeError, ValueError):
        page = 1

    try:
        per_page = int(request.args.get("per_page", default_per_page))
    except (TypeError, ValueError):
        per_page = default_per_page

    per_page = max(1, min(per_page, max_per_page))
    return page, per_page


def paginate_query(query, serializer=None, default_per_page: int = 10, max_per_page: int = 100):
    """
    Paginate a SQLAlchemy query and return a JSON-ready dict:
        {
            "items": [...],
            "pagination": {
                "page": 1, "per_page": 10, "total_items": 42, "total_pages": 5,
                "has_next": true, "has_prev": false
            }
        }
    `serializer` defaults to calling `.to_dict()` on each item.
    """
    page, per_page = get_pagination_params(default_per_page, max_per_page)

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    serializer = serializer or (lambda item: item.to_dict())

    return {
        "items": [serializer(item) for item in paginated.items],
        "pagination": {
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total_items": paginated.total,
            "total_pages": paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        },
    }
