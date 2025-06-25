# TRA API Backend

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