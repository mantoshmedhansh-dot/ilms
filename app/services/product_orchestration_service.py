"""
Product Orchestration Service

Central service that orchestrates all downstream actions when a product is created/updated.
This eliminates the need for manual duplicate entries in Serialization module.

When a product is created (item_type = FG or SP):
1. Auto-generate model_code (3 letters) from product name if not provided
2. Create ModelCodeReference entry for serialization
3. Create ProductSerialSequence entry for barcode generation

This follows the principle: "One entry, automatic propagation"
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.serialization import ModelCodeReference, ProductSerialSequence


class ProductOrchestrationService:
    """
    Central service that orchestrates all downstream actions
    when a product is created or updated.

    Design principle: Single point of entry, automatic propagation
    """

    # Item types that require serialization setup
    SERIALIZABLE_ITEM_TYPES = ["FG", "SP"]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def on_product_created(self, product: Product) -> dict:
        """
        Called after a product is created. Triggers serialization setup.

        Args:
            product: The product that was just created

        Returns:
            dict with results of all orchestration actions
        """
        results = {
            "product_id": str(product.id),
            "product_sku": product.sku,
            "actions_performed": []
        }

        # Only setup serialization for FG and SP items
        if not self._should_setup_serialization(product):
            results["skipped"] = f"Item type '{product.item_type}' does not require serialization"
            return results

        # 1. Auto-generate model_code if not provided
        if not product.model_code:
            model_code = await self._generate_model_code(product)
            if model_code:
                product.model_code = model_code
                results["model_code"] = model_code
                results["actions_performed"].append("model_code_generated")

        # 2. Create ModelCodeReference entry
        if product.model_code:
            model_ref_id = await self._create_model_code_reference(product)
            if model_ref_id:
                results["model_code_reference_id"] = model_ref_id
                results["actions_performed"].append("model_code_reference_created")

            # 3. Create ProductSerialSequence entry
            serial_seq_id = await self._create_serial_sequence(product)
            if serial_seq_id:
                results["serial_sequence_id"] = serial_seq_id
                results["actions_performed"].append("serial_sequence_created")

        return results

    async def on_product_updated(self, product: Product, old_model_code: Optional[str]) -> dict:
        """
        Called after a product is updated. Updates serialization if model_code changed.

        Args:
            product: The updated product
            old_model_code: Previous model_code value (None if unchanged)

        Returns:
            dict with results of orchestration actions
        """
        results = {
            "product_id": str(product.id),
            "product_sku": product.sku,
            "actions_performed": []
        }

        # Only process if item type requires serialization
        if not self._should_setup_serialization(product):
            return results

        # If model_code was added or changed
        if product.model_code and product.model_code != old_model_code:
            # Update/create ModelCodeReference
            model_ref_id = await self._create_or_update_model_code_reference(product)
            if model_ref_id:
                results["model_code_reference_id"] = model_ref_id
                results["actions_performed"].append("model_code_reference_updated")

            # Update/create ProductSerialSequence
            serial_seq_id = await self._create_or_update_serial_sequence(product)
            if serial_seq_id:
                results["serial_sequence_id"] = serial_seq_id
                results["actions_performed"].append("serial_sequence_updated")

        return results

    def _should_setup_serialization(self, product: Product) -> bool:
        """
        Determine if this product needs serialization setup.
        Only FG (Finished Goods) and SP (Spare Parts) require serialization.
        """
        return product.item_type in self.SERIALIZABLE_ITEM_TYPES

    async def _generate_model_code(self, product: Product) -> Optional[str]:
        """
        Auto-generate a unique 3-character model code from product name.

        Algorithm:
        1. Take first letters of first 3 words: "Aura Ionizer Elite" -> "AIE"
        2. If 2 words: "Ionizer Elite" -> "IEL" (first + first + second letters of last word)
        3. If single word: "Optima" -> "OPT" (first 3 letters)
        4. If code exists, iterate: IEL, IEM, IEN... until unique found

        Returns:
            Unique 3-letter model code or None if cannot generate
        """
        # Remove common words that don't add meaning
        skip_words = {'ILMS.AI', 'WATER', 'PURIFIER', 'RO', 'UV', 'UF', 'FILTER',
                      'THE', 'A', 'AN', 'WITH', 'AND', 'FOR', 'PLUS', 'PRO', 'LITE'}

        words = product.name.upper().split()
        words = [w for w in words if w not in skip_words and len(w) > 1]

        # Generate base code
        if len(words) >= 3:
            # First letter of first 3 significant words
            base_code = words[0][0] + words[1][0] + words[2][0]
        elif len(words) == 2:
            # First letter of first word + first 2 letters of second word
            base_code = words[0][0] + words[1][:2]
        elif len(words) == 1 and len(words[0]) >= 3:
            # First 3 letters of single word
            base_code = words[0][:3]
        else:
            # Fallback: use SKU prefix
            base_code = product.sku[:3].upper() if product.sku else "XXX"

        base_code = base_code.upper()[:3]

        # Ensure 3 characters
        while len(base_code) < 3:
            base_code += "X"

        # Find unique code
        code = base_code
        suffix = 0
        max_attempts = 26  # A to Z

        while suffix < max_attempts:
            # Check if code exists in ModelCodeReference
            exists = await self.db.execute(
                select(ModelCodeReference).where(ModelCodeReference.model_code == code)
            )
            if not exists.scalar_one_or_none():
                # Also check ProductSerialSequence
                seq_exists = await self.db.execute(
                    select(ProductSerialSequence).where(
                        ProductSerialSequence.model_code == code,
                        ProductSerialSequence.item_type == product.item_type
                    )
                )
                if not seq_exists.scalar_one_or_none():
                    # Also check other products
                    prod_exists = await self.db.execute(
                        select(Product).where(
                            Product.model_code == code,
                            Product.id != product.id
                        )
                    )
                    if not prod_exists.scalar_one_or_none():
                        return code  # Found unique code

            # Generate next code by changing last letter
            suffix += 1
            code = base_code[:2] + chr(65 + (ord(base_code[2]) - 65 + suffix) % 26)

        return None  # Could not find unique code

    async def _create_model_code_reference(self, product: Product) -> Optional[str]:
        """
        Create ModelCodeReference entry for the product.
        This maps the product to its 3-letter model code for serialization.
        Uses raw SQL to handle UUID type mismatch between model and production.

        Returns:
            str: ID of created record, or None if already exists
        """
        from sqlalchemy import text

        # Check if already exists
        existing = await self.db.execute(
            select(ModelCodeReference).where(ModelCodeReference.product_id == product.id)
        )
        if existing.scalar_one_or_none():
            return None  # Already exists

        # Also check by fg_code if set
        if product.fg_code:
            existing_fg = await self.db.execute(
                select(ModelCodeReference).where(ModelCodeReference.fg_code == product.fg_code)
            )
            if existing_fg.scalar_one_or_none():
                return None  # FG code already mapped

        # Use raw SQL to insert (production uses UUID type, model uses String)
        result = await self.db.execute(text('''
            INSERT INTO model_code_references
            (id, product_id, product_sku, fg_code, model_code, description, is_active, created_at, updated_at)
            VALUES
            (gen_random_uuid(), :product_id, :product_sku, :fg_code, :model_code, :description, true, NOW(), NOW())
            RETURNING id
        '''), {
            'product_id': product.id,
            'product_sku': product.sku,
            'fg_code': product.fg_code,
            'model_code': product.model_code,
            'description': f"Auto-created for {product.name}"
        })
        row = result.fetchone()
        return str(row[0]) if row else None

    async def _create_or_update_model_code_reference(self, product: Product) -> Optional[str]:
        """
        Create or update ModelCodeReference entry for the product.
        Uses raw SQL for updates to handle type mismatches.

        Returns:
            str: ID of created/updated record, or None if unchanged
        """
        from sqlalchemy import text

        # Check if exists for this product
        result = await self.db.execute(
            select(ModelCodeReference).where(ModelCodeReference.product_id == product.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing via raw SQL
            await self.db.execute(text('''
                UPDATE model_code_references
                SET product_sku = :product_sku, fg_code = :fg_code, model_code = :model_code, updated_at = NOW()
                WHERE product_id = :product_id
            '''), {
                'product_id': product.id,
                'product_sku': product.sku,
                'fg_code': product.fg_code,
                'model_code': product.model_code
            })
            return str(existing.id)
        else:
            # Create new
            return await self._create_model_code_reference(product)

    async def _create_serial_sequence(self, product: Product) -> Optional[str]:
        """
        Create ProductSerialSequence entry for the product.
        This initializes the serial number sequence for barcode generation.
        Uses raw SQL to handle UUID type mismatch between model and production.

        Returns:
            str: ID of created record, or None if already exists
        """
        from sqlalchemy import text

        # Check if already exists
        existing = await self.db.execute(
            select(ProductSerialSequence).where(
                ProductSerialSequence.model_code == product.model_code,
                ProductSerialSequence.item_type == product.item_type
            )
        )
        if existing.scalar_one_or_none():
            return None  # Already exists

        # Use raw SQL to insert (production uses UUID type, model uses String)
        result = await self.db.execute(text('''
            INSERT INTO product_serial_sequences
            (id, product_id, model_code, item_type, product_name, product_sku, last_serial, total_generated, max_serial, created_at, updated_at)
            VALUES
            (gen_random_uuid(), :product_id, :model_code, :item_type, :product_name, :product_sku, 0, 0, 99999999, NOW(), NOW())
            ON CONFLICT (model_code, item_type) DO NOTHING
            RETURNING id
        '''), {
            'product_id': product.id,
            'model_code': product.model_code,
            'item_type': product.item_type,
            'product_name': product.name,
            'product_sku': product.sku
        })
        row = result.fetchone()
        return str(row[0]) if row else None

    async def _create_or_update_serial_sequence(self, product: Product) -> Optional[str]:
        """
        Create or update ProductSerialSequence entry for the product.
        Uses raw SQL for updates to handle type mismatches.

        Returns:
            str: ID of created/updated record, or None if unchanged
        """
        from sqlalchemy import text

        # Check if exists for this model_code + item_type
        result = await self.db.execute(
            select(ProductSerialSequence).where(
                ProductSerialSequence.model_code == product.model_code,
                ProductSerialSequence.item_type == product.item_type
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update product linkage via raw SQL (don't reset serial counters!)
            await self.db.execute(text('''
                UPDATE product_serial_sequences
                SET product_id = :product_id, product_name = :product_name, product_sku = :product_sku, updated_at = NOW()
                WHERE model_code = :model_code AND item_type = :item_type
            '''), {
                'product_id': product.id,
                'product_name': product.name,
                'product_sku': product.sku,
                'model_code': product.model_code,
                'item_type': product.item_type
            })
            return str(existing.id)
        else:
            # Create new
            return await self._create_serial_sequence(product)

    async def sync_existing_products(self) -> dict:
        """
        One-time utility to sync existing FG/SP products that don't have model codes.
        Run this to fix products that were created before orchestration was implemented.

        Returns:
            dict with count of products synced
        """
        # Find FG/SP products without model_code in ModelCodeReference
        result = await self.db.execute(
            select(Product).where(
                Product.item_type.in_(self.SERIALIZABLE_ITEM_TYPES),
                Product.is_active == True
            )
        )
        products = result.scalars().all()

        synced = []
        for product in products:
            # Check if already has ModelCodeReference
            ref_exists = await self.db.execute(
                select(ModelCodeReference).where(ModelCodeReference.product_id == product.id)
            )
            if ref_exists.scalar_one_or_none():
                continue  # Already synced

            # Generate model_code if not set
            if not product.model_code:
                model_code = await self._generate_model_code(product)
                if model_code:
                    product.model_code = model_code

            if product.model_code:
                # Create ModelCodeReference
                model_ref = await self._create_model_code_reference(product)

                # Create ProductSerialSequence
                serial_seq = await self._create_serial_sequence(product)

                synced.append({
                    "product_sku": product.sku,
                    "product_name": product.name,
                    "item_type": product.item_type,
                    "model_code": product.model_code,
                    "model_ref_created": model_ref is not None,
                    "serial_seq_created": serial_seq is not None
                })

        await self.db.commit()

        return {
            "total_synced": len(synced),
            "products": synced
        }
