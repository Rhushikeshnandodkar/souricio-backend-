"""
Migration script to add GST (Goods and Services Tax) columns to quotes and quote_items tables.

Run this script to update your database schema:
    python migrations/add_gst_to_quotes.py
"""
from app.core.config import settings
from app.db.database import engine
from sqlalchemy import text
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Run the migration to add GST columns to quotes and quote_items tables"""

    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()

        try:
            print("Starting migration...")

            # Check if columns already exist in quote_items table
            check_quote_items_columns = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='quote_items' 
                AND column_name IN ('gst_rate', 'tax_amount', 'item_total', 'item_total_with_tax')
            """)
            result = conn.execute(check_quote_items_columns)
            existing_quote_items_columns = {row[0]
                                            for row in result.fetchall()}

            # Add GST columns to quote_items table
            if 'gst_rate' not in existing_quote_items_columns:
                print("Adding gst_rate column to quote_items table...")
                conn.execute(text("""
                    ALTER TABLE quote_items 
                    ADD COLUMN gst_rate NUMERIC(5, 2)
                """))
                print("✓ Added gst_rate column")

            if 'item_total' not in existing_quote_items_columns:
                print("Adding item_total column to quote_items table...")
                conn.execute(text("""
                    ALTER TABLE quote_items 
                    ADD COLUMN item_total NUMERIC(10, 2)
                """))
                print("✓ Added item_total column")

            if 'tax_amount' not in existing_quote_items_columns:
                print("Adding tax_amount column to quote_items table...")
                conn.execute(text("""
                    ALTER TABLE quote_items 
                    ADD COLUMN tax_amount NUMERIC(10, 2)
                """))
                print("✓ Added tax_amount column")

            if 'item_total_with_tax' not in existing_quote_items_columns:
                print("Adding item_total_with_tax column to quote_items table...")
                conn.execute(text("""
                    ALTER TABLE quote_items 
                    ADD COLUMN item_total_with_tax NUMERIC(10, 2)
                """))
                print("✓ Added item_total_with_tax column")

            # Check if columns already exist in quotes table
            check_quotes_columns = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='quotes' 
                AND column_name IN ('total_tax', 'tax_breakdown')
            """)
            result = conn.execute(check_quotes_columns)
            existing_quotes_columns = {row[0] for row in result.fetchall()}

            # Add tax columns to quotes table
            if 'total_tax' not in existing_quotes_columns:
                print("Adding total_tax column to quotes table...")
                conn.execute(text("""
                    ALTER TABLE quotes 
                    ADD COLUMN total_tax NUMERIC(10, 2)
                """))
                print("✓ Added total_tax column")

            if 'tax_breakdown' not in existing_quotes_columns:
                print("Adding tax_breakdown column to quotes table...")
                # Check database type for JSON support
                try:
                    # Try PostgreSQL JSONB first
                    conn.execute(text("""
                        ALTER TABLE quotes 
                        ADD COLUMN tax_breakdown JSONB
                    """))
                except Exception:
                    # Fallback to JSON
                    conn.execute(text("""
                        ALTER TABLE quotes 
                        ADD COLUMN tax_breakdown JSON
                    """))
                print("✓ Added tax_breakdown column")

            # Add check constraint for GST rates (optional, but good practice)
            # Check if constraint already exists
            check_constraint = text("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name='quote_items' 
                AND constraint_name='check_valid_gst_rate'
            """)
            result = conn.execute(check_constraint)
            constraint_exists = result.fetchone() is not None

            if not constraint_exists:
                print("Adding check constraint for valid GST rates...")
                try:
                    conn.execute(text("""
                        ALTER TABLE quote_items 
                        ADD CONSTRAINT check_valid_gst_rate 
                        CHECK (gst_rate IS NULL OR gst_rate IN (5.00, 12.00, 18.00, 28.00))
                    """))
                    print("✓ Added GST rate check constraint")
                except Exception as e:
                    print(f"⚠ Warning: Could not add GST rate constraint: {e}")
                    print(
                        "  This is not critical - validation will be handled in application code")

            # Commit the transaction
            trans.commit()
            print("\n✅ Migration completed successfully!")

        except Exception as e:
            # Rollback on error
            trans.rollback()
            print(f"\n❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add GST columns to quotes and quote_items")
    print("=" * 60)
    print(
        f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'N/A'}")
    print()

    try:
        run_migration()
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
