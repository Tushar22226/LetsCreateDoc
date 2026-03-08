from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database.db import Base

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    plan = Column(Text, nullable=True) # Cached documentation blueprint
    page_count = Column(Integer, nullable=False, default=10)
    status = Column(String(50), nullable=False, default="generating")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sections = relationship("Section", back_populates="project", cascade="all, delete-orphan", order_by="Section.order_index")
    diagrams = relationship("Diagram", back_populates="project", cascade="all, delete-orphan")

class Section(Base):
    __tablename__ = "sections"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True) # The generated markdown
    order_index = Column(Integer, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="sections")

class Diagram(Base):
    __tablename__ = "diagrams"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    image_data = Column(Text, nullable=False) # Store as base64 or bytes
    caption = Column(String(255), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="diagrams")
