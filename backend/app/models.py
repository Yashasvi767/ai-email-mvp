from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
import datetime as dt

Base = declarative_base()

class Email(Base):
    __tablename__ = "emails"
    id = Column(String, primary_key=True, index=True)
    sender = Column(String, nullable=False)
    subject = Column(String)
    body_text = Column(Text)
    received_at = Column(DateTime, default=dt.datetime.utcnow)
    raw_headers = Column(Text)
    raw_html = Column(Text)
    source = Column(String, default="seed")
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    meta = relationship("EmailMeta", uselist=False, back_populates="email")
    responses = relationship("Response", back_populates="email")

class EmailMeta(Base):
    __tablename__ = "email_meta"
    email_id = Column(String, ForeignKey("emails.id"), primary_key=True)
    sentiment = Column(String)
    urgency = Column(String)
    priority = Column(Integer)
    keywords = Column(JSON)
    contact_phone = Column(String)
    contact_alt = Column(String)
    product_refs = Column(JSON)
    summary = Column(Text)
    ner_json = Column(JSON)
    status = Column(String, default="pending")
    updated_at = Column(DateTime, default=dt.datetime.utcnow)

    email = relationship("Email", back_populates="meta")

class Response(Base):
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(String, ForeignKey("emails.id"))
    draft_text = Column(Text)
    final_text = Column(Text)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    email = relationship("Email", back_populates="responses")
