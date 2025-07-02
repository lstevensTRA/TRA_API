# TRA API Backend

## Label Studio Integration for Tax Form ML Training Pipeline

This project integrates [Label Studio](https://labelstud.io/) for annotation and ML training of tax form data. The workflow includes:
- Exporting documents and extractions from Supabase to Label Studio for annotation
- Importing completed annotations back into Supabase
- Keeping Label Studio and the database in sync for batch ML training

### Key Scripts
- `export_to_labelstudio.py`: Export documents/extractions to Label Studio format
- `import_from_labelstudio.py`: Import annotations from Label Studio API to Supabase
- `sync_training_data.py`: Sync Label Studio tasks and Supabase records

### Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run Label Studio: `label-studio start`
3. Configure Label Studio with the provided template for tax form field extraction
4. Use the integration scripts in `backend/scripts/` to manage data flow

See the documentation in `backend/scripts/` for details on each script and workflow.

A FastAPI-based backend service for TRA (Transportation Research Associates) data processing and API endpoints.

## Features

- **Health Check Endpoints**: Monitor service status and connectivity
- **Authentication Routes**: Secure API access management
- **Data Processing**: AT (Automated Traffic) and WI (Wisconsin) data services
- **PDF Utilities**: Document processing and manipulation
- **Playwright Integration**: Web scraping and automation capabilities
- **TPS Parser**: Transportation data parsing utilities

## Project Structure

```
backend/
├── app/
│   ├── models/          # Response models and data structures
│   ├── routes/          # API endpoints and routing
│   ├── services/        # Business logic and external service integrations
│   └── utils/           # Utility functions and helpers
├── server.py            # Main application entry point
├── requirements.txt     # Python dependencies
└── test_app.py         # Test suite
```

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- Git

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/lstevensTRA/TRA_API.git
   cd TRA_API/backend
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Configuration

Create a `.env` file in the backend directory with the following variables:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8001
DEBUG=True

# Database Configuration (if applicable)
DATABASE_URL=your_database_url_here

# API Keys and Secrets
API_KEY=your_api_key_here
SECRET_KEY=your_secret_key_here

# External Service URLs
AT_SERVICE_URL=your_at_service_url
WI_SERVICE_URL=your_wi_service_url
```

## Running the Application

### Development Mode
```bash
python server.py
```

### Production Mode
```bash
uvicorn server:app --host 0.0.0.0 --port 8001
```

The API will be available at `http://localhost:8001`

## API Endpoints

### Health Check
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health status

### Authentication
- `POST /auth/login` - User authentication
- `POST /auth/logout` - User logout
- `GET /auth/status` - Authentication status

### Data Services
- `GET /data/at` - AT (Automated Traffic) data
- `GET /data/wi` - WI (Wisconsin) data

## Testing

Run the test suite:
```bash
python test_app.py
```

## Development

### Adding New Routes
1. Create a new route file in `app/routes/`
2. Import and register the router in `server.py`
3. Add corresponding tests in `test_app.py`

### Adding New Services
1. Create a new service file in `app/services/`
2. Implement the business logic
3. Import and use in your routes

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary and confidential. All rights reserved.

## Support

For support and questions, please contact the development team or create an issue in the repository.

## CONSTRAINTS:
- Must use existing backend endpoints (no direct DB access)
- Connect to existing Supabase instance for data (via Supabase JS client)
- Use React (with functional components and hooks)
- Use Express proxy if needed for local development (to avoid CORS)
- Responsive, user-friendly UI
- (Optional) Auth integration with Supabase if enabled

## ENVIRONMENT SETUP:
- REACT_APP_API_URL=http://localhost:8000/api
- REACT_APP_SUPABASE_URL=https://your-project.supabase.co
- REACT_APP_SUPABASE_ANON_KEY=your-anon-key

## UI PREFERENCES:
- Use Tailwind CSS for styling
- Consider using shadcn/ui components
- Or: Use Material-UI / Ant Design / etc.

## ERROR HANDLING:
- Show loading states during API calls
- Display user-friendly error messages
- Handle network failures gracefully

**You can copy-paste this into Famous AI or any code generation tool to get a tailored React frontend for your ML training pipeline!**  
Let me know if you want to add/remove any details or need a more technical/less technical version. # Trigger deploy for TensorFlow fix
