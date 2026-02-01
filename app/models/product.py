import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.brand import Brand
    from app.models.inventory import StockItem
    from app.models.product_review import ProductReview, ProductQuestion


class ProductStatus(str, Enum):
    """Product status enumeration."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DISCONTINUED = "DISCONTINUED"
    OUT_OF_STOCK = "OUT_OF_STOCK"


class ProductItemType(str, Enum):
    """Product item type for classification."""
    FINISHED_GOODS = "FG"      # Water Purifiers, complete products
    SPARE_PART = "SP"          # Filters, Sub-assemblies
    COMPONENT = "CO"           # Electrical components
    CONSUMABLE = "CN"          # Cartridges, Membranes
    ACCESSORY = "AC"           # Add-ons, accessories


class Product(Base):
    """
    Main product model for Consumer Durable catalog.
    Includes pricing, warranty, and relationship to variants.
    """
    __tablename__ = "products"
    __table_args__ = (
        Index('ix_product_category_active_status', 'category_id', 'is_active', 'status'),
        Index('ix_product_item_type_active', 'item_type', 'is_active'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Basic Info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(280), unique=True, nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    model_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Master Product File - FG/Item Code (for serialization)
    fg_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
        index=True,
        comment="Formal product code e.g., WPRAIEL001"
    )
    model_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        index=True,
        comment="3-letter model code for barcode e.g., IEL"
    )

    # Vendor Part Code (supplier's unique code for this item)
    part_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        comment="Vendor's part code e.g., AFGPSW2001"
    )
    item_type: Mapped[str] = mapped_column(
        String(50),
        default="FG",
        nullable=False,
        comment="FG=Finished Goods, SP=Spare Part, CO=Component, CN=Consumable, AC=Accessory"
    )

    # Descriptions
    short_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    features: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # HTML/Markdown

    # Relationships
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Pricing (in INR, stored as Decimal for precision)
    mrp: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Maximum Retail Price"
    )
    selling_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Selling price to customer"
    )
    dealer_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Price for dealers/distributors"
    )
    cost_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Cost price (internal)"
    )

    # Tax & Compliance
    hsn_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="HSN/SAC code for GST"
    )
    gst_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        default=18.00,
        comment="GST rate percentage"
    )

    # Warranty
    warranty_months: Mapped[int] = mapped_column(
        Integer,
        default=12,
        comment="Standard warranty in months"
    )
    extended_warranty_available: Mapped[bool] = mapped_column(Boolean, default=False)
    warranty_terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Physical Attributes - Dimensions & Weight
    dead_weight_kg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 3),
        nullable=True,
        comment="Actual physical weight in kg"
    )
    length_cm: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Length in centimeters"
    )
    width_cm: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Width in centimeters"
    )
    height_cm: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Height in centimeters"
    )

    # Inventory
    min_stock_level: Mapped[int] = mapped_column(Integer, default=10)
    max_stock_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Status & Display
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        comment="DRAFT, ACTIVE, INACTIVE, DISCONTINUED, OUT_OF_STOCK"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bestseller: Mapped[bool] = mapped_column(Boolean, default=False)
    is_new_arrival: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # SEO
    meta_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meta_keywords: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Additional Data (flexible JSONB storage)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="products")
    brand: Mapped["Brand"] = relationship("Brand", back_populates="products")
    images: Mapped[List["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order"
    )
    specifications: Mapped[List["ProductSpecification"]] = relationship(
        "ProductSpecification",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductSpecification.sort_order"
    )
    variants: Mapped[List["ProductVariant"]] = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    documents: Mapped[List["ProductDocument"]] = relationship(
        "ProductDocument",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    stock_items: Mapped[List["StockItem"]] = relationship(
        "StockItem",
        back_populates="product"
    )
    reviews: Mapped[List["ProductReview"]] = relationship(
        "ProductReview",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    questions: Mapped[List["ProductQuestion"]] = relationship(
        "ProductQuestion",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    @property
    def discount_percentage(self) -> float:
        """Calculate discount percentage from MRP."""
        if self.mrp and self.selling_price and self.mrp > 0:
            return float(((self.mrp - self.selling_price) / self.mrp) * 100)
        return 0.0

    @property
    def primary_image(self) -> Optional["ProductImage"]:
        """Get the primary product image."""
        for img in self.images:
            if img.is_primary:
                return img
        return self.images[0] if self.images else None

    @property
    def volumetric_weight_kg(self) -> float:
        """
        Calculate volumetric weight using formula: (L × W × H) / 5000

        This is the industry standard divisor for courier companies.
        Dimensions must be in centimeters.
        """
        if self.length_cm and self.width_cm and self.height_cm:
            volume = float(self.length_cm) * float(self.width_cm) * float(self.height_cm)
            return round(volume / 5000, 3)
        return 0.0

    @property
    def chargeable_weight_kg(self) -> float:
        """
        Calculate chargeable weight = MAX(dead_weight, volumetric_weight)

        Transporters charge based on whichever is higher:
        - Dead weight (actual physical weight)
        - Volumetric weight (space occupied)
        """
        dead = float(self.dead_weight_kg) if self.dead_weight_kg else 0.0
        volumetric = self.volumetric_weight_kg
        return max(dead, volumetric)

    @property
    def weight_info(self) -> dict:
        """Get complete weight information for the product."""
        return {
            "dead_weight_kg": float(self.dead_weight_kg) if self.dead_weight_kg else None,
            "volumetric_weight_kg": self.volumetric_weight_kg,
            "chargeable_weight_kg": self.chargeable_weight_kg,
            "dimensions": {
                "length_cm": float(self.length_cm) if self.length_cm else None,
                "width_cm": float(self.width_cm) if self.width_cm else None,
                "height_cm": float(self.height_cm) if self.height_cm else None,
            }
        }

    def __repr__(self) -> str:
        return f"<Product(name='{self.name}', sku='{self.sku}', fg_code='{self.fg_code}')>"


class ProductImage(Base):
    """Product images with support for multiple images per product."""
    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )

    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    alt_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="images")

    def __repr__(self) -> str:
        return f"<ProductImage(product_id='{self.product_id}', primary={self.is_primary})>"


class ProductSpecification(Base):
    """
    Product specifications as key-value pairs.
    Supports grouping (e.g., 'General', 'Technical', 'Dimensions').
    """
    __tablename__ = "product_specifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )

    group_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="General",
        comment="Specification group (e.g., General, Technical)"
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)

    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="specifications")

    def __repr__(self) -> str:
        return f"<ProductSpec(key='{self.key}', value='{self.value}')>"


class ProductVariant(Base):
    """
    Product variants for different configurations.
    E.g., different capacities, colors, or sizes.
    """
    __tablename__ = "product_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Variant Attributes (JSONB for flexibility)
    # e.g., {"color": "Blue", "capacity": "7L", "model": "Premium"}
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Pricing (can override parent product)
    mrp: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    selling_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)

    # Inventory
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Image
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="variants")

    @property
    def effective_mrp(self) -> Decimal:
        """Get effective MRP (variant override or parent product)."""
        return self.mrp if self.mrp else self.product.mrp

    @property
    def effective_selling_price(self) -> Decimal:
        """Get effective selling price."""
        return self.selling_price if self.selling_price else self.product.selling_price

    def __repr__(self) -> str:
        return f"<ProductVariant(name='{self.name}', sku='{self.sku}')>"


class DocumentType(str, Enum):
    """Types of product documents."""
    MANUAL = "MANUAL"
    BROCHURE = "BROCHURE"
    WARRANTY_CARD = "WARRANTY_CARD"
    SPECIFICATION_SHEET = "SPECIFICATION_SHEET"
    INSTALLATION_GUIDE = "INSTALLATION_GUIDE"
    VIDEO = "VIDEO"
    OTHER = "OTHER"


class ProductDocument(Base):
    """
    Product documents like manuals, brochures, warranty cards.
    """
    __tablename__ = "product_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(50),
        default="OTHER",
        nullable=False,
        comment="MANUAL, BROCHURE, WARRANTY_CARD, SPECIFICATION_SHEET, INSTALLATION_GUIDE, VIDEO, OTHER"
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="documents")

    def __repr__(self) -> str:
        return f"<ProductDocument(title='{self.title}', type='{self.document_type}')>"
