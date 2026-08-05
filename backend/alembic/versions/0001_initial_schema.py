"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _sync_columns() -> list[sa.Column]:
    """Columnas comunes de sincronización — docs/03-modelo-datos.md §6."""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_name", sa.String(), nullable=False),
        sa.Column("subscription_status", sa.String(), nullable=False, server_default="trial"),
        sa.Column("subscribed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("provider_code", sa.String(), nullable=True),
        sa.Column("nit", sa.String(length=20), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        *_sync_columns(),
    )
    op.create_index("ix_providers_tenant_id", "providers", ["tenant_id"])

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        *_sync_columns(),
    )
    op.create_index("ix_categories_tenant_id", "categories", ["tenant_id"])

    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        *_sync_columns(),
        sa.CheckConstraint("type IN ('sucursal', 'bodega')", name="ck_locations_type"),
    )
    op.create_index("ix_locations_tenant_id", "locations", ["tenant_id"])

    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("nit", sa.String(length=20), nullable=True),
        sa.Column("fullname", sa.String(), nullable=False),
        sa.Column("mail", sa.String(), nullable=True),
        *_sync_columns(),
    )
    op.create_index("ix_customers_tenant_id", "customers", ["tenant_id"])

    op.create_table(
        "product_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("sku", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("iva_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
        *_sync_columns(),
    )
    op.create_index("ix_product_references_tenant_id", "product_references", ["tenant_id"])
    op.create_index("ix_product_references_provider_id", "product_references", ["provider_id"])
    op.create_index("ix_product_references_category_id", "product_references", ["category_id"])
    op.create_index("ix_product_references_sku", "product_references", ["sku"])

    op.create_table(
        "items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "reference_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_references.id"),
            nullable=False,
        ),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("current_price", sa.Numeric(12, 2), nullable=False),
        *_sync_columns(),
    )
    op.create_index("ix_items_tenant_id", "items", ["tenant_id"])
    op.create_index("ix_items_reference_id", "items", ["reference_id"])
    op.create_index("ix_items_provider_id", "items", ["provider_id"])
    op.create_index("ix_items_location_id", "items", ["location_id"])

    op.create_table(
        "bills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("bill_number", sa.String(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_iva", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("hmac", sa.String(), nullable=True),
        sa.Column("prev_hash", sa.String(), nullable=True),
        *_sync_columns(),
    )
    op.create_index("ix_bills_tenant_id", "bills", ["tenant_id"])
    op.create_index("ix_bills_customer_id", "bills", ["customer_id"])
    op.create_index("ix_bills_bill_number", "bills", ["bill_number"])

    op.create_table(
        "bill_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bills.id"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("iva_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("iva_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("hmac", sa.String(), nullable=True),
        *_sync_columns(),
    )
    op.create_index("ix_bill_items_tenant_id", "bill_items", ["tenant_id"])
    op.create_index("ix_bill_items_bill_id", "bill_items", ["bill_id"])
    op.create_index("ix_bill_items_item_id", "bill_items", ["item_id"])


def downgrade() -> None:
    op.drop_table("bill_items")
    op.drop_table("bills")
    op.drop_table("items")
    op.drop_table("product_references")
    op.drop_table("customers")
    op.drop_table("locations")
    op.drop_table("categories")
    op.drop_table("providers")
    op.drop_table("tenants")
