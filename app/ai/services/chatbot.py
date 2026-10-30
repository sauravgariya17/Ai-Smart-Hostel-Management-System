"""
app/ai/services/chatbot.py
--------------------------------
AI Hostel Assistant / FAQ Chatbot.

A lightweight retrieval-based chatbot: a small FAQ knowledge base of
(example questions -> intent) is vectorized once with TF-IDF at import
time (no training script / persisted model needed — the corpus is tiny
and static, so fitting it in-process on startup is instant). An incoming
question is vectorized with the same fitted vectorizer and matched to
the closest intent via cosine similarity.

Some intents are purely static text (hostel policy FAQs); others are
"dynamic" and pull live data through the existing models (Student, Room
allocation, StudentFee, Complaint) so the assistant can answer
personal questions like "what is my room number" using the same
services/models the rest of the app already relies on.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models import Student, StudentFee, Complaint, ComplaintStatusEnum
from app.rooms.services import get_active_allocation

SIMILARITY_THRESHOLD = 0.25

# ======================================================================
# FAQ knowledge base
# ======================================================================
# Each entry: intent name, a handful of example phrasings (used to fit
# the TF-IDF matcher), and either a static `answer` or a `handler`
# function name (resolved dynamically against the current user).

_FAQ_INTENTS = [
    {
        "intent": "my_room",
        "examples": [
            "what is my room number", "which room am i in", "my room details",
            "what room do i have", "tell me my room",
        ],
        "handler": "handle_my_room",
    },
    {
        "intent": "my_fee_due",
        "examples": [
            "how much fee do i owe", "what is my pending fee", "my fee balance",
            "how much do i need to pay", "outstanding fee amount", "fee due",
        ],
        "handler": "handle_my_fee_due",
    },
    {
        "intent": "my_complaints",
        "examples": [
            "status of my complaints", "how many open complaints do i have",
            "my complaint status", "did my complaint get resolved",
        ],
        "handler": "handle_my_complaints",
    },
    {
        "intent": "raise_complaint",
        "examples": [
            "how do i raise a complaint", "how to file a complaint",
            "where can i report an issue", "how to complain about my room",
        ],
        "answer": (
            "Go to the Complaints page from the sidebar and click 'Submit Complaint'. "
            "Fill in a title, category, and description — our AI will even suggest a "
            "category and priority for you, which you can review before submitting."
        ),
    },
    {
        "intent": "room_transfer",
        "examples": [
            "how do i request a room transfer", "can i change my room",
            "how to switch rooms", "request different room",
        ],
        "answer": (
            "Go to the Rooms page, check the Availability list for open rooms, and use "
            "the 'Request a Room Transfer' form with the room ID you'd like. An admin or "
            "warden will review and approve or reject your request."
        ),
    },
    {
        "intent": "visiting_hours",
        "examples": [
            "what are the visiting hours", "when can visitors come",
            "visitor timing", "guest hours",
        ],
        "answer": (
            "Visitors are generally welcome between 10:00 AM and 7:00 PM. Please check in "
            "with the warden at the gate — every visit is logged in the Visitor Management system."
        ),
    },
    {
        "intent": "attendance_policy",
        "examples": [
            "what is the attendance policy", "how is attendance marked",
            "do i need to mark my own attendance",
        ],
        "answer": (
            "Attendance is marked daily by the warden, not by students. You can check your "
            "own attendance history any time from the Attendance page."
        ),
    },
    {
        "intent": "wifi",
        "examples": [
            "what is the wifi password", "how do i connect to hostel wifi", "internet access",
        ],
        "answer": (
            "Wi-Fi credentials are provided by your warden at check-in. If you're having "
            "connectivity issues, please raise a complaint under the 'Internet' category."
        ),
    },
    {
        "intent": "mess_timing",
        "examples": [
            "what are the mess timings", "when is breakfast lunch dinner served", "food timing",
        ],
        "answer": (
            "Typical mess timings are: Breakfast 7:30-9:30 AM, Lunch 12:30-2:30 PM, "
            "Dinner 7:30-9:30 PM. Exact timings may vary by hostel — check your hostel's notice board."
        ),
    },
    {
        "intent": "payment_methods",
        "examples": [
            "how can i pay my fees", "what payment methods are accepted", "how to pay hostel fee",
        ],
        "answer": (
            "Fees can be paid via cash, card, UPI, bank transfer, or cheque. Payments are "
            "recorded by the admin/warden and instantly reflected in your Fee & Payments page."
        ),
    },
    {
        "intent": "greeting",
        "examples": ["hi", "hello", "hey there", "good morning"],
        "answer": "Hello! I'm your Hostel Assistant. Ask me about your room, fees, complaints, or hostel policies.",
    },
]


def _handle_my_room(user_id: int) -> str:
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return "I couldn't find a student profile linked to your account."

    allocation = get_active_allocation(student.id)
    if not allocation:
        return "You don't currently have a room allocated. Please contact the hostel admin."

    room = allocation.room
    return (
        f"You're currently allocated Room {room.room_number}"
        f"{f' in {room.hostel.name}' if room.hostel else ''}, "
        f"a {room.room_type.value} room on floor {room.floor}."
    )


def _handle_my_fee_due(user_id: int) -> str:
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return "I couldn't find a student profile linked to your account."

    invoices = StudentFee.query.filter_by(student_id=student.id).all()
    if not invoices:
        return "You don't have any fee invoices on record right now."

    total_due = sum(i.balance for i in invoices if i.balance > 0)
    if total_due <= 0:
        return "Great news — you have no outstanding fee balance right now."
    return f"You currently have an outstanding fee balance of ₹{total_due:.2f}. Check the Fees page for a full breakdown."


def _handle_my_complaints(user_id: int) -> str:
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return "I couldn't find a student profile linked to your account."

    complaints = Complaint.query.filter_by(student_id=student.id).all()
    if not complaints:
        return "You haven't raised any complaints yet."

    open_count = sum(1 for c in complaints if c.status in (ComplaintStatusEnum.OPEN, ComplaintStatusEnum.IN_PROGRESS))
    resolved_count = sum(1 for c in complaints if c.status == ComplaintStatusEnum.RESOLVED)
    return f"You have {len(complaints)} complaint(s) total: {open_count} open/in-progress, {resolved_count} resolved."


_HANDLERS = {
    "handle_my_room": _handle_my_room,
    "handle_my_fee_due": _handle_my_fee_due,
    "handle_my_complaints": _handle_my_complaints,
}


class _ChatbotMatcher:
    """Fits the TF-IDF vectorizer once (lazily, on first use) over every
    example phrase across all intents, then matches new questions
    against that fitted space via cosine similarity."""

    def __init__(self):
        self._vectorizer = None
        self._example_vectors = None
        self._example_to_intent = []

    def _ensure_fitted(self):
        if self._vectorizer is not None:
            return

        all_examples = []
        for entry in _FAQ_INTENTS:
            for example in entry["examples"]:
                all_examples.append(example)
                self._example_to_intent.append(entry)

        self._vectorizer = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2))
        self._example_vectors = self._vectorizer.fit_transform(all_examples)

    def match(self, question: str):
        self._ensure_fitted()
        query_vector = self._vectorizer.transform([question])
        similarities = cosine_similarity(query_vector, self._example_vectors)[0]

        best_idx = int(similarities.argmax())
        best_score = float(similarities[best_idx])
        matched_entry = self._example_to_intent[best_idx]

        return matched_entry, best_score


_matcher = _ChatbotMatcher()


def ask(question: str, user_id: int = None) -> dict:
    """
    Returns:
        {
            "answer": "...",
            "matched_intent": "my_room" | None,
            "confidence": 0.71,
        }
    """
    question = (question or "").strip()
    if not question:
        return {
            "answer": "Please type a question and I'll do my best to help!",
            "matched_intent": None,
            "confidence": 0.0,
        }

    entry, score = _matcher.match(question)

    if score < SIMILARITY_THRESHOLD:
        return {
            "answer": (
                "I'm not confident I understood that. Try asking about your room, fees, "
                "complaints, visiting hours, mess timings, or how to raise a complaint. "
                "For anything else, please contact the hostel office."
            ),
            "matched_intent": None,
            "confidence": round(score, 3),
        }

    if "handler" in entry:
        handler_fn = _HANDLERS.get(entry["handler"])
        if handler_fn and user_id is not None:
            answer = handler_fn(user_id)
        else:
            answer = "Please log in to ask personal questions like this one."
    else:
        answer = entry["answer"]

    return {"answer": answer, "matched_intent": entry["intent"], "confidence": round(score, 3)}
