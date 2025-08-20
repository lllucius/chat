# AI Chatbot Backend API

A comprehensive AI chatbot backend API built with FastAPI, LangChain, and LlamaIndex. This system provides advanced conversational AI capabilities with document knowledge integration, user management, and streaming responses.

## 🚀 Features

### Core Capabilities
- **Conversational AI**: Powered by OpenAI GPT models via LangChain
- **Document Intelligence**: Upload and query documents using LlamaIndex vector search
- **Streaming Responses**: Real-time message streaming for better UX
- **Conversation Memory**: Persistent conversation history and context
- **User Management**: JWT-based authentication and user profiles
- **Vector Search**: Semantic document search with similarity scoring

### API Features
- **RESTful API**: Full OpenAPI/Swagger documentation
- **Async Operations**: Built for high performance with async/await
- **Rate Limiting**: Built-in request throttling
- **CORS Support**: Configurable cross-origin resource sharing
- **Health Checks**: Kubernetes-ready liveness and readiness probes

### Developer Experience
- **CLI Tools**: Interactive chat and management interfaces
- **Docker Support**: Containerized deployment
- **Structured Logging**: JSON logging with correlation IDs
- **Type Safety**: Full type annotations and Pydantic validation
- **Testing**: Comprehensive test suite (coming soon)

## 📋 Requirements

- Python 3.9+
- PostgreSQL 12+ with pgvector extension
- OpenAI API key
- Docker and Docker Compose (optional)

## 🛠 Installation

### Option 1: Local Development

1. **Clone the repository**
```bash
git clone https://github.com/lllucius/chat.git
cd chat
```

2. **Install dependencies**
```bash
pip install -e .
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Set up PostgreSQL with pgvector**
```bash
# Install PostgreSQL and pgvector extension
# Create database: chatbot
# Update DATABASE_URL in .env
```

5. **Initialize database**
```bash
chat-manage init-database
```

6. **Create an admin user**
```bash
chat-manage create-admin --username admin --email admin@example.com --password yourpassword
```

7. **Start the API server**
```bash
python -m uvicorn chat.main:app --reload
```

### Option 2: Docker Compose

1. **Clone and configure**
```bash
git clone https://github.com/lllucius/chat.git
cd chat
cp .env.example .env
# Set your OPENAI_API_KEY in .env
```

2. **Start services**
```bash
docker-compose up -d
```

3. **Initialize database**
```bash
docker-compose exec api chat-manage init-database
docker-compose exec api chat-manage create-admin --username admin --email admin@example.com --password yourpassword
```

## 🔧 Configuration

Key environment variables in `.env`:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7

# Database Configuration
DATABASE_URL=postgresql://chatbot:chatbot@localhost:5432/chatbot

# Authentication
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Document Processing
MAX_FILE_SIZE=10485760  # 10MB
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

## 📚 API Usage

### Authentication

1. **Register a new user**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com", 
    "password": "secure_password"
  }'
```

2. **Login**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "secure_password"
  }'
```

### Chat API

1. **Send a message**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how can you help me today?"
  }'
```

2. **Stream a conversation**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/stream" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about artificial intelligence"
  }'
```

### Document Management

1. **Upload a document**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

2. **Search documents**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/search" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning algorithms",
    "limit": 5
  }'
```

## 🖥 CLI Usage

### Interactive Chat

Start an interactive chat session:
```bash
# Login first
chat-cli login --username your_username --password your_password

# Start chatting
chat-cli chat
```

### Management Commands

```bash
# Initialize database
chat-manage init-database

# Create admin user
chat-manage create-admin --username admin --email admin@example.com

# List users
chat-manage list-users

# Show system statistics
chat-manage stats

# Export data
chat-manage export-data --output ./backup

# Show configuration
chat-manage config
```

## 🏗 Architecture

### Project Structure
```
src/chat/
├── __init__.py
├── main.py                 # FastAPI application
├── config/
│   ├── __init__.py
│   └── settings.py         # Configuration management
├── core/
│   ├── __init__.py
│   ├── database.py         # Database setup
│   ├── logging.py          # Structured logging
│   └── security.py         # Authentication utilities
├── models/
│   ├── __init__.py
│   ├── user.py            # User models
│   ├── chat.py            # Chat/conversation models
│   └── documents.py       # Document models
├── services/
│   ├── __init__.py
│   ├── auth_service.py     # Authentication service
│   ├── llm_service.py      # LangChain LLM service
│   ├── vector_store_service.py  # LlamaIndex vector store
│   └── document_service.py # Document processing
├── api/
│   ├── __init__.py
│   ├── dependencies.py     # FastAPI dependencies
│   └── routes/
│       ├── __init__.py
│       ├── auth.py         # Authentication routes
│       ├── chat.py         # Chat routes
│       ├── documents.py    # Document routes
│       └── health.py       # Health check routes
└── cli/
    ├── __init__.py
    ├── chat.py            # Interactive chat CLI
    └── manage.py          # Management CLI
```

### Technology Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **LangChain**: LLM orchestration and memory management
- **LlamaIndex**: Document ingestion and vector search
- **SQLAlchemy**: Async ORM for database operations
- **PostgreSQL + pgvector**: Vector database for embeddings
- **Pydantic**: Data validation and serialization
- **Structlog**: Structured logging
- **Typer + Rich**: Beautiful CLI interfaces

### Key Design Patterns

- **Dependency Injection**: Services are injected via FastAPI dependencies
- **Repository Pattern**: Database access abstracted through services
- **Factory Pattern**: Configurable LLM and vector store providers
- **Observer Pattern**: Streaming responses via async generators
- **Strategy Pattern**: Pluggable document processors and embeddings

## 🧪 Development

### Setup Development Environment

1. **Install development dependencies**
```bash
pip install -e ".[dev]"
```

2. **Install pre-commit hooks**
```bash
pre-commit install
```

3. **Run code formatting**
```bash
black src/
isort src/
```

4. **Run type checking**
```bash
mypy src/
```

5. **Run tests**
```bash
pytest
```

### Adding New Features

1. **Add a new LLM provider**
   - Extend `LLMService` in `services/llm_service.py`
   - Update configuration in `config/settings.py`
   - Add provider-specific dependencies

2. **Add a new vector store**
   - Extend `VectorStoreService` in `services/vector_store_service.py`
   - Update configuration options
   - Implement provider-specific methods

3. **Add new API endpoints**
   - Create route handlers in `api/routes/`
   - Add Pydantic models in `models/`
   - Update dependencies if needed

## 🚀 Deployment

### Production Checklist

- [ ] Set strong `SECRET_KEY` in environment
- [ ] Configure production database with connection pooling
- [ ] Set up reverse proxy (nginx) for SSL termination
- [ ] Configure log aggregation and monitoring
- [ ] Set up backup strategy for database and documents
- [ ] Enable CORS restrictions for your domain
- [ ] Set up rate limiting and DDoS protection

### Docker Production Deployment

```bash
# Build production image
docker build -t chatbot-api:latest .

# Run with production settings
docker run -d \
  --name chatbot-api \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e DATABASE_URL=postgresql://... \
  -e OPENAI_API_KEY=... \
  -e SECRET_KEY=... \
  chatbot-api:latest
```

### Kubernetes Deployment

Example deployment manifests:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chatbot-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chatbot-api
  template:
    metadata:
      labels:
        app: chatbot-api
    spec:
      containers:
      - name: api
        image: chatbot-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: chatbot-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
```

## 📊 Monitoring

### Health Endpoints

- `/health/` - Comprehensive health check
- `/health/live` - Kubernetes liveness probe
- `/health/ready` - Kubernetes readiness probe

### Metrics

The application provides structured logs that can be ingested by:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Prometheus + Grafana
- DataDog
- CloudWatch

### Key Metrics to Monitor

- Request latency and throughput
- Database connection pool usage
- OpenAI API usage and costs
- Document processing queue length
- Memory and CPU usage
- Error rates by endpoint

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Write docstrings for all public methods
- Maintain test coverage above 80%

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check this README and API docs at `/docs`
- **Issues**: Report bugs and feature requests on GitHub
- **Discussions**: Join community discussions on GitHub Discussions

## 🗺 Roadmap

### Near Term (v0.2)
- [ ] Plugin system for custom tools
- [ ] Multi-language support
- [ ] Advanced conversation analytics
- [ ] File format support (Word, Excel, PowerPoint)

### Medium Term (v0.3)
- [ ] Real-time collaboration features
- [ ] Advanced RAG techniques (hybrid search, re-ranking)
- [ ] Model fine-tuning capabilities
- [ ] Voice chat integration

### Long Term (v1.0)
- [ ] Multi-modal support (images, audio)
- [ ] Advanced AI agents and workflows
- [ ] Enterprise SSO integration
- [ ] On-premises deployment options

---

Made with ❤️ using modern Python and AI technologies.