from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    products = db.relationship("Product", backref="category", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "name": self.name}

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(80), nullable=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)
    stock = db.Column(db.Integer, nullable=True, default=0)
    unit = db.Column(db.String(40), nullable=True)
    specs = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    def image_url(self):
        if self.image_filename:
            return f"/static/uploads/{self.image_filename}"
        return "/static/img-placeholder.png"

    def specs_dict(self):
        if not self.specs:
            return {}
        try:
            return json.loads(self.specs)
        except:
            return {"details": self.specs}

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "sku": self.sku,
            "description": self.description,
            "price": self.price,
            "stock": self.stock,
            "unit": self.unit,
            "specs": self.specs_dict(),
            "image_url": self.image_url(),
            "category": self.category.to_dict() if self.category else None,
        }
