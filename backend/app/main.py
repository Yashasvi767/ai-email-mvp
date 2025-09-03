import os
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import datetime as dt

from . import database, models, processor, seed_emails, email_sender

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
SEED_ON_START = os.getenv("SEED_ON_START", "true").lower() in ("1", "true", "yes")

app = FastAPI(title="AI Email MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount static UI
app.mount("/static", StaticFiles(directory="static"), name="static")

# start up: create tables, optionally seed data
@app.on_event("startup")
def startup():
    database.init_db()
    if SEED_ON_START:
        seed_emails.seed_sample_emails()

@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse("static/index.html")

@app.get("/emails")
def list_emails(status: str | None = None):
    with database.get_session() as s:
        q = s.query(models.Email).join(models.EmailMeta, isouter=True)
        if status:
            q = q.filter(models.EmailMeta.status == status)
        rows = q.order_by(models.EmailMeta.urgency.desc().nullslast(), models.EmailMeta.priority.desc().nullslast(), models.Email.received_at.asc()).all()
        result = []
        for e in rows:
            m = e.meta
            result.append({
                "id": e.id,
                "sender": e.sender,
                "subject": e.subject,
                "body_text": e.body_text,
                "received_at": e.received_at.isoformat(),
                "sentiment": m.sentiment if m else None,
                "urgency": m.urgency if m else None,
                "priority": m.priority if m else None,
                "summary": m.summary if m else None,
                "contact_phone": m.contact_phone if m else None,
                "status": m.status if m else "pending",
            })
        return result

@app.get("/emails/{email_id}")
def get_email(email_id: str):
    with database.get_session() as s:
        e = s.query(models.Email).filter_by(id=email_id).first()
        if not e:
            raise HTTPException(404, "email not found")
        m = e.meta
        r = s.query(models.Response).filter_by(email_id=email_id).order_by(models.Response.created_at.desc()).first()
        draft = r.draft_text if r else None
        return {
            "id": e.id,
            "sender": e.sender,
            "subject": e.subject,
            "body_text": e.body_text,
            "received_at": e.received_at.isoformat(),
            "sentiment": m.sentiment if m else None,
            "urgency": m.urgency if m else None,
            "priority": m.priority if m else None,
            "summary": m.summary if m else None,
            "contact_phone": m.contact_phone if m else None,
            "ner_json": m.ner_json if m else None,
            "draft": draft,
            "status": m.status if m else "pending"
        }

@app.post("/emails/{email_id}/respond")
def send_response(email_id: str, payload: dict = Body(...)):
    final_text = payload.get("final_text")
    if final_text is None:
        raise HTTPException(400, "final_text required")
    with database.get_session() as s:
        e = s.query(models.Email).filter_by(id=email_id).first()
        if not e:
            raise HTTPException(404, "email not found")
        # create response record or update
        resp = models.Response(email_id=email_id, draft_text=final_text, final_text=final_text, sent_at=dt.datetime.utcnow())
        s.add(resp)
        # update meta status
        if e.meta:
            e.meta.status = "sent"
            e.meta.updated_at = dt.datetime.utcnow()
        s.commit()
        # stub send (does not actually send by default)
        try:
            email_sender.send_email_stub(e.sender, final_text)
        except Exception as ex:
            # keep it simple: log to file
            print("send stub error:", ex)
        return {"ok": True, "sent_at": resp.sent_at.isoformat()}

@app.get("/stats/24h")
def stats_24h():
    now = dt.datetime.utcnow()
    since = now - dt.timedelta(hours=24)
    with database.get_session() as s:
        total = s.query(models.Email).filter(models.Email.received_at >= since).count()
        meta = s.query(models.EmailMeta).join(models.Email).filter(models.Email.received_at >= since).all()
        resolved = sum(1 for m in meta if m.status == "sent" or m.status == "resolved")
        pending = total - resolved
        urgent = sum(1 for m in meta if m.urgency == "urgent")
        by_sentiment = {"positive": 0, "neutral": 0, "negative": 0}
        for m in meta:
            if m.sentiment in by_sentiment:
                by_sentiment[m.sentiment] += 1
        return {"total": total, "resolved": resolved, "pending": pending, "urgent": urgent, "by_sentiment": by_sentiment}
