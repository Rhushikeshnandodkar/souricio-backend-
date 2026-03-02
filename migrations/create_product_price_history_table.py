"""
Migration script to create product_price_history table.

Run this script to update your database schema:
    python migrations/create_product_price_history_table.py
"""
from app.core.config import settings
from app.db.database import engine
from sqlalchemy import text
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Run the migration to create product_price_history table"""

    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()

        try:
            print("Starting migration...")

            # Check if table already exists
            check_table_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='product_price_history'
            """)
            result = conn.execute(check_table_query)
            table_exists = result.fetchone() is not None

            if not table_exists:
                print("Creating product_price_history table...")
                # Create the table
                conn.execute(text("""
                    CREATE TABLE product_price_history (
                        id SERIAL PRIMARY KEY,
                        product_id INTEGER NOT NULL,
                        variant_id INTEGER,
                        price NUMERIC(10, 2) NOT NULL,
                        quote_id INTEGER,
                        quote_item_id INTEGER,
                        created_by INTEGER NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT fk_product_price_history_product 
                            FOREIGN KEY (product_id) REFERENCES products(id),
                        CONSTRAINT fk_product_price_history_variant 
                            FOREIGN KEY (variant_id) REFERENCES product_variants(id),
                        CONSTRAINT fk_product_price_history_quote 
                            FOREIGN KEY (quote_id) REFERENCES quotes(id),
                        CONSTRAINT fk_product_price_history_quote_item 
                            FOREIGN KEY (quote_item_id) REFERENCES quote_items(id),
                        CONSTRAINT fk_product_price_history_user 
                            FOREIGN KEY (created_by) REFERENCES users(id)
                    )
                """))

                # Create indexes
                print("Creating indexes...")
                conn.execute(text("""
                    CREATE INDEX idx_product_price_history_product_id 
                    ON product_price_history(product_id)
                """))

                conn.execute(text("""
                    CREATE INDEX idx_product_price_history_variant_id 
                    ON product_price_history(variant_id)
                """))

                conn.execute(text("""
                    CREATE INDEX idx_product_price_history_quote_id 
                    ON product_price_history(quote_id)
                """))

                conn.execute(text("""
                    CREATE INDEX idx_product_price_history_created_by 
                    ON product_price_history(created_by)
                """))

                conn.execute(text("""
                    CREATE INDEX idx_product_price_history_created_at 
                    ON product_price_history(created_at)
                """))

                conn.execute(text("""
                    CREATE INDEX idx_product_variant_created 
                    ON product_price_history(product_id, variant_id, created_at DESC)
                """))

                print("✓ Created product_price_history table with indexes")
            else:
                print("✓ product_price_history table already exists")

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
    print("Migration: Create product_price_history table")
    print("=" * 60)
    print(
        f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'N/A'}")
    print()

    try:
        run_migration()
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
