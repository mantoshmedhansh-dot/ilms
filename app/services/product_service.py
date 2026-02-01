from typing import List, Optional, Tuple
from math import ceil
import uuid

from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import (
    Product, ProductStatus, ProductImage, ProductSpecification,
    ProductVariant, ProductDocument
)
from app.models.category import Category
from app.models.brand import Brand
from app.schemas.product import (
    ProductCreate, ProductUpdate,
    ProductImageCreate, ProductSpecCreate,
    ProductVariantCreate, ProductVariantUpdate,
    ProductDocumentCreate
)


class ProductService:
    """Service for managing products and related entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== CATEGORY METHODS ====================

    async def get_categories(
        self,
        parent_id: Optional[uuid.UUID] = None,
        roots_only: bool = False,
        include_inactive: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Category], int]:
        """Get categories with optional parent filter.

        Args:
            parent_id: Filter by parent category ID (children of this category)
            roots_only: If True, only return ROOT categories (parent_id IS NULL)
            include_inactive: Include inactive categories
            skip: Pagination offset
            limit: Pagination limit
        """
        stmt = select(Category).order_by(Category.sort_order, Category.name)
        count_stmt = select(func.count(Category.id))

        # Filter by parent
        if roots_only:
            # Only root categories (parent_id IS NULL)
            stmt = stmt.where(Category.parent_id.is_(None))
            count_stmt = count_stmt.where(Category.parent_id.is_(None))
        elif parent_id:
            # Children of specific parent
            stmt = stmt.where(Category.parent_id == parent_id)
            count_stmt = count_stmt.where(Category.parent_id == parent_id)
        # else: include all categories (no filter)

        if not include_inactive:
            stmt = stmt.where(Category.is_active == True)
            count_stmt = count_stmt.where(Category.is_active == True)

        # Count
        total = (await self.db.execute(count_stmt)).scalar()

        # Paginate
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        categories = result.scalars().all()

        return list(categories), total

    async def get_category_by_id(self, category_id: uuid.UUID) -> Optional[Category]:
        """Get category by ID."""
        stmt = select(Category).where(Category.id == category_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_category_by_slug(self, slug: str) -> Optional[Category]:
        """Get category by slug."""
        stmt = select(Category).where(Category.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_category(self, data: dict) -> Category:
        """Create a new category."""
        category = Category(**data)
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def update_category(
        self,
        category_id: uuid.UUID,
        data: dict
    ) -> Optional[Category]:
        """Update a category."""
        category = await self.get_category_by_id(category_id)
        if not category:
            return None

        for key, value in data.items():
            if value is not None:
                setattr(category, key, value)

        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def get_category_tree(self) -> List[Category]:
        """Get full category tree with recursive children loading."""
        from sqlalchemy.orm import selectinload

        # Use recursive selectinload to load all nested children
        # This handles categories up to 5 levels deep
        stmt = (
            select(Category)
            .options(
                selectinload(Category.children)
                .selectinload(Category.children)
                .selectinload(Category.children)
                .selectinload(Category.children)
                .selectinload(Category.children)
            )
            .where(Category.parent_id.is_(None))
            .where(Category.is_active == True)
            .order_by(Category.sort_order, Category.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ==================== BRAND METHODS ====================

    async def get_brands(
        self,
        include_inactive: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Brand], int]:
        """Get brands list."""
        stmt = select(Brand).order_by(Brand.sort_order, Brand.name)

        if not include_inactive:
            stmt = stmt.where(Brand.is_active == True)

        # Count
        count_stmt = select(func.count(Brand.id))
        if not include_inactive:
            count_stmt = count_stmt.where(Brand.is_active == True)
        total = (await self.db.execute(count_stmt)).scalar()

        # Paginate
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        brands = result.scalars().all()

        return list(brands), total

    async def get_brand_by_id(self, brand_id: uuid.UUID) -> Optional[Brand]:
        """Get brand by ID."""
        stmt = select(Brand).where(Brand.id == brand_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_brand_by_slug(self, slug: str) -> Optional[Brand]:
        """Get brand by slug."""
        stmt = select(Brand).where(Brand.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_brand(self, data: dict) -> Brand:
        """Create a new brand."""
        brand = Brand(**data)
        self.db.add(brand)
        await self.db.commit()
        await self.db.refresh(brand)
        return brand

    async def update_brand(self, brand_id: uuid.UUID, data: dict) -> Optional[Brand]:
        """Update a brand."""
        brand = await self.get_brand_by_id(brand_id)
        if not brand:
            return None

        for key, value in data.items():
            if value is not None:
                setattr(brand, key, value)

        await self.db.commit()
        await self.db.refresh(brand)
        return brand

    # ==================== PRODUCT METHODS ====================

    async def get_products(
        self,
        category_id: Optional[uuid.UUID] = None,
        brand_id: Optional[uuid.UUID] = None,
        status: Optional[ProductStatus] = None,
        search: Optional[str] = None,
        is_featured: Optional[bool] = None,
        is_active: Optional[bool] = True,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Product], int]:
        """Get products with filters."""
        stmt = (
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.brand),
                selectinload(Product.images)
            )
        )

        # Apply filters
        filters = []

        if category_id:
            filters.append(Product.category_id == category_id)

        if brand_id:
            filters.append(Product.brand_id == brand_id)

        if status:
            filters.append(Product.status == status)

        if is_active is not None:
            filters.append(Product.is_active == is_active)

        if is_featured is not None:
            filters.append(Product.is_featured == is_featured)

        if min_price is not None:
            filters.append(Product.selling_price >= min_price)

        if max_price is not None:
            filters.append(Product.selling_price <= max_price)

        if search:
            search_filter = f"%{search}%"
            filters.append(
                or_(
                    Product.name.ilike(search_filter),
                    Product.sku.ilike(search_filter),
                    Product.model_number.ilike(search_filter),
                    Product.description.ilike(search_filter)
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        # Count total
        count_stmt = select(func.count(Product.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar()

        # Sorting
        sort_column = getattr(Product, sort_by, Product.created_at)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Pagination
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        products = result.scalars().unique().all()

        return list(products), total

    async def get_product_by_id(
        self,
        product_id: uuid.UUID,
        include_all: bool = False
    ) -> Optional[Product]:
        """Get product by ID."""
        stmt = select(Product).where(Product.id == product_id)

        if include_all:
            stmt = stmt.options(
                selectinload(Product.category),
                selectinload(Product.brand),
                selectinload(Product.images),
                selectinload(Product.specifications),
                selectinload(Product.variants),
                selectinload(Product.documents)
            )
        else:
            stmt = stmt.options(
                selectinload(Product.category),
                selectinload(Product.brand),
                selectinload(Product.images)
            )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU."""
        stmt = (
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.brand),
                selectinload(Product.images)
            )
            .where(Product.sku == sku)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_product_by_slug(self, slug: str) -> Optional[Product]:
        """Get product by slug."""
        stmt = (
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.brand),
                selectinload(Product.images),
                selectinload(Product.specifications),
                selectinload(Product.variants),
                selectinload(Product.documents)
            )
            .where(Product.slug == slug)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_product(self, data: ProductCreate) -> Product:
        """Create a new product with related entities."""
        # Extract nested data
        images_data = data.images or []
        specs_data = data.specifications or []
        variants_data = data.variants or []
        docs_data = data.documents or []

        # Create product
        product_data = data.model_dump(
            exclude={"images", "specifications", "variants", "documents"}
        )
        product = Product(**product_data)
        self.db.add(product)
        await self.db.flush()

        # Add images
        for img_data in images_data:
            image = ProductImage(
                product_id=product.id,
                **img_data.model_dump()
            )
            self.db.add(image)

        # Add specifications
        for spec_data in specs_data:
            spec = ProductSpecification(
                product_id=product.id,
                **spec_data.model_dump()
            )
            self.db.add(spec)

        # Add variants
        for var_data in variants_data:
            variant = ProductVariant(
                product_id=product.id,
                **var_data.model_dump()
            )
            self.db.add(variant)

        # Add documents
        for doc_data in docs_data:
            doc = ProductDocument(
                product_id=product.id,
                **doc_data.model_dump()
            )
            self.db.add(doc)

        await self.db.commit()

        # Reload with all relations
        return await self.get_product_by_id(product.id, include_all=True)

    async def update_product(
        self,
        product_id: uuid.UUID,
        data: ProductUpdate
    ) -> Optional[Product]:
        """Update a product."""
        product = await self.get_product_by_id(product_id)
        if not product:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(product, key, value)

        await self.db.commit()
        return await self.get_product_by_id(product_id, include_all=True)

    async def delete_product(self, product_id: uuid.UUID) -> bool:
        """Soft delete a product by deactivating."""
        product = await self.get_product_by_id(product_id)
        if not product:
            return False

        product.is_active = False
        product.status = ProductStatus.INACTIVE.value
        await self.db.commit()
        return True

    # ==================== PRODUCT IMAGE METHODS ====================

    async def add_product_image(
        self,
        product_id: uuid.UUID,
        data: ProductImageCreate
    ) -> ProductImage:
        """Add an image to a product."""
        image = ProductImage(product_id=product_id, **data.model_dump())
        self.db.add(image)
        await self.db.commit()
        await self.db.refresh(image)
        return image

    async def delete_product_image(self, image_id: uuid.UUID) -> bool:
        """Delete a product image."""
        stmt = select(ProductImage).where(ProductImage.id == image_id)
        result = await self.db.execute(stmt)
        image = result.scalar_one_or_none()

        if not image:
            return False

        await self.db.delete(image)
        await self.db.commit()
        return True

    async def set_primary_image(
        self,
        product_id: uuid.UUID,
        image_id: uuid.UUID
    ) -> bool:
        """Set an image as primary for a product."""
        # Reset all images to non-primary
        stmt = select(ProductImage).where(ProductImage.product_id == product_id)
        result = await self.db.execute(stmt)
        images = result.scalars().all()

        for img in images:
            img.is_primary = (img.id == image_id)

        await self.db.commit()
        return True

    # ==================== PRODUCT VARIANT METHODS ====================

    async def add_product_variant(
        self,
        product_id: uuid.UUID,
        data: ProductVariantCreate
    ) -> ProductVariant:
        """Add a variant to a product."""
        variant = ProductVariant(product_id=product_id, **data.model_dump())
        self.db.add(variant)
        await self.db.commit()
        await self.db.refresh(variant)
        return variant

    async def update_product_variant(
        self,
        variant_id: uuid.UUID,
        data: ProductVariantUpdate
    ) -> Optional[ProductVariant]:
        """Update a product variant."""
        stmt = select(ProductVariant).where(ProductVariant.id == variant_id)
        result = await self.db.execute(stmt)
        variant = result.scalar_one_or_none()

        if not variant:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(variant, key, value)

        await self.db.commit()
        await self.db.refresh(variant)
        return variant

    async def delete_product_variant(self, variant_id: uuid.UUID) -> bool:
        """Delete a product variant."""
        stmt = select(ProductVariant).where(ProductVariant.id == variant_id)
        result = await self.db.execute(stmt)
        variant = result.scalar_one_or_none()

        if not variant:
            return False

        await self.db.delete(variant)
        await self.db.commit()
        return True

    # ==================== PRODUCT STATISTICS ====================

    async def get_product_stats(self) -> dict:
        """Get product statistics."""
        # Total products
        total = (await self.db.execute(
            select(func.count(Product.id))
        )).scalar()

        # By status
        status_counts = {}
        for status in ProductStatus:
            count = (await self.db.execute(
                select(func.count(Product.id)).where(Product.status == status)
            )).scalar()
            status_counts[status.value] = count

        # Active products
        active = (await self.db.execute(
            select(func.count(Product.id)).where(Product.is_active == True)
        )).scalar()

        # Featured products
        featured = (await self.db.execute(
            select(func.count(Product.id)).where(Product.is_featured == True)
        )).scalar()

        return {
            "total": total,
            "active": active,
            "featured": featured,
            "by_status": status_counts,
        }

    async def get_top_selling_products(self, limit: int = 5) -> List[dict]:
        """Get top selling products based on order item quantities."""
        from app.models.order import OrderItem

        # Query products with sum of order quantities
        stmt = (
            select(
                Product.id,
                Product.name,
                Product.sku,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("total_sales")
            )
            .outerjoin(OrderItem, OrderItem.product_id == Product.id)
            .where(Product.is_active == True)
            .group_by(Product.id, Product.name, Product.sku)
            .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "id": str(row.id),
                "name": row.name,
                "sku": row.sku,
                "sales": int(row.total_sales),
            }
            for row in rows
        ]
