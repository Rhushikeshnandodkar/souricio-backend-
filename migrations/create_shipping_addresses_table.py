"""
Migration script to create shipping_addresses table.

Run this script to update your database schema:
    python migrations/create_shipping_addresses_table.py
"""
import os
import sys

from sqlalchemy import text

from app.core.config import settings
from app.db.database import engine

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Run the migration to create shipping_addresses table."""
    with engine.connect() as conn:
        trans = conn.begin()

        try:
            print("Starting migration...")

            # Check if table already exists
            check_table_query = text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='shipping_addresses'
                """
            )
            result = conn.execute(check_table_query)
            table_exists = result.fetchone() is not None

            if not table_exists:
                print("Creating shipping_addresses table...")
                conn.execute(
                    text(
                        """
                        CREATE TABLE shipping_addresses (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL,
                            name VARCHAR(255) NOT NULL,
                            phone VARCHAR(20) NOT NULL,
                            country VARCHAR(100) NOT NULL DEFAULT 'India',
                            state VARCHAR(100) NOT NULL,
                            city VARCHAR(100) NOT NULL,
                            address1 VARCHAR(255) NOT NULL,
                            address2 VARCHAR(255),
                            postal_code VARCHAR(20) NOT NULL,
                            company VARCHAR(255),
                            instructions TEXT,
                            is_default BOOLEAN NOT NULL DEFAULT FALSE,
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            CONSTRAINT fk_shipping_addresses_user
                                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                        )
                        """
                    )
                )
                print("✓ Created shipping_addresses table")

                print("Creating indexes...")
                conn.execute(
                    text(
                        """
                        CREATE INDEX idx_shipping_addresses_user_id
                        ON shipping_addresses(user_id)
                        """
                    )
                )
                conn.execute(
                    text(
                        """
                        CREATE INDEX idx_shipping_addresses_user_default
                        ON shipping_addresses(user_id, is_default)
                        """
                    )
                )
                print("✓ Created indexes")
            else:
                print("✓ shipping_addresses table already exists")

            # Commit the transaction
            trans.commit()
            print("\n✅ Migration completed successfully!")

        except Exception as exc:
            # Rollback on error
            trans.rollback()
            print(f"\n❌ Migration failed: {exc}")
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Create shipping_addresses table")
    print("=" * 60)
    print(
        f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'N/A'}"
    )
    print()

    try:
        run_migration()
    except Exception as err:
        print(f"\nError: {err}")
        sys.exit(1)

