import uuid, datetime as dt
from . import database, models, processor

SAMPLES = [
    {
        "sender": "alice@example.com",
        "subject": "Support: Cannot access my account - urgent",
        "body_text": "Hi, I cannot access my account since yesterday. It says ERROR 403. Please help immediately. My phone +919876543210."
    },
    {
        "sender": "bob@example.com",
        "subject": "Request: Refund for order #12345",
        "body_text": "Hello, I'd like a refund for order 12345. The payment failed but money deducted. disappointed."
    },
    {
        "sender": "carol@example.com",
        "subject": "Question about product features",
        "body_text": "Hey team, can you tell me if product X supports batch upload? Thanks!"
    },
    {
        "sender": "dan@example.com",
        "subject": "Help needed: cannot sync data",
        "body_text": "Syncing fails with timeout. Error logs attached (not included here). Please assist."
    }
]

def seed_sample_emails():
    with database.get_session() as s:
        existing = s.query(models.Email).count()
        if existing > 0:
            return
        for item in SAMPLES:
            eid = str(uuid.uuid4())
            e = models.Email(
                id=eid,
                sender=item["sender"],
                subject=item["subject"],
                body_text=item["body_text"],
                received_at=dt.datetime.utcnow() - dt.timedelta(hours=1)
            )
            s.add(e)
            s.commit()
            # process/draft
            processor.process_and_draft(e)
