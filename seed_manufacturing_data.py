"""
Seed script to add manufacturing component sourcing data to the database.
Run this script to populate the database with comprehensive manufacturing components,
categories, and tags for sourcing operations.
"""
from decimal import Decimal
from datetime import datetime
from app.db.database import SessionLocal
from app.services.category_service import create_category
from app.services.tag_service import create_tag
from app.services.product_service import create_product
from app.schemas.models import (
    CategoryCreate,
    TagCreate,
    ProductCreate,
    ProductVariant,
    ProductStatus
)


def seed_manufacturing_data():
    """Seed the database with manufacturing component sourcing data."""
    db = SessionLocal()
    
    try:
        print("🌱 Starting to seed manufacturing component data...")
        
        # Create Main Categories
        print("\n📁 Creating main categories...")
        main_categories = {}
        
        main_category_data = [
            {
                "name": "Electronic Components",
                "description": "Electronic components and parts for circuit assembly and electronic manufacturing",
                "meta_title": "Electronic Components | Manufacturing Sourcing",
                "meta_description": "Source electronic components including microcontrollers, sensors, connectors, and passive components"
            },
            {
                "name": "Mechanical Components",
                "description": "Mechanical parts and components for assembly and manufacturing",
                "meta_title": "Mechanical Components | Manufacturing Parts",
                "meta_description": "Bearings, gears, fasteners, springs, and other mechanical components"
            },
            {
                "name": "Raw Materials",
                "description": "Raw materials and base materials for manufacturing processes",
                "meta_title": "Raw Materials | Manufacturing Supplies",
                "meta_description": "Metals, plastics, composites, and chemicals for manufacturing"
            },
            {
                "name": "Fabrication Materials",
                "description": "Materials ready for fabrication and machining operations",
                "meta_title": "Fabrication Materials | Sheet Metal & Profiles",
                "meta_description": "Sheet metal, extrusions, tubes, pipes, and wire materials"
            },
            {
                "name": "Assembly Hardware",
                "description": "Hardware components for product assembly and fastening",
                "meta_title": "Assembly Hardware | Screws, Bolts, Fasteners",
                "meta_description": "Screws, bolts, nuts, washers, rivets, and mounting hardware"
            },
            {
                "name": "Hydraulic & Pneumatic Components",
                "description": "Hydraulic and pneumatic system components for industrial applications",
                "meta_title": "Hydraulic & Pneumatic Components",
                "meta_description": "Valves, cylinders, fittings, hoses, pumps, and motors"
            }
        ]
        
        for idx, cat_info in enumerate(main_category_data):
            try:
                category = create_category(db, CategoryCreate(
                    name=cat_info["name"],
                    description=cat_info["description"],
                    meta_title=cat_info["meta_title"],
                    meta_description=cat_info["meta_description"],
                    sort_order=idx + 1,
                    is_active=True
                ))
                main_categories[cat_info["name"]] = category
                print(f"  ✓ Created main category: {cat_info['name']}")
            except ValueError as e:
                from app.db.models.category import Category
                existing = db.query(Category).filter(Category.name == cat_info["name"]).first()
                if existing:
                    main_categories[cat_info["name"]] = existing
                    print(f"  ⚠ Main category already exists: {cat_info['name']}")
                else:
                    print(f"  ✗ Error creating category {cat_info['name']}: {e}")
        
        # Create Subcategories
        print("\n📁 Creating subcategories...")
        subcategories = {}
        
        subcategory_data = [
            # Electronic Components subcategories
            {"name": "Microcontrollers & Processors", "parent": "Electronic Components"},
            {"name": "Sensors & Actuators", "parent": "Electronic Components"},
            {"name": "Connectors & Cables", "parent": "Electronic Components"},
            {"name": "Passive Components", "parent": "Electronic Components"},
            {"name": "PCBs & Circuit Boards", "parent": "Electronic Components"},
            
            # Mechanical Components subcategories
            {"name": "Bearings & Bushings", "parent": "Mechanical Components"},
            {"name": "Gears & Sprockets", "parent": "Mechanical Components"},
            {"name": "Fasteners & Hardware", "parent": "Mechanical Components"},
            {"name": "Springs & Dampers", "parent": "Mechanical Components"},
            {"name": "Shafts & Couplings", "parent": "Mechanical Components"},
            
            # Raw Materials subcategories
            {"name": "Metals & Alloys", "parent": "Raw Materials"},
            {"name": "Plastics & Polymers", "parent": "Raw Materials"},
            {"name": "Composites & Laminates", "parent": "Raw Materials"},
            {"name": "Chemicals & Adhesives", "parent": "Raw Materials"},
            
            # Fabrication Materials subcategories
            {"name": "Sheet Metal", "parent": "Fabrication Materials"},
            {"name": "Profiles & Extrusions", "parent": "Fabrication Materials"},
            {"name": "Tubes & Pipes", "parent": "Fabrication Materials"},
            {"name": "Wire & Cable", "parent": "Fabrication Materials"},
            
            # Assembly Hardware subcategories
            {"name": "Screws & Bolts", "parent": "Assembly Hardware"},
            {"name": "Nuts & Washers", "parent": "Assembly Hardware"},
            {"name": "Rivets & Pins", "parent": "Assembly Hardware"},
            {"name": "Brackets & Mounts", "parent": "Assembly Hardware"},
            
            # Hydraulic & Pneumatic subcategories
            {"name": "Valves", "parent": "Hydraulic & Pneumatic Components"},
            {"name": "Cylinders", "parent": "Hydraulic & Pneumatic Components"},
            {"name": "Fittings & Hoses", "parent": "Hydraulic & Pneumatic Components"},
            {"name": "Pumps & Motors", "parent": "Hydraulic & Pneumatic Components"}
        ]
        
        for idx, subcat_info in enumerate(subcategory_data):
            try:
                parent = main_categories.get(subcat_info["parent"])
                if not parent:
                    print(f"  ⚠ Skipping subcategory {subcat_info['name']} - parent not found")
                    continue
                    
                category = create_category(db, CategoryCreate(
                    name=subcat_info["name"],
                    description=f"{subcat_info['name']} for manufacturing",
                    parent_id=parent.id,
                    sort_order=idx + 1,
                    is_active=True
                ))
                subcategories[subcat_info["name"]] = category
                print(f"  ✓ Created subcategory: {subcat_info['name']}")
            except ValueError as e:
                from app.db.models.category import Category
                existing = db.query(Category).filter(Category.name == subcat_info["name"]).first()
                if existing:
                    subcategories[subcat_info["name"]] = existing
                    print(f"  ⚠ Subcategory already exists: {subcat_info['name']}")
                else:
                    print(f"  ✗ Error creating subcategory {subcat_info['name']}: {e}")
        
        # Combine all categories
        all_categories = {**main_categories, **subcategories}
        
        # Create Tags
        print("\n🏷️  Creating tags...")
        tags = {}
        
        tag_data = [
            {"name": "Bulk Available", "color": "#4ECDC4", "description": "Available in bulk quantities"},
            {"name": "Customizable", "color": "#45B7D1", "description": "Custom specifications available"},
            {"name": "OEM Compatible", "color": "#96CEB4", "description": "OEM compatible components"},
            {"name": "ISO Certified", "color": "#FFEAA7", "description": "ISO certified quality"},
            {"name": "Fast Lead Time", "color": "#DDA15E", "description": "Fast shipping and delivery"},
            {"name": "MOQ Available", "color": "#C9ADA7", "description": "Low minimum order quantity"},
            {"name": "Made in USA", "color": "#9A8C98", "description": "Manufactured in the USA"},
            {"name": "Made in China", "color": "#FF6B6B", "description": "Manufactured in China"},
            {"name": "RoHS Compliant", "color": "#A8E6CF", "description": "RoHS compliant materials"},
            {"name": "CE Certified", "color": "#FFD3A5", "description": "CE certified products"},
            {"name": "Custom Specifications", "color": "#FD9853", "description": "Custom specs available"},
            {"name": "Stock Item", "color": "#A8DADC", "description": "In stock, ready to ship"}
        ]
        
        for idx, tag_info in enumerate(tag_data):
            try:
                tag = create_tag(db, TagCreate(
                    name=tag_info["name"],
                    description=tag_info["description"],
                    color=tag_info["color"],
                    is_active=True,
                    sort_order=idx + 1
                ))
                tags[tag_info["name"]] = tag
                print(f"  ✓ Created tag: {tag_info['name']}")
            except ValueError as e:
                from app.db.models.tag import Tag
                existing = db.query(Tag).filter(Tag.name == tag_info["name"]).first()
                if existing:
                    tags[tag_info["name"]] = existing
                    print(f"  ⚠ Tag already exists: {tag_info['name']}")
                else:
                    print(f"  ✗ Error creating tag {tag_info['name']}: {e}")
        
        # Create Products
        print("\n📦 Creating products...")
        
        products_data = [
            # Electronic Components
            {
                "name": "ESP32 Development Board - WiFi & Bluetooth",
                "description": "ESP32 microcontroller development board with integrated WiFi and Bluetooth. Perfect for IoT applications and embedded systems.",
                "brand": "Espressif Systems",
                "category": "Microcontrollers & Processors",
                "price": Decimal("8.50"),
                "compare_at_price": Decimal("12.00"),
                "cost_price": Decimal("5.20"),
                "sku": "ESP32-DEV-V1",
                "stock_quantity": 2500,
                "status": ProductStatus.PUBLISHED,
                "is_featured": True,
                "tags": ["Bulk Available", "OEM Compatible", "RoHS Compliant", "Stock Item", "Made in China"],
                "specifications": {
                    "Microcontroller": "ESP32-D0WDQ6",
                    "WiFi": "802.11 b/g/n",
                    "Bluetooth": "Bluetooth 4.2",
                    "CPU": "Dual-core 32-bit",
                    "Flash": "4MB",
                    "Operating Voltage": "3.3V",
                    "GPIO Pins": "30"
                },
                "weight": Decimal("0.025"),
                "dimensions": {"length": "52", "width": "27", "height": "3"},
                "variants": [
                    {"name": "ESP32 DevKit V1", "sku": "ESP32-DEV-V1", "price": Decimal("8.50"), "stockQuantity": 1500},
                    {"name": "ESP32 DevKit V2", "sku": "ESP32-DEV-V2", "price": Decimal("9.50"), "stockQuantity": 1000}
                ]
            },
            {
                "name": "DS18B20 Temperature Sensor - Waterproof",
                "description": "Digital temperature sensor with waterproof probe. 1-Wire interface, -55°C to +125°C range.",
                "brand": "Maxim Integrated",
                "category": "Sensors & Actuators",
                "price": Decimal("3.25"),
                "compare_at_price": Decimal("4.50"),
                "cost_price": Decimal("1.80"),
                "sku": "DS18B20-WP",
                "stock_quantity": 5000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in China", "RoHS Compliant"],
                "specifications": {
                    "Temperature Range": "-55°C to +125°C",
                    "Accuracy": "±0.5°C",
                    "Resolution": "9-12 bit selectable",
                    "Interface": "1-Wire",
                    "Supply Voltage": "3.0V to 5.5V",
                    "Probe Length": "1 meter"
                },
                "weight": Decimal("0.015"),
                "dimensions": {"length": "6", "width": "15", "height": "4"},
                "variants": [
                    {"name": "1m Cable", "sku": "DS18B20-WP-1M", "price": Decimal("3.25"), "stockQuantity": 3000},
                    {"name": "2m Cable", "sku": "DS18B20-WP-2M", "price": Decimal("3.75"), "stockQuantity": 2000}
                ]
            },
            {
                "name": "USB Type-C Connector - 24 Pin SMT",
                "description": "Surface mount USB Type-C connector, 24-pin configuration. Supports USB 3.1 Gen 2 and USB Power Delivery.",
                "brand": "Amphenol",
                "category": "Connectors & Cables",
                "price": Decimal("1.85"),
                "compare_at_price": Decimal("2.50"),
                "cost_price": Decimal("0.95"),
                "sku": "USB-C-24PIN-SMT",
                "stock_quantity": 10000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "OEM Compatible", "RoHS Compliant", "Stock Item", "Made in China"],
                "specifications": {
                    "Connector Type": "USB Type-C",
                    "Pin Count": "24 pins",
                    "Mounting": "Surface Mount",
                    "Current Rating": "5A",
                    "Voltage Rating": "20V",
                    "Data Rate": "10 Gbps",
                    "RoHS": "Compliant"
                },
                "weight": Decimal("0.002"),
                "dimensions": {"length": "8.5", "width": "3.5", "height": "3.0"},
                "variants": [
                    {"name": "Standard", "sku": "USB-C-24PIN-STD", "price": Decimal("1.85"), "stockQuantity": 6000},
                    {"name": "Reversible", "sku": "USB-C-24PIN-REV", "price": Decimal("2.15"), "stockQuantity": 4000}
                ]
            },
            {
                "name": "Ceramic Capacitor - 100nF 50V X7R",
                "description": "Multilayer ceramic capacitor, 100nF capacitance, 50V rating, X7R dielectric. 0805 package.",
                "brand": "Murata",
                "category": "Passive Components",
                "price": Decimal("0.12"),
                "compare_at_price": Decimal("0.18"),
                "cost_price": Decimal("0.06"),
                "sku": "CAP-100NF-50V-X7R",
                "stock_quantity": 50000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in China", "RoHS Compliant", "MOQ Available"],
                "specifications": {
                    "Capacitance": "100nF",
                    "Voltage Rating": "50V",
                    "Dielectric": "X7R",
                    "Package": "0805",
                    "Tolerance": "±10%",
                    "Temperature Range": "-55°C to +125°C"
                },
                "weight": Decimal("0.0001"),
                "dimensions": {"length": "2.0", "width": "1.25", "height": "0.8"},
                "variants": [
                    {"name": "0805 Package", "sku": "CAP-100NF-0805", "price": Decimal("0.12"), "stockQuantity": 30000},
                    {"name": "0603 Package", "sku": "CAP-100NF-0603", "price": Decimal("0.10"), "stockQuantity": 20000}
                ]
            },
            {
                "name": "Custom PCB - 2 Layer FR4",
                "description": "Custom printed circuit board, 2-layer FR4 substrate. Standard thickness 1.6mm. Minimum order 10 pieces.",
                "brand": "PCBWay",
                "category": "PCBs & Circuit Boards",
                "price": Decimal("25.00"),
                "compare_at_price": Decimal("35.00"),
                "cost_price": Decimal("15.00"),
                "sku": "PCB-2LAYER-FR4",
                "stock_quantity": 0,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Customizable", "Custom Specifications", "MOQ Available", "Made in China"],
                "specifications": {
                    "Layers": "2",
                    "Material": "FR4",
                    "Thickness": "1.6mm",
                    "Copper Weight": "1oz",
                    "Minimum Order": "10 pieces",
                    "Lead Time": "5-7 days",
                    "Surface Finish": "HASL"
                },
                "weight": Decimal("0.050"),
                "dimensions": {"length": "100", "width": "100", "height": "1.6"},
                "variants": [
                    {"name": "10cm x 10cm", "sku": "PCB-2L-10X10", "price": Decimal("25.00"), "stockQuantity": 0},
                    {"name": "5cm x 5cm", "sku": "PCB-2L-5X5", "price": Decimal("12.00"), "stockQuantity": 0}
                ]
            },
            
            # Mechanical Components
            {
                "name": "Deep Groove Ball Bearing - 6205-2RS",
                "description": "Sealed deep groove ball bearing, 25mm ID x 52mm OD x 15mm width. Double rubber seals.",
                "brand": "SKF",
                "category": "Bearings & Bushings",
                "price": Decimal("12.50"),
                "compare_at_price": Decimal("18.00"),
                "cost_price": Decimal("8.20"),
                "sku": "BEARING-6205-2RS",
                "stock_quantity": 1500,
                "status": ProductStatus.PUBLISHED,
                "is_featured": True,
                "tags": ["Bulk Available", "ISO Certified", "Stock Item", "Made in China"],
                "specifications": {
                    "Inner Diameter": "25mm",
                    "Outer Diameter": "52mm",
                    "Width": "15mm",
                    "Seals": "Double rubber seals (2RS)",
                    "Dynamic Load Rating": "14.0 kN",
                    "Static Load Rating": "6.95 kN",
                    "Max Speed": "12,000 rpm"
                },
                "weight": Decimal("0.130"),
                "dimensions": {"length": "52", "width": "52", "height": "15"},
                "variants": [
                    {"name": "6205-2RS", "sku": "BRG-6205-2RS", "price": Decimal("12.50"), "stockQuantity": 800},
                    {"name": "6205-ZZ (Metal Shield)", "sku": "BRG-6205-ZZ", "price": Decimal("11.00"), "stockQuantity": 700}
                ]
            },
            {
                "name": "Timing Belt - GT2 2mm Pitch",
                "description": "GT2 timing belt, 2mm pitch, fiberglass reinforced. Available in various lengths.",
                "brand": "Gates",
                "category": "Gears & Sprockets",
                "price": Decimal("8.50"),
                "compare_at_price": Decimal("12.00"),
                "cost_price": Decimal("5.50"),
                "sku": "BELT-GT2-2MM",
                "stock_quantity": 500,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Pitch": "2mm",
                    "Type": "GT2",
                    "Width": "6mm",
                    "Material": "Fiberglass reinforced",
                    "Temperature Range": "-30°C to +85°C",
                    "Standard Lengths": "100mm to 2000mm"
                },
                "weight": Decimal("0.050"),
                "dimensions": {"length": "1000", "width": "6", "height": "2"},
                "variants": [
                    {"name": "100mm Length", "sku": "BELT-GT2-100", "price": Decimal("2.50"), "stockQuantity": 200},
                    {"name": "500mm Length", "sku": "BELT-GT2-500", "price": Decimal("8.50"), "stockQuantity": 150},
                    {"name": "1000mm Length", "sku": "BELT-GT2-1000", "price": Decimal("15.00"), "stockQuantity": 150}
                ]
            },
            {
                "name": "Metric Hex Screw - M3 x 20mm",
                "description": "Stainless steel metric hex head screw, M3 thread, 20mm length. A2-70 grade.",
                "brand": "Fastenal",
                "category": "Fasteners & Hardware",
                "price": Decimal("0.15"),
                "compare_at_price": Decimal("0.25"),
                "cost_price": Decimal("0.08"),
                "sku": "SCREW-M3-20",
                "stock_quantity": 50000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "MOQ Available", "Made in China"],
                "specifications": {
                    "Thread": "M3",
                    "Length": "20mm",
                    "Head Type": "Hex",
                    "Material": "Stainless Steel A2-70",
                    "Finish": "Natural",
                    "Drive": "Hex socket"
                },
                "weight": Decimal("0.001"),
                "dimensions": {"length": "20", "width": "5.5", "height": "5.5"},
                "variants": [
                    {"name": "M3 x 10mm", "sku": "SCREW-M3-10", "price": Decimal("0.12"), "stockQuantity": 20000},
                    {"name": "M3 x 20mm", "sku": "SCREW-M3-20", "price": Decimal("0.15"), "stockQuantity": 15000},
                    {"name": "M3 x 30mm", "sku": "SCREW-M3-30", "price": Decimal("0.18"), "stockQuantity": 15000}
                ]
            },
            {
                "name": "Compression Spring - 10mm OD x 50mm",
                "description": "Stainless steel compression spring, 10mm outer diameter, 50mm free length.",
                "brand": "Lee Spring",
                "category": "Springs & Dampers",
                "price": Decimal("2.50"),
                "compare_at_price": Decimal("3.50"),
                "cost_price": Decimal("1.50"),
                "sku": "SPRING-COMP-10X50",
                "stock_quantity": 2000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Type": "Compression",
                    "Outer Diameter": "10mm",
                    "Free Length": "50mm",
                    "Wire Diameter": "1.0mm",
                    "Material": "Stainless Steel 302",
                    "Spring Rate": "0.5 N/mm"
                },
                "weight": Decimal("0.005"),
                "dimensions": {"length": "50", "width": "10", "height": "10"},
                "variants": [
                    {"name": "10mm OD x 30mm", "sku": "SPRING-10X30", "price": Decimal("1.80"), "stockQuantity": 800},
                    {"name": "10mm OD x 50mm", "sku": "SPRING-10X50", "price": Decimal("2.50"), "stockQuantity": 600},
                    {"name": "10mm OD x 70mm", "sku": "SPRING-10X70", "price": Decimal("3.20"), "stockQuantity": 600}
                ]
            },
            {
                "name": "Flexible Shaft Coupling - 6mm",
                "description": "Flexible shaft coupling, 6mm bore diameter. Nylon body with aluminum hubs.",
                "brand": "Lovejoy",
                "category": "Shafts & Couplings",
                "price": Decimal("8.75"),
                "compare_at_price": Decimal("12.00"),
                "cost_price": Decimal("5.50"),
                "sku": "COUPLING-FLEX-6MM",
                "stock_quantity": 800,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Bore Diameter": "6mm",
                    "Type": "Flexible",
                    "Body Material": "Nylon",
                    "Hub Material": "Aluminum",
                    "Max Torque": "2.5 Nm",
                    "Max Speed": "6000 rpm"
                },
                "weight": Decimal("0.025"),
                "dimensions": {"length": "25", "width": "25", "height": "20"},
                "variants": [
                    {"name": "6mm Bore", "sku": "COUP-FLEX-6", "price": Decimal("8.75"), "stockQuantity": 300},
                    {"name": "8mm Bore", "sku": "COUP-FLEX-8", "price": Decimal("10.50"), "stockQuantity": 250},
                    {"name": "10mm Bore", "sku": "COUP-FLEX-10", "price": Decimal("12.25"), "stockQuantity": 250}
                ]
            },
            
            # Raw Materials
            {
                "name": "Stainless Steel Sheet - 304 Grade 2mm",
                "description": "304 stainless steel sheet, 2mm thickness. Cold rolled finish. Perfect for fabrication.",
                "brand": "MetalWorks Supply",
                "category": "Metals & Alloys",
                "price": Decimal("125.00"),
                "compare_at_price": Decimal("145.00"),
                "cost_price": Decimal("95.00"),
                "sku": "SS-304-SHEET-2MM",
                "stock_quantity": 200,
                "status": ProductStatus.PUBLISHED,
                "is_featured": True,
                "tags": ["Bulk Available", "Stock Item", "Made in USA", "ISO Certified"],
                "specifications": {
                    "Grade": "304 Stainless Steel",
                    "Thickness": "2mm",
                    "Finish": "2B Cold Rolled",
                    "Standard": "ASTM A240",
                    "Width": "1000mm",
                    "Length": "2000mm",
                    "Corrosion Resistance": "Excellent"
                },
                "weight": Decimal("15.70"),
                "dimensions": {"length": "2000", "width": "1000", "height": "2"},
                "variants": [
                    {"name": "1m x 2m Sheet", "sku": "SS-304-1X2", "price": Decimal("125.00"), "stockQuantity": 100},
                    {"name": "1.5m x 3m Sheet", "sku": "SS-304-1.5X3", "price": Decimal("280.00"), "stockQuantity": 50},
                    {"name": "2m x 4m Sheet", "sku": "SS-304-2X4", "price": Decimal("500.00"), "stockQuantity": 50}
                ]
            },
            {
                "name": "ABS Plastic Pellets - Natural",
                "description": "ABS (Acrylonitrile Butadiene Styrene) plastic pellets, natural color. Injection molding grade.",
                "brand": "SABIC",
                "category": "Plastics & Polymers",
                "price": Decimal("2.25"),
                "compare_at_price": Decimal("2.75"),
                "cost_price": Decimal("1.50"),
                "sku": "ABS-PELLETS-NAT",
                "stock_quantity": 10000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "MOQ Available", "Made in China"],
                "specifications": {
                    "Material": "ABS",
                    "Color": "Natural",
                    "Grade": "Injection Molding",
                    "Melt Flow Index": "22 g/10min",
                    "Tensile Strength": "45 MPa",
                    "Density": "1.04 g/cm³",
                    "Packaging": "25kg bags"
                },
                "weight": Decimal("25.00"),
                "dimensions": {"length": "50", "width": "50", "height": "80"},
                "variants": [
                    {"name": "25kg Bag", "sku": "ABS-25KG", "price": Decimal("56.25"), "stockQuantity": 400},
                    {"name": "500kg Pallet", "sku": "ABS-500KG", "price": Decimal("1125.00"), "stockQuantity": 20}
                ]
            },
            {
                "name": "Carbon Fiber Sheet - 3K Twill",
                "description": "Carbon fiber sheet, 3K twill weave, 0.5mm thickness. High strength-to-weight ratio.",
                "brand": "Toray Industries",
                "category": "Composites & Laminates",
                "price": Decimal("85.00"),
                "compare_at_price": Decimal("110.00"),
                "cost_price": Decimal("60.00"),
                "sku": "CF-SHEET-3K-0.5MM",
                "stock_quantity": 150,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in Japan", "Customizable"],
                "specifications": {
                    "Weave": "3K Twill",
                    "Thickness": "0.5mm",
                    "Fiber Type": "T700",
                    "Resin": "Epoxy",
                    "Width": "1000mm",
                    "Length": "2000mm",
                    "Tensile Strength": "4900 MPa"
                },
                "weight": Decimal("0.75"),
                "dimensions": {"length": "2000", "width": "1000", "height": "0.5"},
                "variants": [
                    {"name": "0.5mm Thickness", "sku": "CF-3K-0.5", "price": Decimal("85.00"), "stockQuantity": 80},
                    {"name": "1.0mm Thickness", "sku": "CF-3K-1.0", "price": Decimal("165.00"), "stockQuantity": 70}
                ]
            },
            {
                "name": "Epoxy Adhesive - Two Part",
                "description": "High-strength two-part epoxy adhesive. 1:1 mixing ratio. 5-minute work time.",
                "brand": "Loctite",
                "category": "Chemicals & Adhesives",
                "price": Decimal("12.50"),
                "compare_at_price": Decimal("18.00"),
                "cost_price": Decimal("7.50"),
                "sku": "EPOXY-2PART-50ML",
                "stock_quantity": 500,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Type": "Two-part epoxy",
                    "Mix Ratio": "1:1",
                    "Work Time": "5 minutes",
                    "Cure Time": "24 hours",
                    "Tensile Strength": "25 MPa",
                    "Temperature Range": "-40°C to +120°C",
                    "Volume": "50ml"
                },
                "weight": Decimal("0.060"),
                "dimensions": {"length": "15", "width": "5", "height": "10"},
                "variants": [
                    {"name": "50ml", "sku": "EPOXY-50ML", "price": Decimal("12.50"), "stockQuantity": 300},
                    {"name": "250ml", "sku": "EPOXY-250ML", "price": Decimal("45.00"), "stockQuantity": 200}
                ]
            },
            
            # Fabrication Materials
            {
                "name": "Aluminum Extrusion Profile - 20x20mm",
                "description": "Aluminum extrusion profile, 20x20mm cross-section, 6061-T6 alloy. 1 meter length.",
                "brand": "AlumTech Supply",
                "category": "Profiles & Extrusions",
                "price": Decimal("8.50"),
                "compare_at_price": Decimal("12.00"),
                "cost_price": Decimal("5.50"),
                "sku": "ALUM-20X20-1M",
                "stock_quantity": 2000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": True,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Alloy": "6061-T6",
                    "Cross Section": "20mm x 20mm",
                    "Length": "1 meter",
                    "Finish": "Mill finish",
                    "Standard": "ASTM B221",
                    "Weight": "0.27 kg/m"
                },
                "weight": Decimal("0.27"),
                "dimensions": {"length": "1000", "width": "20", "height": "20"},
                "variants": [
                    {"name": "1m Length", "sku": "ALUM-20X20-1M", "price": Decimal("8.50"), "stockQuantity": 1000},
                    {"name": "2m Length", "sku": "ALUM-20X20-2M", "price": Decimal("16.00"), "stockQuantity": 500},
                    {"name": "3m Length", "sku": "ALUM-20X20-3M", "price": Decimal("23.50"), "stockQuantity": 500}
                ]
            },
            {
                "name": "Steel Tube - 25mm OD x 2mm Wall",
                "description": "Carbon steel tube, 25mm outer diameter, 2mm wall thickness. Seamless construction.",
                "brand": "SteelTube Co",
                "category": "Tubes & Pipes",
                "price": Decimal("15.00"),
                "compare_at_price": Decimal("20.00"),
                "cost_price": Decimal("10.00"),
                "sku": "TUBE-STEEL-25X2",
                "stock_quantity": 800,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Material": "Carbon Steel",
                    "Outer Diameter": "25mm",
                    "Wall Thickness": "2mm",
                    "Inner Diameter": "21mm",
                    "Length": "6 meters",
                    "Standard": "ASTM A106",
                    "Finish": "Black"
                },
                "weight": Decimal("3.40"),
                "dimensions": {"length": "6000", "width": "25", "height": "25"},
                "variants": [
                    {"name": "3m Length", "sku": "TUBE-25X2-3M", "price": Decimal("7.50"), "stockQuantity": 400},
                    {"name": "6m Length", "sku": "TUBE-25X2-6M", "price": Decimal("15.00"), "stockQuantity": 400}
                ]
            },
            {
                "name": "Copper Wire - 12 AWG Stranded",
                "description": "Stranded copper wire, 12 AWG gauge. THHN insulation. 100ft spool.",
                "brand": "Southwire",
                "category": "Wire & Cable",
                "price": Decimal("45.00"),
                "compare_at_price": Decimal("60.00"),
                "cost_price": Decimal("30.00"),
                "sku": "WIRE-CU-12AWG-100FT",
                "stock_quantity": 200,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Gauge": "12 AWG",
                    "Conductor": "Stranded copper",
                    "Insulation": "THHN",
                    "Voltage Rating": "600V",
                    "Temperature Rating": "90°C",
                    "Length": "100 feet",
                    "Color": "Black"
                },
                "weight": Decimal("1.50"),
                "dimensions": {"length": "30500", "width": "10", "height": "10"},
                "variants": [
                    {"name": "100ft Black", "sku": "WIRE-12AWG-BLK", "price": Decimal("45.00"), "stockQuantity": 100},
                    {"name": "100ft Red", "sku": "WIRE-12AWG-RED", "price": Decimal("45.00"), "stockQuantity": 50},
                    {"name": "100ft White", "sku": "WIRE-12AWG-WHT", "price": Decimal("45.00"), "stockQuantity": 50}
                ]
            },
            
            # Assembly Hardware
            {
                "name": "Hex Nut - M3 Stainless Steel",
                "description": "Stainless steel hex nut, M3 thread. A2-70 grade. Bulk packaging.",
                "brand": "Fastenal",
                "category": "Nuts & Washers",
                "price": Decimal("0.08"),
                "compare_at_price": Decimal("0.15"),
                "cost_price": Decimal("0.04"),
                "sku": "NUT-M3-SS",
                "stock_quantity": 100000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "MOQ Available", "Made in China"],
                "specifications": {
                    "Thread": "M3",
                    "Material": "Stainless Steel A2-70",
                    "Width": "5.5mm",
                    "Height": "2.4mm",
                    "Finish": "Natural",
                    "Packaging": "Bulk"
                },
                "weight": Decimal("0.0005"),
                "dimensions": {"length": "5.5", "width": "5.5", "height": "2.4"},
                "variants": [
                    {"name": "M3 Standard", "sku": "NUT-M3-STD", "price": Decimal("0.08"), "stockQuantity": 50000},
                    {"name": "M3 Nylon", "sku": "NUT-M3-NYL", "price": Decimal("0.12"), "stockQuantity": 30000},
                    {"name": "M3 Lock Nut", "sku": "NUT-M3-LOCK", "price": Decimal("0.15"), "stockQuantity": 20000}
                ]
            },
            {
                "name": "Pop Rivet - 3.2mm x 10mm",
                "description": "Aluminum pop rivet, 3.2mm diameter, 10mm grip range. Blind rivet for sheet metal.",
                "brand": "GESIPA",
                "category": "Rivets & Pins",
                "price": Decimal("0.25"),
                "compare_at_price": Decimal("0.35"),
                "cost_price": Decimal("0.15"),
                "sku": "RIVET-POP-3.2X10",
                "stock_quantity": 10000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in Germany"],
                "specifications": {
                    "Type": "Pop Rivet",
                    "Diameter": "3.2mm",
                    "Grip Range": "0.5-10mm",
                    "Material": "Aluminum",
                    "Head Type": "Dome",
                    "Color": "Natural"
                },
                "weight": Decimal("0.001"),
                "dimensions": {"length": "10", "width": "3.2", "height": "3.2"},
                "variants": [
                    {"name": "3.2mm x 6mm", "sku": "RIVET-3.2X6", "price": Decimal("0.22"), "stockQuantity": 4000},
                    {"name": "3.2mm x 10mm", "sku": "RIVET-3.2X10", "price": Decimal("0.25"), "stockQuantity": 3000},
                    {"name": "3.2mm x 16mm", "sku": "RIVET-3.2X16", "price": Decimal("0.28"), "stockQuantity": 3000}
                ]
            },
            {
                "name": "L-Bracket - 50x50x3mm",
                "description": "Steel L-bracket, 50mm x 50mm, 3mm thickness. Pre-drilled mounting holes.",
                "brand": "Hardware Supply Co",
                "category": "Brackets & Mounts",
                "price": Decimal("2.50"),
                "compare_at_price": Decimal("3.50"),
                "cost_price": Decimal("1.50"),
                "sku": "BRACKET-L-50X50",
                "stock_quantity": 2000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in China"],
                "specifications": {
                    "Type": "L-Bracket",
                    "Dimensions": "50mm x 50mm",
                    "Thickness": "3mm",
                    "Material": "Steel",
                    "Finish": "Zinc plated",
                    "Holes": "2 x M4"
                },
                "weight": Decimal("0.025"),
                "dimensions": {"length": "50", "width": "50", "height": "3"},
                "variants": [
                    {"name": "30x30x2mm", "sku": "BRACKET-30X30", "price": Decimal("1.25"), "stockQuantity": 800},
                    {"name": "50x50x3mm", "sku": "BRACKET-50X50", "price": Decimal("2.50"), "stockQuantity": 600},
                    {"name": "75x75x4mm", "sku": "BRACKET-75X75", "price": Decimal("4.50"), "stockQuantity": 600}
                ]
            },
            
            # Hydraulic & Pneumatic Components
            {
                "name": "Solenoid Valve - 2-Way 12V DC",
                "description": "2-way solenoid valve, 12V DC, normally closed. 1/4 inch NPT ports.",
                "brand": "ASCO",
                "category": "Valves",
                "price": Decimal("45.00"),
                "compare_at_price": Decimal("65.00"),
                "cost_price": Decimal("28.00"),
                "sku": "VALVE-SOL-2WAY-12V",
                "stock_quantity": 300,
                "status": ProductStatus.PUBLISHED,
                "is_featured": True,
                "tags": ["Bulk Available", "Stock Item", "CE Certified", "Made in USA"],
                "specifications": {
                    "Type": "2-Way Solenoid",
                    "Voltage": "12V DC",
                    "Port Size": "1/4 inch NPT",
                    "Flow Rate": "25 L/min",
                    "Max Pressure": "10 bar",
                    "Body Material": "Brass",
                    "Seal Material": "NBR"
                },
                "weight": Decimal("0.350"),
                "dimensions": {"length": "60", "width": "40", "height": "50"},
                "variants": [
                    {"name": "12V DC NC", "sku": "VALVE-12V-NC", "price": Decimal("45.00"), "stockQuantity": 150},
                    {"name": "24V DC NC", "sku": "VALVE-24V-NC", "price": Decimal("48.00"), "stockQuantity": 100},
                    {"name": "12V DC NO", "sku": "VALVE-12V-NO", "price": Decimal("46.00"), "stockQuantity": 50}
                ]
            },
            {
                "name": "Pneumatic Cylinder - 32mm Bore x 100mm Stroke",
                "description": "Double-acting pneumatic cylinder, 32mm bore, 100mm stroke. Cushioned ends.",
                "brand": "Festo",
                "category": "Cylinders",
                "price": Decimal("85.00"),
                "compare_at_price": Decimal("120.00"),
                "cost_price": Decimal("55.00"),
                "sku": "CYL-PNEU-32X100",
                "stock_quantity": 200,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "CE Certified", "Made in Germany"],
                "specifications": {
                    "Type": "Double-acting",
                    "Bore": "32mm",
                    "Stroke": "100mm",
                    "Max Pressure": "10 bar",
                    "Port Size": "M5",
                    "Cushioning": "Both ends",
                    "Mounting": "Threaded rod"
                },
                "weight": Decimal("0.850"),
                "dimensions": {"length": "150", "width": "32", "height": "32"},
                "variants": [
                    {"name": "32mm x 50mm", "sku": "CYL-32X50", "price": Decimal("65.00"), "stockQuantity": 80},
                    {"name": "32mm x 100mm", "sku": "CYL-32X100", "price": Decimal("85.00"), "stockQuantity": 60},
                    {"name": "32mm x 200mm", "sku": "CYL-32X200", "price": Decimal("110.00"), "stockQuantity": 60}
                ]
            },
            {
                "name": "Quick Connect Fitting - 1/4 inch",
                "description": "Quick connect pneumatic fitting, 1/4 inch NPT thread. Push-to-connect design.",
                "brand": "SMC",
                "category": "Fittings & Hoses",
                "price": Decimal("3.50"),
                "compare_at_price": Decimal("5.00"),
                "cost_price": Decimal("2.00"),
                "sku": "FITTING-QC-1/4",
                "stock_quantity": 1500,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in Japan"],
                "specifications": {
                    "Type": "Quick Connect",
                    "Thread": "1/4 inch NPT",
                    "Tube OD": "6mm",
                    "Material": "Brass",
                    "Max Pressure": "1.0 MPa",
                    "Temperature Range": "-5°C to +60°C"
                },
                "weight": Decimal("0.015"),
                "dimensions": {"length": "25", "width": "15", "height": "15"},
                "variants": [
                    {"name": "1/8 inch", "sku": "FITTING-QC-1/8", "price": Decimal("2.50"), "stockQuantity": 600},
                    {"name": "1/4 inch", "sku": "FITTING-QC-1/4", "price": Decimal("3.50"), "stockQuantity": 500},
                    {"name": "3/8 inch", "sku": "FITTING-QC-3/8", "price": Decimal("4.50"), "stockQuantity": 400}
                ]
            },
            {
                "name": "Gear Pump - 0.5 GPM",
                "description": "External gear pump, 0.5 GPM flow rate. 12V DC motor. For hydraulic applications.",
                "brand": "Parker",
                "category": "Pumps & Motors",
                "price": Decimal("285.00"),
                "compare_at_price": Decimal("380.00"),
                "cost_price": Decimal("180.00"),
                "sku": "PUMP-GEAR-0.5GPM",
                "stock_quantity": 50,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Type": "External Gear Pump",
                    "Flow Rate": "0.5 GPM",
                    "Max Pressure": "2000 PSI",
                    "Motor": "12V DC",
                    "Port Size": "1/4 inch NPT",
                    "Displacement": "0.25 cu in/rev"
                },
                "weight": Decimal("2.50"),
                "dimensions": {"length": "150", "width": "100", "height": "120"},
                "variants": [
                    {"name": "0.5 GPM", "sku": "PUMP-0.5GPM", "price": Decimal("285.00"), "stockQuantity": 25},
                    {"name": "1.0 GPM", "sku": "PUMP-1.0GPM", "price": Decimal("350.00"), "stockQuantity": 15},
                    {"name": "2.0 GPM", "sku": "PUMP-2.0GPM", "price": Decimal("450.00"), "stockQuantity": 10}
                ]
            },
            
            # Additional Electronic Components
            {
                "name": "Arduino Nano - ATmega328P",
                "description": "Arduino Nano development board with ATmega328P microcontroller. Compact form factor for embedded projects.",
                "brand": "Arduino",
                "category": "Microcontrollers & Processors",
                "price": Decimal("22.00"),
                "compare_at_price": Decimal("30.00"),
                "cost_price": Decimal("12.00"),
                "sku": "ARDUINO-NANO",
                "stock_quantity": 800,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "OEM Compatible", "Stock Item", "Made in Italy"],
                "specifications": {
                    "Microcontroller": "ATmega328P",
                    "Operating Voltage": "5V",
                    "Digital I/O": "14 pins",
                    "Analog Input": "8 pins",
                    "Flash Memory": "32 KB",
                    "Clock Speed": "16 MHz"
                },
                "weight": Decimal("0.007"),
                "dimensions": {"length": "45", "width": "18", "height": "3"},
                "variants": [
                    {"name": "Standard", "sku": "ARDUINO-NANO-STD", "price": Decimal("22.00"), "stockQuantity": 500},
                    {"name": "With Headers", "sku": "ARDUINO-NANO-HDR", "price": Decimal("25.00"), "stockQuantity": 300}
                ]
            },
            {
                "name": "HC-SR04 Ultrasonic Sensor",
                "description": "Ultrasonic distance sensor, 2-400cm range. 4-pin interface, 5V operation.",
                "brand": "Generic",
                "category": "Sensors & Actuators",
                "price": Decimal("2.50"),
                "compare_at_price": Decimal("4.00"),
                "cost_price": Decimal("1.20"),
                "sku": "SENSOR-HC-SR04",
                "stock_quantity": 3000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in China"],
                "specifications": {
                    "Range": "2-400 cm",
                    "Accuracy": "3mm",
                    "Operating Voltage": "5V",
                    "Current": "15mA",
                    "Frequency": "40 kHz",
                    "Interface": "4-pin"
                },
                "weight": Decimal("0.010"),
                "dimensions": {"length": "45", "width": "20", "height": "15"},
                "variants": [
                    {"name": "Standard", "sku": "HC-SR04-STD", "price": Decimal("2.50"), "stockQuantity": 2000},
                    {"name": "Waterproof", "sku": "HC-SR04-WP", "price": Decimal("4.50"), "stockQuantity": 1000}
                ]
            },
            {
                "name": "JST-XH Connector - 2 Pin",
                "description": "JST-XH connector, 2-pin configuration. 2.54mm pitch. Male and female available.",
                "brand": "JST",
                "category": "Connectors & Cables",
                "price": Decimal("0.35"),
                "compare_at_price": Decimal("0.50"),
                "cost_price": Decimal("0.18"),
                "sku": "JST-XH-2PIN",
                "stock_quantity": 20000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "MOQ Available", "Made in Japan"],
                "specifications": {
                    "Type": "JST-XH",
                    "Pin Count": "2",
                    "Pitch": "2.54mm",
                    "Current Rating": "3A",
                    "Voltage Rating": "250V",
                    "Wire Gauge": "22-28 AWG"
                },
                "weight": Decimal("0.001"),
                "dimensions": {"length": "8", "width": "5", "height": "8"},
                "variants": [
                    {"name": "2 Pin Male", "sku": "JST-XH-2M", "price": Decimal("0.35"), "stockQuantity": 10000},
                    {"name": "2 Pin Female", "sku": "JST-XH-2F", "price": Decimal("0.35"), "stockQuantity": 10000}
                ]
            },
            {
                "name": "Resistor - 1K Ohm 1/4W",
                "description": "Carbon film resistor, 1K ohm, 1/4W power rating. 5% tolerance. Through-hole package.",
                "brand": "Yageo",
                "category": "Passive Components",
                "price": Decimal("0.02"),
                "compare_at_price": Decimal("0.05"),
                "cost_price": Decimal("0.01"),
                "sku": "RES-1K-1/4W",
                "stock_quantity": 100000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "MOQ Available", "Made in China"],
                "specifications": {
                    "Resistance": "1K ohm",
                    "Power Rating": "1/4W",
                    "Tolerance": "±5%",
                    "Type": "Carbon Film",
                    "Package": "Through-hole",
                    "Temperature Coefficient": "±200 ppm/°C"
                },
                "weight": Decimal("0.0001"),
                "dimensions": {"length": "6.3", "width": "2.5", "height": "2.5"},
                "variants": [
                    {"name": "1K ohm", "sku": "RES-1K", "price": Decimal("0.02"), "stockQuantity": 40000},
                    {"name": "10K ohm", "sku": "RES-10K", "price": Decimal("0.02"), "stockQuantity": 30000},
                    {"name": "100K ohm", "sku": "RES-100K", "price": Decimal("0.02"), "stockQuantity": 30000}
                ]
            },
            
            # Additional Mechanical Components
            {
                "name": "Linear Ball Bearing - LM8UU",
                "description": "Linear ball bearing, 8mm inner diameter. For smooth linear motion applications.",
                "brand": "IGUS",
                "category": "Bearings & Bushings",
                "price": Decimal("4.50"),
                "compare_at_price": Decimal("7.00"),
                "cost_price": Decimal("2.50"),
                "sku": "BEARING-LM8UU",
                "stock_quantity": 2000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in Germany"],
                "specifications": {
                    "Type": "Linear Ball Bearing",
                    "Inner Diameter": "8mm",
                    "Outer Diameter": "15mm",
                    "Length": "24mm",
                    "Load Capacity": "200N",
                    "Material": "Steel"
                },
                "weight": Decimal("0.015"),
                "dimensions": {"length": "24", "width": "15", "height": "15"},
                "variants": [
                    {"name": "LM8UU", "sku": "LM8UU", "price": Decimal("4.50"), "stockQuantity": 800},
                    {"name": "LM10UU", "sku": "LM10UU", "price": Decimal("5.50"), "stockQuantity": 600},
                    {"name": "LM12UU", "sku": "LM12UU", "price": Decimal("6.50"), "stockQuantity": 600}
                ]
            },
            {
                "name": "Spur Gear - Module 1, 20 Teeth",
                "description": "Steel spur gear, module 1, 20 teeth. 6mm bore diameter. For precision gear trains.",
                "brand": "SDP-SI",
                "category": "Gears & Sprockets",
                "price": Decimal("3.25"),
                "compare_at_price": Decimal("5.00"),
                "cost_price": Decimal("1.80"),
                "sku": "GEAR-SPUR-M1-20T",
                "stock_quantity": 1500,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Type": "Spur Gear",
                    "Module": "1",
                    "Teeth": "20",
                    "Bore Diameter": "6mm",
                    "Material": "Steel",
                    "Pressure Angle": "20°"
                },
                "weight": Decimal("0.010"),
                "dimensions": {"length": "22", "width": "22", "height": "5"},
                "variants": [
                    {"name": "20 Teeth", "sku": "GEAR-M1-20T", "price": Decimal("3.25"), "stockQuantity": 500},
                    {"name": "30 Teeth", "sku": "GEAR-M1-30T", "price": Decimal("4.50"), "stockQuantity": 500},
                    {"name": "40 Teeth", "sku": "GEAR-M1-40T", "price": Decimal("5.75"), "stockQuantity": 500}
                ]
            },
            {
                "name": "Flat Washer - M3 Stainless Steel",
                "description": "Stainless steel flat washer, M3 size. A2-70 grade. Standard thickness.",
                "brand": "Fastenal",
                "category": "Nuts & Washers",
                "price": Decimal("0.05"),
                "compare_at_price": Decimal("0.10"),
                "cost_price": Decimal("0.025"),
                "sku": "WASHER-FLAT-M3",
                "stock_quantity": 50000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "MOQ Available", "Made in China"],
                "specifications": {
                    "Type": "Flat Washer",
                    "Size": "M3",
                    "Material": "Stainless Steel A2-70",
                    "Outer Diameter": "7mm",
                    "Inner Diameter": "3.2mm",
                    "Thickness": "0.5mm"
                },
                "weight": Decimal("0.0002"),
                "dimensions": {"length": "7", "width": "7", "height": "0.5"},
                "variants": [
                    {"name": "M3 Standard", "sku": "WASHER-M3", "price": Decimal("0.05"), "stockQuantity": 25000},
                    {"name": "M4 Standard", "sku": "WASHER-M4", "price": Decimal("0.06"), "stockQuantity": 15000},
                    {"name": "M5 Standard", "sku": "WASHER-M5", "price": Decimal("0.08"), "stockQuantity": 10000}
                ]
            },
            {
                "name": "Torsion Spring - 5mm OD",
                "description": "Stainless steel torsion spring, 5mm outer diameter. For rotational applications.",
                "brand": "Lee Spring",
                "category": "Springs & Dampers",
                "price": Decimal("1.85"),
                "compare_at_price": Decimal("2.75"),
                "cost_price": Decimal("1.10"),
                "sku": "SPRING-TORSION-5MM",
                "stock_quantity": 1500,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Type": "Torsion Spring",
                    "Outer Diameter": "5mm",
                    "Wire Diameter": "0.5mm",
                    "Material": "Stainless Steel 302",
                    "Coils": "10",
                    "Torque": "0.1 Nm"
                },
                "weight": Decimal("0.003"),
                "dimensions": {"length": "15", "width": "5", "height": "5"},
                "variants": [
                    {"name": "5mm OD", "sku": "SPRING-TOR-5", "price": Decimal("1.85"), "stockQuantity": 600},
                    {"name": "8mm OD", "sku": "SPRING-TOR-8", "price": Decimal("2.50"), "stockQuantity": 500},
                    {"name": "10mm OD", "sku": "SPRING-TOR-10", "price": Decimal("3.25"), "stockQuantity": 400}
                ]
            },
            
            # Additional Raw Materials
            {
                "name": "Aluminum Sheet - 6061-T6 3mm",
                "description": "6061-T6 aluminum sheet, 3mm thickness. Mill finish. Perfect for machining and fabrication.",
                "brand": "MetalWorks Supply",
                "category": "Metals & Alloys",
                "price": Decimal("85.00"),
                "compare_at_price": Decimal("105.00"),
                "cost_price": Decimal("60.00"),
                "sku": "ALUM-SHEET-6061-3MM",
                "stock_quantity": 150,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Alloy": "6061-T6",
                    "Thickness": "3mm",
                    "Finish": "Mill finish",
                    "Width": "1000mm",
                    "Length": "2000mm",
                    "Standard": "ASTM B209"
                },
                "weight": Decimal("8.10"),
                "dimensions": {"length": "2000", "width": "1000", "height": "3"},
                "variants": [
                    {"name": "1m x 2m", "sku": "ALUM-SHEET-1X2", "price": Decimal("85.00"), "stockQuantity": 80},
                    {"name": "1.5m x 3m", "sku": "ALUM-SHEET-1.5X3", "price": Decimal("190.00"), "stockQuantity": 70}
                ]
            },
            {
                "name": "Polycarbonate Sheet - 3mm Clear",
                "description": "Clear polycarbonate sheet, 3mm thickness. Impact resistant, UV protected.",
                "brand": "SABIC",
                "category": "Plastics & Polymers",
                "price": Decimal("45.00"),
                "compare_at_price": Decimal("60.00"),
                "cost_price": Decimal("30.00"),
                "sku": "PC-SHEET-3MM-CLR",
                "stock_quantity": 300,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Material": "Polycarbonate",
                    "Thickness": "3mm",
                    "Color": "Clear",
                    "Width": "1000mm",
                    "Length": "2000mm",
                    "Impact Resistance": "High",
                    "UV Protection": "Yes"
                },
                "weight": Decimal("3.60"),
                "dimensions": {"length": "2000", "width": "1000", "height": "3"},
                "variants": [
                    {"name": "3mm Clear", "sku": "PC-3MM-CLR", "price": Decimal("45.00"), "stockQuantity": 150},
                    {"name": "5mm Clear", "sku": "PC-5MM-CLR", "price": Decimal("75.00"), "stockQuantity": 150}
                ]
            },
            {
                "name": "Fiberglass Cloth - 200gsm",
                "description": "Fiberglass cloth, 200gsm weight. Plain weave. For composite layup applications.",
                "brand": "Fiberglass Supply",
                "category": "Composites & Laminates",
                "price": Decimal("12.50"),
                "compare_at_price": Decimal("18.00"),
                "cost_price": Decimal("8.00"),
                "sku": "FG-CLOTH-200GSM",
                "stock_quantity": 500,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Type": "Fiberglass Cloth",
                    "Weight": "200 gsm",
                    "Weave": "Plain",
                    "Width": "1000mm",
                    "Length": "50 meters",
                    "Thickness": "0.2mm"
                },
                "weight": Decimal("10.00"),
                "dimensions": {"length": "50000", "width": "1000", "height": "0.2"},
                "variants": [
                    {"name": "200gsm", "sku": "FG-200GSM", "price": Decimal("12.50"), "stockQuantity": 250},
                    {"name": "300gsm", "sku": "FG-300GSM", "price": Decimal("18.00"), "stockQuantity": 250}
                ]
            },
            {
                "name": "Cyanoacrylate Adhesive - Super Glue",
                "description": "Fast-curing cyanoacrylate adhesive. 10g tube. Bonds most materials in seconds.",
                "brand": "Loctite",
                "category": "Chemicals & Adhesives",
                "price": Decimal("4.50"),
                "compare_at_price": Decimal("6.50"),
                "cost_price": Decimal("2.50"),
                "sku": "ADHESIVE-CA-10G",
                "stock_quantity": 1000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Type": "Cyanoacrylate",
                    "Volume": "10g",
                    "Cure Time": "10-30 seconds",
                    "Bond Strength": "High",
                    "Temperature Range": "-40°C to +82°C",
                    "Viscosity": "Low"
                },
                "weight": Decimal("0.015"),
                "dimensions": {"length": "10", "width": "2", "height": "2"},
                "variants": [
                    {"name": "10g Tube", "sku": "CA-10G", "price": Decimal("4.50"), "stockQuantity": 600},
                    {"name": "20g Tube", "sku": "CA-20G", "price": Decimal("7.50"), "stockQuantity": 400}
                ]
            },
            
            # Additional Fabrication Materials
            {
                "name": "Steel Sheet - 1.5mm Cold Rolled",
                "description": "Cold rolled steel sheet, 1.5mm thickness. SPCC grade. Mill finish.",
                "brand": "SteelWorks Supply",
                "category": "Sheet Metal",
                "price": Decimal("35.00"),
                "compare_at_price": Decimal("45.00"),
                "cost_price": Decimal("25.00"),
                "sku": "STEEL-SHEET-1.5MM",
                "stock_quantity": 400,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Material": "Cold Rolled Steel",
                    "Grade": "SPCC",
                    "Thickness": "1.5mm",
                    "Width": "1000mm",
                    "Length": "2000mm",
                    "Finish": "Mill finish"
                },
                "weight": Decimal("11.78"),
                "dimensions": {"length": "2000", "width": "1000", "height": "1.5"},
                "variants": [
                    {"name": "1m x 2m", "sku": "STEEL-1X2", "price": Decimal("35.00"), "stockQuantity": 200},
                    {"name": "1.5m x 3m", "sku": "STEEL-1.5X3", "price": Decimal("78.75"), "stockQuantity": 200}
                ]
            },
            {
                "name": "Aluminum Tube - 25mm OD x 2mm Wall",
                "description": "6061-T6 aluminum tube, 25mm outer diameter, 2mm wall thickness. 3 meter length.",
                "brand": "AlumTech Supply",
                "category": "Tubes & Pipes",
                "price": Decimal("18.50"),
                "compare_at_price": Decimal("25.00"),
                "cost_price": Decimal("12.00"),
                "sku": "ALUM-TUBE-25X2",
                "stock_quantity": 600,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Material": "6061-T6 Aluminum",
                    "Outer Diameter": "25mm",
                    "Wall Thickness": "2mm",
                    "Inner Diameter": "21mm",
                    "Length": "3 meters",
                    "Standard": "ASTM B210"
                },
                "weight": Decimal("1.15"),
                "dimensions": {"length": "3000", "width": "25", "height": "25"},
                "variants": [
                    {"name": "3m Length", "sku": "ALUM-TUBE-3M", "price": Decimal("18.50"), "stockQuantity": 300},
                    {"name": "6m Length", "sku": "ALUM-TUBE-6M", "price": Decimal("35.00"), "stockQuantity": 300}
                ]
            },
            {
                "name": "Multi-Strand Wire - 18 AWG",
                "description": "Multi-strand copper wire, 18 AWG gauge. PVC insulation. 100ft spool.",
                "brand": "Southwire",
                "category": "Wire & Cable",
                "price": Decimal("28.00"),
                "compare_at_price": Decimal("38.00"),
                "cost_price": Decimal("18.00"),
                "sku": "WIRE-18AWG-100FT",
                "stock_quantity": 300,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Gauge": "18 AWG",
                    "Conductor": "Multi-strand copper",
                    "Insulation": "PVC",
                    "Voltage Rating": "300V",
                    "Temperature Rating": "60°C",
                    "Length": "100 feet",
                    "Strand Count": "16"
                },
                "weight": Decimal("0.75"),
                "dimensions": {"length": "30500", "width": "8", "height": "8"},
                "variants": [
                    {"name": "18 AWG Red", "sku": "WIRE-18AWG-RED", "price": Decimal("28.00"), "stockQuantity": 100},
                    {"name": "18 AWG Black", "sku": "WIRE-18AWG-BLK", "price": Decimal("28.00"), "stockQuantity": 100},
                    {"name": "18 AWG White", "sku": "WIRE-18AWG-WHT", "price": Decimal("28.00"), "stockQuantity": 100}
                ]
            },
            
            # Additional Assembly Hardware
            {
                "name": "Socket Head Cap Screw - M4 x 20mm",
                "description": "Stainless steel socket head cap screw, M4 thread, 20mm length. A2-70 grade.",
                "brand": "Fastenal",
                "category": "Screws & Bolts",
                "price": Decimal("0.35"),
                "compare_at_price": Decimal("0.55"),
                "cost_price": Decimal("0.18"),
                "sku": "SCREW-SHCS-M4-20",
                "stock_quantity": 25000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "MOQ Available", "Made in China"],
                "specifications": {
                    "Type": "Socket Head Cap Screw",
                    "Thread": "M4",
                    "Length": "20mm",
                    "Material": "Stainless Steel A2-70",
                    "Head Type": "Socket",
                    "Drive": "Hex socket"
                },
                "weight": Decimal("0.002"),
                "dimensions": {"length": "20", "width": "7", "height": "7"},
                "variants": [
                    {"name": "M4 x 10mm", "sku": "SHCS-M4-10", "price": Decimal("0.30"), "stockQuantity": 10000},
                    {"name": "M4 x 20mm", "sku": "SHCS-M4-20", "price": Decimal("0.35"), "stockQuantity": 8000},
                    {"name": "M4 x 30mm", "sku": "SHCS-M4-30", "price": Decimal("0.40"), "stockQuantity": 7000}
                ]
            },
            {
                "name": "Spring Pin - 3mm x 20mm",
                "description": "Spring pin (roll pin), 3mm diameter, 20mm length. Carbon steel, zinc plated.",
                "brand": "Hardware Supply Co",
                "category": "Rivets & Pins",
                "price": Decimal("0.15"),
                "compare_at_price": Decimal("0.25"),
                "cost_price": Decimal("0.08"),
                "sku": "PIN-SPRING-3X20",
                "stock_quantity": 15000,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "MOQ Available", "Made in China"],
                "specifications": {
                    "Type": "Spring Pin",
                    "Diameter": "3mm",
                    "Length": "20mm",
                    "Material": "Carbon Steel",
                    "Finish": "Zinc plated",
                    "Standard": "DIN 1481"
                },
                "weight": Decimal("0.001"),
                "dimensions": {"length": "20", "width": "3", "height": "3"},
                "variants": [
                    {"name": "3mm x 15mm", "sku": "PIN-3X15", "price": Decimal("0.12"), "stockQuantity": 6000},
                    {"name": "3mm x 20mm", "sku": "PIN-3X20", "price": Decimal("0.15"), "stockQuantity": 5000},
                    {"name": "3mm x 25mm", "sku": "PIN-3X25", "price": Decimal("0.18"), "stockQuantity": 4000}
                ]
            },
            {
                "name": "Corner Bracket - 50x50x3mm",
                "description": "Steel corner bracket, 50mm x 50mm, 3mm thickness. Pre-drilled mounting holes.",
                "brand": "Hardware Supply Co",
                "category": "Brackets & Mounts",
                "price": Decimal("3.25"),
                "compare_at_price": Decimal("4.50"),
                "cost_price": Decimal("2.00"),
                "sku": "BRACKET-CORNER-50X50",
                "stock_quantity": 1500,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in China"],
                "specifications": {
                    "Type": "Corner Bracket",
                    "Dimensions": "50mm x 50mm",
                    "Thickness": "3mm",
                    "Material": "Steel",
                    "Finish": "Zinc plated",
                    "Holes": "2 x M4 per leg"
                },
                "weight": Decimal("0.030"),
                "dimensions": {"length": "50", "width": "50", "height": "3"},
                "variants": [
                    {"name": "30x30x2mm", "sku": "BRACKET-CORNER-30", "price": Decimal("1.75"), "stockQuantity": 600},
                    {"name": "50x50x3mm", "sku": "BRACKET-CORNER-50", "price": Decimal("3.25"), "stockQuantity": 500},
                    {"name": "75x75x4mm", "sku": "BRACKET-CORNER-75", "price": Decimal("5.50"), "stockQuantity": 400}
                ]
            },
            
            # Additional Hydraulic & Pneumatic Components
            {
                "name": "Ball Valve - 1/4 inch NPT",
                "description": "Brass ball valve, 1/4 inch NPT ports. Full port design. Manual operation.",
                "brand": "Parker",
                "category": "Valves",
                "price": Decimal("18.50"),
                "compare_at_price": Decimal("28.00"),
                "cost_price": Decimal("12.00"),
                "sku": "VALVE-BALL-1/4",
                "stock_quantity": 400,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Type": "Ball Valve",
                    "Port Size": "1/4 inch NPT",
                    "Material": "Brass",
                    "Max Pressure": "600 PSI",
                    "Temperature Range": "-20°C to +120°C",
                    "Operation": "Manual"
                },
                "weight": Decimal("0.150"),
                "dimensions": {"length": "50", "width": "30", "height": "50"},
                "variants": [
                    {"name": "1/4 inch", "sku": "VALVE-BALL-1/4", "price": Decimal("18.50"), "stockQuantity": 200},
                    {"name": "3/8 inch", "sku": "VALVE-BALL-3/8", "price": Decimal("22.00"), "stockQuantity": 100},
                    {"name": "1/2 inch", "sku": "VALVE-BALL-1/2", "price": Decimal("28.00"), "stockQuantity": 100}
                ]
            },
            {
                "name": "Hydraulic Cylinder - 40mm Bore x 100mm Stroke",
                "description": "Single-acting hydraulic cylinder, 40mm bore, 100mm stroke. 3000 PSI rating.",
                "brand": "Parker",
                "category": "Cylinders",
                "price": Decimal("185.00"),
                "compare_at_price": Decimal("250.00"),
                "cost_price": Decimal("120.00"),
                "sku": "CYL-HYD-40X100",
                "stock_quantity": 100,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Type": "Single-acting",
                    "Bore": "40mm",
                    "Stroke": "100mm",
                    "Max Pressure": "3000 PSI",
                    "Port Size": "1/4 inch NPT",
                    "Rod Diameter": "20mm"
                },
                "weight": Decimal("2.50"),
                "dimensions": {"length": "200", "width": "40", "height": "40"},
                "variants": [
                    {"name": "40mm x 50mm", "sku": "CYL-HYD-40X50", "price": Decimal("150.00"), "stockQuantity": 40},
                    {"name": "40mm x 100mm", "sku": "CYL-HYD-40X100", "price": Decimal("185.00"), "stockQuantity": 30},
                    {"name": "40mm x 200mm", "sku": "CYL-HYD-40X200", "price": Decimal("250.00"), "stockQuantity": 30}
                ]
            },
            {
                "name": "Pneumatic Hose - 6mm ID, 10m",
                "description": "Polyurethane pneumatic hose, 6mm inner diameter. 10 meter length. Flexible and durable.",
                "brand": "SMC",
                "category": "Fittings & Hoses",
                "price": Decimal("25.00"),
                "compare_at_price": Decimal("35.00"),
                "cost_price": Decimal("15.00"),
                "sku": "HOSE-PNEU-6MM-10M",
                "stock_quantity": 200,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in Japan"],
                "specifications": {
                    "Type": "Pneumatic Hose",
                    "Inner Diameter": "6mm",
                    "Outer Diameter": "10mm",
                    "Length": "10 meters",
                    "Material": "Polyurethane",
                    "Max Pressure": "1.0 MPa",
                    "Temperature Range": "-10°C to +60°C"
                },
                "weight": Decimal("0.50"),
                "dimensions": {"length": "10000", "width": "10", "height": "10"},
                "variants": [
                    {"name": "5m Length", "sku": "HOSE-6MM-5M", "price": Decimal("15.00"), "stockQuantity": 100},
                    {"name": "10m Length", "sku": "HOSE-6MM-10M", "price": Decimal("25.00"), "stockQuantity": 50},
                    {"name": "20m Length", "sku": "HOSE-6MM-20M", "price": Decimal("45.00"), "stockQuantity": 50}
                ]
            },
            {
                "name": "DC Gear Motor - 12V 30 RPM",
                "description": "12V DC gear motor, 30 RPM output speed. High torque. For automation applications.",
                "brand": "Pololu",
                "category": "Pumps & Motors",
                "price": Decimal("28.50"),
                "compare_at_price": Decimal("40.00"),
                "cost_price": Decimal("18.00"),
                "sku": "MOTOR-DC-12V-30RPM",
                "stock_quantity": 300,
                "status": ProductStatus.PUBLISHED,
                "is_featured": False,
                "tags": ["Bulk Available", "Stock Item", "Made in USA"],
                "specifications": {
                    "Type": "DC Gear Motor",
                    "Voltage": "12V DC",
                    "Speed": "30 RPM",
                    "Torque": "2.5 kg-cm",
                    "Current": "0.5A (no load)",
                    "Shaft Diameter": "6mm",
                    "Gear Ratio": "298:1"
                },
                "weight": Decimal("0.250"),
                "dimensions": {"length": "60", "width": "38", "height": "38"},
                "variants": [
                    {"name": "30 RPM", "sku": "MOTOR-30RPM", "price": Decimal("28.50"), "stockQuantity": 100},
                    {"name": "60 RPM", "sku": "MOTOR-60RPM", "price": Decimal("32.00"), "stockQuantity": 100},
                    {"name": "100 RPM", "sku": "MOTOR-100RPM", "price": Decimal("35.00"), "stockQuantity": 100}
                ]
            }
        ]
        
        products_created = 0
        for product_info in products_data:
            try:
                # Get category
                category = all_categories.get(product_info["category"])
                if not category:
                    print(f"  ⚠ Skipping product {product_info['name']} - category not found")
                    continue
                
                # Get tag IDs
                tag_ids = [tags[tag_name].id for tag_name in product_info["tags"] if tag_name in tags]
                
                # Create variants
                variants = [
                    {
                        "name": v["name"],
                        "sku": v["sku"],
                        "price": v["price"],
                        "stockQuantity": v["stockQuantity"],
                        "inStock": True
                    }
                    for v in product_info["variants"]
                ]
                
                product = create_product(db, ProductCreate(
                    name=product_info["name"],
                    description=product_info["description"],
                    brand=product_info["brand"],
                    category_id=category.id,
                    tags=tag_ids,
                    price=product_info["price"],
                    compare_at_price=product_info["compare_at_price"],
                    cost_price=product_info["cost_price"],
                    sku=product_info["sku"],
                    stock_quantity=product_info["stock_quantity"],
                    status=product_info["status"],
                    is_featured=product_info["is_featured"],
                    is_active=True,
                    specifications=product_info["specifications"],
                    weight=product_info["weight"],
                    dimensions=product_info["dimensions"],
                    variants=variants,
                    published_at=datetime.utcnow()
                ))
                products_created += 1
                print(f"  ✓ Created product: {product_info['name']}")
            except ValueError as e:
                print(f"  ✗ Error creating product {product_info['name']}: {e}")
            except Exception as e:
                print(f"  ✗ Unexpected error creating product {product_info['name']}: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n✅ Manufacturing component data seeding completed!")
        print(f"\n📊 Summary:")
        print(f"   - Main categories created: {len(main_categories)}")
        print(f"   - Subcategories created: {len(subcategories)}")
        print(f"   - Tags created: {len(tags)}")
        print(f"   - Products created: {products_created}")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_manufacturing_data()
