from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# 1. SETUP DATABASE (Using SQLite for local testing)
SQLALCHEMY_DATABASE_URL = "sqlite:///./tracker.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. DEFINE DATABASE MODELS
class ReferralLink(Base):
    __tablename__ = "referral_links"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True)      # e.g., "promo2026"
    target_url = Column(String)                        # e.g., "https://myproduct.com"

class ClickEvent(Base):
    __tablename__ = "click_events"
    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer, ForeignKey("referral_links.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="clicked")          # "clicked" or "purchased"

# Create tables in SQLite file
Base.metadata.create_all(bind=engine)

# 3. INITIALIZE FASTAPI APP
app = FastAPI()

# Helper dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. CORE ENDPOINT: Create a Referral Link (For testing purposes)
@app.post("/create-link/")
def create_link(slug: str, target_url: str, db: Session = Depends(get_db)):
    db_link = ReferralLink(slug=slug, target_url=target_url)
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return {"message": "Link created!", "tracking_url": f"http://127.0.0.1:8000/r/{slug}"}

# 5. CORE ENDPOINT: The Redirect & Click Tracker Engine
@app.get("/r/{slug}")
def redirect_and_track(slug: str, db: Session = Depends(get_db)):
    # Find the link by slug
    link = db.query(ReferralLink).filter(ReferralLink.slug == slug).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Referral link not found")
    
    # Log the click event in the database
    click = ClickEvent(link_id=link.id, status="clicked")
    db.add(click)
    db.commit()
    
    # Redirect user to the actual target URL
    return RedirectResponse(url=link.target_url, status_code=302)

# 6. CORE ENDPOINT: Simulate a Purchase (Conversion)
@app.post("/convert/{slug}")
def record_conversion(slug: str, db: Session = Depends(get_db)):
    link = db.query(ReferralLink).filter(ReferralLink.slug == slug).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    # Find the latest click for this link and update status to purchased
    click = db.query(ClickEvent).filter(ClickEvent.link_id == link.id, ClickEvent.status == "clicked").order_by(ClickEvent.timestamp.desc()).first()
    
    if click:
        click.status = "purchased"
        db.commit()
        return {"message": f"Conversion recorded for link: {slug}"}
    
    return {"message": "No active unpurchased click found to convert."}

# 7. CORE ENDPOINT: Raw Analytics Data (JSON view before we add charts)
@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    links = db.query(ReferralLink).all()
    results = []
    for link in links:
        total_clicks = db.query(ClickEvent).filter(ClickEvent.link_id == link.id).count()
        total_purchases = db.query(ClickEvent).filter(ClickEvent.link_id == link.id, ClickEvent.status == "purchased").count()
        results.append({
            "slug": link.slug,
            "target_url": link.target_url,
            "clicks": total_clicks,
            "purchases": total_purchases
        })
    return results