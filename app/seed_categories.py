"""
Seed script to add 6 main categories to the database.
Run this script to populate the database with the required categories.
"""
from app.db.database import SessionLocal
from app.services.category_service import create_category
from app.schemas.models import CategoryCreate


def seed_categories():
    """Seed the database with 6 main categories."""
    db = SessionLocal()
    
    try:
        print("🌱 Starting to seed categories...")
        
        # Define the 6 categories
        category_data = [
            {
                "name": "Manufacturing",
                "slug": "manufacturing",
                "description": "Comprehensive manufacturing solutions and equipment for industrial production",
                "meta_title": "Manufacturing Equipment & Solutions",
                "meta_description": "Browse our complete range of manufacturing equipment and solutions for industrial production"
            },
            {
                "name": "Industrial Machinery",
                "slug": "industrial-machinery",
                "description": "Heavy-duty machinery and equipment for industrial manufacturing processes",
                "meta_title": "Industrial Machinery | Manufacturing Equipment",
                "meta_description": "Browse our selection of industrial machinery and manufacturing equipment"
            },
            {
                "name": "Tools & Equipment",
                "slug": "tools-equipment",
                "description": "Hand tools, power tools, and precision equipment for manufacturing",
                "meta_title": "Manufacturing Tools & Equipment",
                "meta_description": "Quality tools and equipment for all your manufacturing needs"
            },
            {
                "name": "Raw Materials",
                "slug": "raw-materials",
                "description": "Essential raw materials and supplies for manufacturing processes",
                "meta_title": "Raw Materials for Manufacturing",
                "meta_description": "Source high-quality raw materials for your production line"
            },
            {
                "name": "Safety Equipment",
                "slug": "safety-equipment",
                "description": "Personal protective equipment and safety gear for manufacturing facilities",
                "meta_title": "Manufacturing Safety Equipment",
                "meta_description": "Keep your workforce safe with our comprehensive safety equipment"
            },
            {
                "name": "Automation Systems",
                "slug": "automation-systems",
                "description": "Automated systems and robotics for modern manufacturing",
                "meta_title": "Manufacturing Automation Systems",
                "meta_description": "Upgrade your production with cutting-edge automation technology"
            }
        ]
        
        categories_created = 0
        categories_existing = 0
        
        for idx, cat_info in enumerate(category_data):
            try:
                category = create_category(db, CategoryCreate(
                    name=cat_info["name"],
                    description=cat_info["description"],
                    meta_title=cat_info["meta_title"],
                    meta_description=cat_info["meta_description"],
                    sort_order=idx + 1,
                    is_active=True
                ))
                categories_created += 1
                print(f"  ✓ Created category: {cat_info['name']} (slug: {category.slug})")
            except ValueError as e:
                # Category might already exist, try to get it
                from app.db.models.category import Category
                existing = db.query(Category).filter(
                    Category.slug == cat_info["slug"]
                ).first()
                if existing:
                    categories_existing += 1
                    print(f"  ⚠ Category already exists: {cat_info['name']} (slug: {cat_info['slug']})")
                else:
                    print(f"  ✗ Error creating category {cat_info['name']}: {e}")
        
        print(f"\n✅ Category seeding completed!")
        print(f"   - Categories created: {categories_created}")
        print(f"   - Categories already existing: {categories_existing}")
        print(f"   - Total categories: {categories_created + categories_existing}")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_categories()
