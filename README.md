# Status Page API

A comprehensive multi-tenant status page API built with FastAPI, providing real-time incident management, service monitoring, and public status page functionality with WebSocket support.

## 🏗️ Architecture Overview
```
┌─────────────────────────────────────────────────────────────────┐
│ Client Applications                                             │
├─────────────────────────────────────────────────────────────────┤
│ Dashboard UI │ Public Status Page │ Mobile Apps │ APIs          │
└─────────────────┬───────────────────────┬───────────────────────┘
│ │
▼ ▼
┌─────────────────────────────────────────────────────────────────┐
│ FastAPI Application                                             │
├─────────────────────────────────────────────────────────────────┤
│ Authentication Middleware (Auth0) │ CORS │ WebSocket Manager    │
├─────────────────────────────────────────────────────────────────┤
│ Controllers (API Routes)                                        │
│ ┌─────────────┬─────────────┬─────────────┬─────────────────┐   │
│ │Organizations│ Services    │ Incidents   │ Public APIs     │   │
│ └─────────────┴─────────────┴─────────────┴─────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│ Service Layer                                                   │
│ ┌─────────────┬─────────────┬─────────────┬─────────────────┐   │
│ │ Service     │ Incident    │ Public      │ WebSocket       │   │
│ │ CRUD        │ CRUD        │ Service     │ Broadcasting    │   │
│ └─────────────┴─────────────┴─────────────┴─────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│ Data Access Layer                                               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ SQLAlchemy ORM Models                                       │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────┬───────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ PostgreSQL Database                                             │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Key Features

### Core Functionality
- **Multi-tenant Architecture**: Complete organization isolation with Auth0 integration
- **Service Monitoring**: Track multiple services with status management
- **Incident Management**: Create, update, and resolve incidents with impact levels
- **Real-time Updates**: WebSocket support for live status updates
- **Public Status Pages**: Public API endpoints for status page display
- **Status History**: Complete audit trail of service status changes
- **Uptime Calculations**: Service uptime tracking and reporting

### Security & Authentication
- **Auth0 Integration**: JWT-based authentication with organization isolation
- **CORS Support**: Configurable cross-origin resource sharing
- **Secure WebSockets**: Organization-scoped WebSocket connections
- **Multi-tenant Security**: Strict data isolation between organizations

### Real-time Features
- **WebSocket Manager**: Live incident and status updates
- **Background Tasks**: Asynchronous processing for status updates
- **Event Broadcasting**: Organization-specific event distribution

## 🛠️ Technologies & Libraries

### Core Framework
- **FastAPI**: Modern, fast web framework for building APIs
- **Uvicorn**: ASGI server for running the application
- **Pydantic**: Data validation and serialization
- **Starlette**: Lightweight ASGI framework (FastAPI dependency)

### Database & ORM
- **PostgreSQL**: Primary database with advanced features
- **SQLAlchemy**: Powerful ORM with relationship management
- **psycopg2-binary**: PostgreSQL adapter for Python

### Authentication & Security
- **Auth0**: Enterprise-grade authentication service
- **python-jose**: JWT token handling and validation
- **cryptography**: Cryptographic operations

### Real-time & Communication
- **WebSockets**: Real-time bidirectional communication
- **httpx**: Modern HTTP client for external API calls

### Development & Deployment
- **Docker**: Containerization for consistent deployment
- **Docker Compose**: Multi-service orchestration
- **python-dotenv**: Environment variable management
- **PyYAML**: YAML configuration support

## 📊 Database Schema
![](erDiagram.png)

### Entity Relationships

#### Organizations
- Central tenant entity for multi-tenancy
- Linked to Auth0 organization ID for authentication
- Contains all other entities through foreign keys

#### Users
- Authenticated users within organizations
- Linked to Auth0 user ID for identity management
- Can create incident updates and status history entries

#### Services
- Core entities being monitored
- Have current status and complete status history
- Can be affected by multiple incidents

#### Incidents
- Issues affecting one or more services
- Have status progression and impact levels
- Support multiple updates for resolution tracking

#### Status History
- Complete audit trail of service status changes
- Tracks who made changes and when
- Enables uptime calculations and reporting

## 🔧 Integration Mechanisms

### Auth0 Integration
```python
# JWT token validation with Auth0
- JWKS endpoint caching for performance
- Organization-scoped tokens
- User identity synchronization
- Multi-tenant token validation
```

### WebSocket Integration
```python
# Real-time updates per organization
- Organization-scoped connection management
- Broadcast incident updates
- Service status change notifications
- Connection lifecycle management
```

### Database Integration
```python
# PostgreSQL with SQLAlchemy ORM
- Connection pooling for performance
- Transaction management with context managers
- Relationship loading optimization
- Migration support through model definitions
```

## 🔄 API Architecture

### RESTful Endpoints

#### Organizations
- `GET /api/organizations` - List organizations
- Organization management and tenant setup

#### Services
- `GET /api/services` - List all services
- `POST /api/services` - Create new service
- `GET /api/services/{id}` - Get service details with history
- `PUT /api/services/{id}` - Update service information
- `PUT /api/services/{id}/status` - Update service status
- `DELETE /api/services/{id}` - Delete service
- `GET /api/services/{id}/uptime` - Get uptime statistics
- `GET /api/services/{id}/status-history` - Get status history

#### Incidents
- `GET /api/incidents` - List incidents with filtering
- `POST /api/incidents` - Create new incident
- `GET /api/incidents/{id}` - Get incident details
- `PUT /api/incidents/{id}` - Update incident
- `POST /api/incidents/{id}/updates` - Add incident update
- `PUT /api/incidents/{id}/resolve` - Resolve incident

#### Public APIs
- `GET /api/public/{org_name}/status` - Public status page data
- `GET /api/public/{org_name}/incidents` - Public incident history
- Public endpoints for status page display

### WebSocket Endpoints
- `WS /ws/{org_info}` - Organization-specific WebSocket connection
- Real-time updates for incidents and status changes

## 📋 Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (optional)
- Auth0 account and application setup

### Local Development Setup

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd statuspage-api
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Create a `.env` file in the project root:
   ```env
   # Environment
   ENVIRONMENT=LOCAL

   # Database
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/statuspage

   # Auth0 Configuration
   AUTH0_CLIENT_SECRET=your_auth0_client_secret
   AUTH0_DOMAIN=your_auth0_domain
   AUTH0_CLIENT_ID=your_auth0_client_id
   AUTH0_AUDIENCE=your_auth0_audience
   AUTH0_CLIENT_AUDIENCE=your_auth0_client_audience
   AUTH0_ALGORITHMS=RS256

   # Development Settings
   DEBUG=true
   CREATE_TABLES=true

   # CORS
   CORS_ORIGINS=["http://localhost:3000"]
   ```

5. **Database Setup**
   ```bash
   # Start PostgreSQL (if not using Docker)
   # Create database
   createdb statuspage

   # Or use Docker
   docker run --name postgres-statuspage -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=statuspage -p 5432:5432 -d postgres:15
   ```

6. **Auth0 Setup**
   - Create Auth0 Application (Single Page Application)
   - Create Auth0 API with identifier
   - Configure organization support in Auth0
   - Update `.env` with Auth0 credentials

7. **Run the Application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Docker Setup

1. **Using Docker Compose**
   ```bash
   # Build and start all services
   docker-compose up --build

   # Start in background
   docker-compose up -d
   ```

2. **Access the Application**
   - API: http://localhost:8000
   - Health Check: http://localhost:8000/api/healthcheck
   - API Documentation: http://localhost:8000/docs

### Production Deployment

1. **Environment Variables**
   ```env
   ENVIRONMENT=PROD
   DATABASE_URL=postgresql://user:password@host:port/database
   CREATE_TABLES=false
   DEBUG=false
   # ... other production configs
   ```

2. **Database Migration**
   ```bash
   # In production, handle migrations separately
   # Tables are auto-created only in LOCAL environment
   ```

3. **Security Considerations**
   - Use environment-specific Auth0 applications
   - Configure proper CORS origins
   - Enable HTTPS in production
   - Use connection pooling for database
   - Monitor WebSocket connections

### Testing

1. **Run Health Check**
   ```bash
   curl http://localhost:8000/api/healthcheck
   ```

2. **Test WebSocket Connection**
   ```javascript
   const ws = new WebSocket('ws://localhost:8000/ws/your_org_id');
   ```

3. **API Testing**
   - Use the interactive docs at `/docs`
   - Import the API collection into Postman
   - Test with proper Auth0 tokens

## 📚 Additional Information

### Performance Considerations
- Database connection pooling (50 connections)
- JWKS caching for Auth0 token validation
- Efficient WebSocket connection management
- Background task processing for status updates

### Monitoring & Observability
- Health check endpoint for monitoring
- Structured logging throughout the application
- Database query optimization with SQLAlchemy
- WebSocket connection tracking

### Scalability
- Multi-tenant architecture for horizontal scaling
- Stateless application design
- Background task queue support
- Database connection pooling
