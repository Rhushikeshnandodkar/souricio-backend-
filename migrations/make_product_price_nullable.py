"""
Migration script to make price column nullable in products table.

Run this script to update your database schema:
    python migrations/make_product_price_nullable.py
"""
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import engine
from app.core.config import settings


def run_migration():
    """Run the migration to make price column nullable in products table"""
    
    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()
        
        try:
            print("Starting migration...")
            
            # Check if price column is nullable
            check_price_query = text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name='products' 
                AND column_name='price'
            """)
            result = conn.execute(check_price_query)
            price_row = result.fetchone()
            
            if price_row and price_row[0] == 'NO':
                print("Making price column nullable in products table...")
                conn.execute(text("""
                    ALTER TABLE products 
                    ALTER COLUMN price DROP NOT NULL
                """))
                print("✓ Made price column nullable")
            else:
                print("✓ price column is already nullable")
            
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
    print("Migration: Make product price nullable")
    print("=" * 60)
    print(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'N/A'}")
    print()
    
    try:
        run_migration()
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
