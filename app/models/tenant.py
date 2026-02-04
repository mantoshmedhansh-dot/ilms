"""
Tenant management models for multi-tenant architecture
"""
from sqlalchemy import String, Integer, Boolean, Numeric, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class Tenant(Base):
    """
    Tenant/Organization model

    Each tenant represents a customer organization with its own data schema
    """
    __tablename__ = "tenants"
    __table_args__ = {'schema': 'public'}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subdomain: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    database_schema: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.plans.id", ondelete="SET NULL"),
        nullable=True
    )
    trial_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    onboarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    tenant_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
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
    plan: Mapped["Plan"] = relationship("Plan", back_populates="tenants")
    subscriptions: Mapped[list["TenantSubscription"]] = relationship(
        "TenantSubscription",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    feature_flags: Mapped[list["FeatureFlag"]] = relationship(
        "FeatureFlag",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    billing_history: Mapped[list["BillingHistory"]] = relationship(
        "BillingHistory",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )


class ErpModule(Base):
    """
    ERP Module definition model

    Represents available ERP modules that can be subscribed to
    (Renamed from Module to avoid conflict with existing Module model)
    """
    __tablename__ = "modules"
    __table_args__ = {'schema': 'public'}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=True)
    icon: Mapped[str] = mapped_column(String(50), nullable=True)
    color: Mapped[str] = mapped_column(String(20), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=True)
    price_monthly: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    price_yearly: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    is_base_module: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dependencies: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    sections: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    database_tables: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    api_endpoints: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    frontend_routes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    features: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    subscriptions: Mapped[list["TenantSubscription"]] = relationship(
        "TenantSubscription",
        back_populates="module"
    )


class Plan(Base):
    """
    Pricing plan model

    Represents bundled pricing plans (Starter, Growth, Professional, Enterprise)
    """
    __tablename__ = "plans"
    __table_args__ = {'schema': 'public'}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(20), nullable=True)
    price_inr: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    original_price_inr: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    discount_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    included_modules: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    max_users: Mapped[int] = mapped_column(Integer, nullable=True)
    max_transactions_monthly: Mapped[int] = mapped_column(Integer, nullable=True)
    features: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_popular: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=True)
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
    tenants: Mapped[list["Tenant"]] = relationship("Tenant", back_populates="plan")
    subscriptions: Mapped[list["TenantSubscription"]] = relationship(
        "TenantSubscription",
        back_populates="plan"
    )


class TenantSubscription(Base):
    """
    Tenant subscription to modules

    Tracks which modules are enabled for each tenant
    """
    __tablename__ = "tenant_subscriptions"
    __table_args__ = {'schema': 'public'}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id", ondelete="CASCADE"),
        nullable=False
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.modules.id", ondelete="CASCADE"),
        nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.plans.id", ondelete="SET NULL"),
        nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    subscription_type: Mapped[str] = mapped_column(String(20), nullable=True)
    billing_cycle: Mapped[str] = mapped_column(String(20), nullable=True)
    price_paid: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trial_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
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
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="subscriptions")
    module: Mapped["ErpModule"] = relationship("ErpModule", back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship("Plan", back_populates="subscriptions")


class FeatureFlag(Base):
    """
    Feature flag model

    Granular feature control within modules
    """
    __tablename__ = "feature_flags"
    __table_args__ = {'schema': 'public'}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id", ondelete="CASCADE"),
        nullable=False
    )
    module_code: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_key: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
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
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="feature_flags")


class BillingHistory(Base):
    """
    Billing history model

    Tracks invoices and payments for tenants
    """
    __tablename__ = "billing_history"
    __table_args__ = {'schema': 'public'}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id", ondelete="CASCADE"),
        nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    billing_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    billing_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=True)
    payment_transaction_id: Mapped[str] = mapped_column(String(255), nullable=True)
    invoice_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
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
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="billing_history")


class UsageMetric(Base):
    """
    Usage metrics model

    Tracks usage statistics for analytics and billing
    """
    __tablename__ = "usage_metrics"
    __table_args__ = {'schema': 'public'}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id", ondelete="CASCADE"),
        nullable=False
    )
    module_code: Mapped[str] = mapped_column(String(50), nullable=True)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=True)
    metric_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    metric_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class TokenBlacklist(Base):
    """
    Token blacklist for invalidating JWT tokens on logout.

    Stores JTI (JWT ID) of invalidated tokens until they expire naturally.
    A background job should periodically clean up expired entries.
    """
    __tablename__ = "token_blacklist"
    __table_args__ = {'schema': 'public'}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    jti: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    token_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'access' or 'refresh'
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    blacklisted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
