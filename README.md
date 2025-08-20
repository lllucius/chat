# Chat API - Advanced AI Chatbot Backend Platform

A comprehensive AI chatbot backend API platform built with FastAPI, LangChain, LangGraph, PostgreSQL, and PGVector. This platform provides enterprise-grade conversational AI capabilities with advanced features like vector-based knowledge retrieval, conversation management, user profiles, and comprehensive analytics.

## 🚀 Features

### Core Chat Functionality
- **Real-time Chat**: Async chat endpoints with streaming support
- **Conversation Management**: Create, manage, and organize chat conversations
- **Message History**: Persistent message storage with full conversation context
- **Multiple LLM Support**: Configurable LLM models and parameters

### Advanced AI Capabilities
- **Vector Knowledge Base**: Upload and query documents using semantic search
- **Hybrid Search**: Combine vector similarity and keyword search
- **LangChain Integration**: Advanced prompt engineering and chain management
- **Conversation Memory**: Context-aware conversations with memory management
- **Tool Integration**: Extensible tool calling and function execution

### User & Profile Management
- **User Authentication**: JWT-based authentication with refresh tokens
- **Profile System**: Customizable LLM profiles with different settings
- **Prompt Templates**: Reusable prompt templates and workflows
- **Personalization**: User-specific settings and preferences

### Document Processing
- **Multi-format Support**: PDF, DOCX, TXT, Markdown document processing
- **Automatic Chunking**: Intelligent document chunking for optimal retrieval
- **Embedding Generation**: Automatic vector embedding creation
- **Version Control**: Document versioning and update tracking

### Analytics & Monitoring
- **Usage Analytics**: Comprehensive usage tracking and metrics
- **Performance Monitoring**: Response time and token usage analytics
- **Health Checks**: System health monitoring and readiness checks
- **Cost Tracking**: Token usage and cost estimation

### Enterprise Features
- **Rate Limiting**: Configurable rate limiting and quota management
- **Background Processing**: Async document processing and embedding generation
- **Streaming Responses**: Real-time response streaming
- **Comprehensive Logging**: Structured logging with request/response tracking

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   LangChain     │    │   PostgreSQL    │
│                 │    │   + LangGraph   │    │   + PGVector    │
│ • REST API      │────│                 │────│                 │
│ • WebSocket     │    │ • LLM Chains    │    │ • Vector Store  │
│ • Auth/Sessions │    │ • Tool Calling  │    │ • Conversations │
│ • File Upload   │    │ • Memory Mgmt   │    │ • Documents     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                    ┌─────────────────┐
                    │   CLI Tools     │
                    │                 │
                    │ • Chat Client   │
                    │ • Admin Tools   │
                    │ • DB Management │
                    └─────────────────┘
```

## 📋 Requirements

- Python 3.11+
- PostgreSQL 12+ with PGVector extension
- OpenAI API key (or compatible LLM API)
- 4GB+ RAM recommended
- 10GB+ storage for documents and embeddings

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd chat
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Set Up PostgreSQL with PGVector

```bash
# Install PostgreSQL and PGVector
# Ubuntu/Debian:
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo apt install postgresql-14-pgvector

# macOS (with Homebrew):
brew install postgresql pgvector

# Start PostgreSQL service
sudo systemctl start postgresql  # Linux
brew services start postgresql   # macOS
```

Create database and user:

```sql
-- Connect to PostgreSQL as superuser
sudo -u postgres psql

-- Create database and user
CREATE DATABASE chat_db;
CREATE USER chat_user WITH ENCRYPTED PASSWORD 'chat_password';
GRANT ALL PRIVILEGES ON DATABASE chat_db TO chat_user;

-- Enable PGVector extension
\c chat_db
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. Configuration

Copy the environment configuration:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Database
DATABASE_URL=postgresql+asyncpg://chat_user:chat_password@localhost:5432/chat_db

# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# Security
SECRET_KEY=your_secret_key_here_change_in_production

# Optional: Customize other settings
DEBUG=True
LOG_LEVEL=INFO
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
```

### 5. Initialize Database

```bash
# Initialize database tables
python -m cli.manage init-database

# Create a superuser account
python -m cli.manage create-superuser --username admin --email admin@example.com
```

## 🚀 Running the Application

### Development Server

```bash
# Run the development server
python -m cli.manage runserver --reload

# Or use uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Server

```bash
# Run with multiple workers
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000

# Or use gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Using Docker (Optional)

```bash
# Build and run with Docker
docker build -t chat-api .
docker run -p 8000:8000 --env-file .env chat-api
```

## 📖 API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

#### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user info

#### Chat
- `POST /api/v1/chat/message` - Send message and get response
- `POST /api/v1/chat/stream` - Stream chat response
- `GET /api/v1/chat/models` - Get available models

#### Conversations
- `POST /api/v1/conversations/` - Create conversation
- `GET /api/v1/conversations/` - List conversations
- `GET /api/v1/conversations/{id}` - Get conversation with messages

#### Documents
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents/` - List documents
- `GET /api/v1/documents/search` - Search documents

#### Analytics
- `GET /api/v1/analytics/summary` - Usage summary
- `GET /api/v1/analytics/usage` - Usage metrics over time

#### Health
- `GET /healthz` - Basic health check
- `GET /readyz` - Comprehensive readiness check
- `GET /metrics` - System metrics

## 🖥️ CLI Usage

### Interactive Chat Client

```bash
# Start interactive chat
python -m cli.chat_cli chat

# Register new user via CLI
python -m cli.chat_cli register
```

### Management Commands

```bash
# Check database status
python -m cli.manage check-database

# Show system statistics
python -m cli.manage show-stats

# Clean up old analytics
python -m cli.manage cleanup-analytics

# Show configuration
python -m cli.manage show-config
```

## 💻 Development

### Project Structure

```
chat/
├── app/                    # Main application
│   ├── api/               # API endpoints
│   │   ├── v1/           # API v1 routes
│   │   └── health.py     # Health checks
│   ├── core/             # Core utilities
│   │   ├── exceptions.py # Custom exceptions
│   │   ├── logging.py    # Logging setup
│   │   └── security.py   # Authentication
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   ├── utils/            # Utility functions
│   ├── config.py         # Configuration
│   ├── database.py       # Database setup
│   ├── dependencies.py   # Dependency injection
│   └── main.py           # FastAPI app
├── cli/                   # CLI tools
│   ├── chat_cli.py       # Interactive chat
│   └── manage.py         # Management commands
├── tests/                 # Test suite
├── alembic/              # Database migrations
├── requirements.txt      # Dependencies
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### Code Quality

```bash
# Format code
black app/ cli/ tests/

# Sort imports
isort app/ cli/ tests/

# Lint code
flake8 app/ cli/ tests/

# Type checking
mypy app/
```

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `False` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `SECRET_KEY` | JWT secret key | Required |
| `LLM_MODEL` | Default LLM model | `gpt-4` |
| `LLM_TEMPERATURE` | Default temperature | `0.7` |
| `MAX_FILE_SIZE_MB` | Max upload size | `50` |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Rate limit | `60` |

### LLM Profiles

Create custom LLM profiles with different settings:

```python
{
    "name": "Creative Writing",
    "model_name": "gpt-4",
    "temperature": 0.9,
    "max_tokens": 2048,
    "system_prompt": "You are a creative writing assistant...",
    "retrieval_enabled": True,
    "tools_enabled": True
}
```

## 📊 Monitoring & Analytics

### Metrics Collected
- Message count and token usage
- Response times and performance
- Document upload and access patterns
- User activity and engagement
- Error rates and system health

### Logging
- Structured JSON logging
- Request/response logging
- Error tracking with stack traces
- Performance metrics
- Security events

## 🔒 Security

### Authentication
- JWT tokens with refresh capability
- Secure password hashing (bcrypt)
- Rate limiting per user/IP
- CORS protection

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- Secure file upload handling

### Privacy
- User data isolation
- Document access controls
- Audit logging
- GDPR compliance helpers

## 🚀 Deployment

### Production Checklist

1. **Environment Setup**
   - [ ] Set `DEBUG=False`
   - [ ] Use strong `SECRET_KEY`
   - [ ] Configure production database
   - [ ] Set up SSL/TLS certificates

2. **Database**
   - [ ] Configure connection pooling
   - [ ] Set up database backups
   - [ ] Monitor database performance
   - [ ] Configure PGVector properly

3. **Security**
   - [ ] Enable rate limiting
   - [ ] Configure CORS origins
   - [ ] Set up firewall rules
   - [ ] Enable request logging

4. **Monitoring**
   - [ ] Set up health checks
   - [ ] Configure alerting
   - [ ] Monitor resource usage
   - [ ] Track error rates

### Scaling Considerations

- **Horizontal Scaling**: Run multiple app instances behind a load balancer
- **Database**: Use read replicas for analytics queries
- **Vector Storage**: Consider dedicated vector databases for large-scale deployments
- **Caching**: Add Redis for session and query caching
- **Background Processing**: Use Celery for heavy document processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation for new features
- Use type hints throughout
- Add docstrings to all functions/classes

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check this README and API docs
- **Issues**: Open GitHub issues for bugs and feature requests
- **Discord**: Join our community Discord server
- **Email**: Contact support@chat-api.com

## 🗺️ Roadmap

### Upcoming Features

- [ ] **Multi-modal Support**: Image and audio message support
- [ ] **Plugin System**: Custom tool and integration plugins
- [ ] **Team Collaboration**: Shared conversations and workspaces
- [ ] **Advanced Analytics**: ML-powered insights and recommendations
- [ ] **Mobile SDKs**: Native mobile app integration
- [ ] **Enterprise SSO**: SAML/OIDC integration
- [ ] **Data Export**: Full data export and migration tools
- [ ] **Custom Models**: Support for fine-tuned and local models

### Performance Improvements

- [ ] Caching layer for frequent queries
- [ ] Background processing optimization
- [ ] Database query optimization
- [ ] Vector search performance tuning

## 🙏 Acknowledgments

- **FastAPI**: High-performance web framework
- **LangChain**: LLM orchestration and tooling
- **PostgreSQL**: Reliable database foundation
- **PGVector**: Vector similarity search
- **OpenAI**: GPT models and embeddings
- **Rich**: Beautiful CLI interfaces
- **Pydantic**: Data validation and serialization

---

Built with ❤️ by the Chat API Team