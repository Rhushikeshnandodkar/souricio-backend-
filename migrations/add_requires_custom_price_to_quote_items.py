"""
Migration script to add requires_custom_price column to quote_items table
and make subtotal/total nullable in quotes table.

Run this script to update your database schema:
    python migrations/add_requires_custom_price_to_quote_items.py
"""
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import engine
from app.core.config import settings


def run_migration():
    """Run the migration to add requires_custom_price column and update quotes table"""
    
    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()
        
        try:
            print("Starting migration...")
            
            # Check if column already exists
            check_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='quote_items' 
                AND column_name='requires_custom_price'
            """)
            result = conn.execute(check_column_query)
            column_exists = result.fetchone() is not None
            
            if not column_exists:
                print("Adding requires_custom_price column to quote_items table...")
                # Add requires_custom_price column with default False
                conn.execute(text("""
                    ALTER TABLE quote_items 
                    ADD COLUMN requires_custom_price BOOLEAN NOT NULL DEFAULT FALSE
                """))
                print("✓ Added requires_custom_price column")
            else:
                print("✓ requires_custom_price column already exists")
            
            # Check if subtotal is nullable
            check_subtotal_query = text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name='quotes' 
                AND column_name='subtotal'
            """)
            result = conn.execute(check_subtotal_query)
            subtotal_row = result.fetchone()
            
            if subtotal_row and subtotal_row[0] == 'NO':
                print("Making subtotal nullable in quotes table...")
                conn.execute(text("""
                    ALTER TABLE quotes 
                    ALTER COLUMN subtotal DROP NOT NULL
                """))
                print("✓ Made subtotal nullable")
            else:
                print("✓ subtotal is already nullable")
            
            # Check if total is nullable
            check_total_query = text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name='quotes' 
                AND column_name='total'
            """)
            result = conn.execute(check_total_query)
            total_row = result.fetchone()
            
            if total_row and total_row[0] == 'NO':
                print("Making total nullable in quotes table...")
                conn.execute(text("""
                    ALTER TABLE quotes 
                    ALTER COLUMN total DROP NOT NULL
                """))
                print("✓ Made total nullable")
            else:
                print("✓ total is already nullable")
            
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
    print("Migration: Add requires_custom_price to quote_items")
    print("=" * 60)
    print(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'N/A'}")
    print()
    
    try:
        run_migration()
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
