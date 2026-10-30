"""
app/utils/query_helpers.py
------------------------------
Generic, reusable query-building helpers for search, filtering, and
sorting. Every "list" endpoint across the system (students, rooms,
fees, complaints, visitors, attendance, maintenance...) composes these
instead of hand-rolling ad-hoc query logic.
"""

from flask import request
from sqlalchemy import or_, asc, desc


def apply_search(query, model, search_fields: list[str]):
    """
    Apply a case-insensitive partial match across `search_fields` using
    the `?search=` query parameter. `search_fields` are attribute names
    on `model` (e.g. ["name", "email"]).
    """
    search_term = request.args.get("search", "").strip()
    if not search_term:
        return query

    conditions = []
    for field_name in search_fields:
        column = getattr(model, field_name, None)
        if column is not None:
            conditions.append(column.ilike(f"%{search_term}%"))

    if conditions:
        query = query.filter(or_(*conditions))
    return query


def apply_filters(query, model, filterable_fields: list[str]):
    """
    Apply exact-match filters for any of `filterable_fields` present in
    the request's query string, e.g. ?status=open&priority=high
    """
    for field_name in filterable_fields:
        value = request.args.get(field_name)
        if value not in (None, "", "all"):
            column = getattr(model, field_name, None)
            if column is not None:
                query = query.filter(column == value)
    return query


def apply_sort(query, model, allowed_sort_fields: list[str], default_field: str = "id", default_dir: str = "desc"):
    """
    Apply sorting via ?sort_by=<field>&sort_dir=<asc|desc>, restricted
    to `allowed_sort_fields` to prevent arbitrary column injection.
    """
    sort_by = request.args.get("sort_by", default_field)
    sort_dir = request.args.get("sort_dir", default_dir).lower()

    if sort_by not in allowed_sort_fields:
        sort_by = default_field

    column = getattr(model, sort_by, None)
    if column is None:
        return query

    return query.order_by(desc(column) if sort_dir == "desc" else asc(column))


def apply_date_range(query, model, date_field: str, start_param: str = "start_date", end_param: str = "end_date"):
    """Apply an inclusive date-range filter using ?start_date=&end_date= (YYYY-MM-DD)."""
    column = getattr(model, date_field, None)
    if column is None:
        return query

    start_value = request.args.get(start_param)
    end_value = request.args.get(end_param)

    if start_value:
        query = query.filter(column >= start_value)
    if end_value:
        query = query.filter(column <= end_value)
    return query
