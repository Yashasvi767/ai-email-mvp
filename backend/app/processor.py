import re
import datetime as dt
from . import database, models

URGENCY_KWS = [
    'immediately','urgent','critical','down','cannot access','payment failed',
    'security','data loss','refund','deadline today','escalate'
]
NEG_WORDS = ['not', "can't", 'cannot', 'failed', 'error', 'frustrat', 'angry', 'disappointed', 'issue', 'problem']

PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-\s]?)?(?:\d{10,12})")

def sentiment_simple(text: str):
    t = text.lower()
    neg = sum(1 for w in NEG_WORDS if w in t)
    if neg >= 2:
        return "negative", -1
    if neg == 1:
        return "neutral", 0
    return "positive", 1

def urgency_score(text: str):
    t = text.lower()
    matched = [kw for kw in URGENCY_KWS if kw in t]
    score = min(40, 10 * len(matched))
    urgency = "urgent" if score >= 20 else "not_urgent"
    return score, urgency, matched

def extract_entities(text: str):
    phones = PHONE_RE.findall(text)
    return {"phones": phones, "emails": re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", text)}

def build_summary(text: str, max_len=200):
    # naive: first 200 chars of the main body trimmed
    s = " ".join(text.split())
    return (s[:max_len] + "...") if len(s) > max_len else s

def draft_reply_template(sender_name: str, product_refs: list | None, summary: str, sentiment: str):
    empath = ""
    if sentiment == "negative":
        empath = "I'm sorry you're facing this — I know it's frustrating.\n\n"
    product_line = f"We checked {', '.join(product_refs)}. " if product_refs else ""
    steps = "Could you please confirm the following so I can help: 1) Your account email, 2) A brief screenshot or error ID if available?"
    return (
        f"Hi {sender_name or 'there'},\n\n"
        f"{empath}"
        f"Thanks for reaching out about this. {product_line}Here's a quick summary of your request:\n\n{summary}\n\n"
        f"{steps}\n\n"
        f"If you'd like faster assistance, reply with 'ESCALATE'.\n\nBest,\nSupport Team"
    )

def process_and_draft(email_record):
    # email_record is models.Email instance
    with database.get_session() as s:
        # compute sentiment, urgency, extract entities
        sentiment_label, sent_score = sentiment_simple(email_record.body_text or "")
        kw_score, urgency_label, matched = urgency_score(email_record.subject + " " + (email_record.body_text or ""))
        age_hours = max(0, (dt.datetime.utcnow() - (email_record.received_at or dt.datetime.utcnow())).total_seconds()/3600)
        age_boost = int(min(10, age_hours // 1))
        priority = 10 + kw_score + (10 if sentiment_label=="negative" else 0) + age_boost
        ner = extract_entities(email_record.body_text or "")
        summary = build_summary(email_record.body_text or "")
        product_refs = []  # placeholder: simple detection could be added
        # upsert meta
        meta = s.query(models.EmailMeta).filter_by(email_id=email_record.id).first()
        if not meta:
            meta = models.EmailMeta(email_id=email_record.id)
        meta.sentiment = sentiment_label
        meta.urgency = urgency_label
        meta.priority = priority
        meta.keywords = matched
        meta.contact_phone = ner["phones"][0] if ner["phones"] else None
        meta.contact_alt = ner["emails"][0] if ner["emails"] else None
        meta.product_refs = product_refs
        meta.summary = summary
        meta.ner_json = ner
        meta.status = "drafted"
        meta.updated_at = dt.datetime.utcnow()
        s.add(meta)
        # draft reply
        sender_name = email_record.sender.split("@")[0]
        draft = draft_reply_template(sender_name, product_refs, summary, sentiment_label)
        resp = models.Response(email_id=email_record.id, draft_text=draft)
        s.add(resp)
        s.commit()
        return {"draft": draft, "meta": {"sentiment": sentiment_label, "urgency": urgency_label, "priority": priority}}
