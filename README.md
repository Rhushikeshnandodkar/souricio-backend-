# Sourcio Backend

FastAPI backend application for the Sourcio platform.

## Prerequisites

- Python 3.9 or higher
- PostgreSQL database
- pip or pipenv for package management
- **For PDF generation (WeasyPrint)**, system libraries are required:
  - **macOS**: Install via Homebrew: `brew install cairo pango gdk-pixbuf libffi glib gobject-introspection`
  - **Ubuntu/Debian**: `sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0 libgirepository1.0-dev`
  - **Fedora**: `sudo dnf install cairo pango gdk-pixbuf2 libffi gobject-introspection-devel`

## Setup

1. **Create a virtual environment** (if not already created):

```bash
python -m venv venv
```

2. **Activate the virtual environment**:

   - On macOS/Linux:

   ```bash
   source venv/bin/activate
   ```

   - On Windows:

   ```bash
   venv\Scripts\activate
   ```

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```

4. **Create a `.env` file** in the root directory with the following variables:

```env
APP_NAME=Sourcio Backend
APP_VERSION=1.0.0
DEBUG=True

# Database
DATABASE_URL=postgresql://username:password@localhost:5432/dbname

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# CORS (optional, defaults provided)
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]

# SMTP/Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@sourcio.com

# Company Information for PDF Quotes (optional)
COMPANY_NAME=Your Company Name
COMPANY_ADDRESS=Your Company Address
COMPANY_PHONE=+1234567890
COMPANY_EMAIL=contact@company.com
COMPANY_LOGO_URL=https://example.com/logo.png
COMPANY_TERMS_CONDITIONS=Your terms and conditions text

# Cloudinary (optional, for image uploads)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Redis (optional, for caching)
REDIS_URL=Upstack URL
```

## Running the Application

### Option 1: Using the run script (Recommended)

```bash
python run.py
```

### Option 2: Using uvicorn directly

```bash
uvicorn app.main:app --reload
```

The application will be available at `http://127.0.0.1:8000`

## API Documentation

Once the server is running, you can access:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **Health Check**: http://127.0.0.1:8000/health

## Project Structure

```
sourcio-backend/
├── app/
│   ├── api/           # API endpoints
│   ├── core/          # Core configuration
│   ├── db/            # Database models and setup
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic services
│   └── main.py        # FastAPI application entry point
├── migrations/        # Database migration scripts
├── run.py            # Application runner script
└── requirements.txt  # Python dependencies
```

## Notes

- The application automatically creates database tables on startup if they don't exist
- For macOS users, the `run.py` script includes special handling for WeasyPrint dependencies
- Make sure your PostgreSQL database is running before starting the application
"# souricio-backend-" 
