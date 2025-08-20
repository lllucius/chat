"""Management CLI for database operations and system administration."""

import asyncio
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from dotenv import load_dotenv

# Add app to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import init_db, close_db, engine
from app.config import settings
from app.core.logging import setup_logging, get_logger

# Load environment variables
load_dotenv()

# Setup
console = Console()
setup_logging()
logger = get_logger(__name__)


@click.group()
def cli():
    """Chat API Management CLI."""
    pass


@cli.command()
def init_database():
    """Initialize the database with tables and extensions."""
    asyncio.run(_init_database())


async def _init_database():
    """Initialize database."""
    try:
        console.print("[yellow]Initializing database...[/yellow]")
        
        with console.status("[bold green]Creating tables and extensions..."):
            await init_db()
        
        console.print("[green]✓ Database initialized successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Database initialization failed: {str(e)}[/red]")
        logger.error("Database initialization failed", error=str(e))
    
    finally:
        await close_db()


@cli.command()
def check_database():
    """Check database connection and status."""
    asyncio.run(_check_database())


async def _check_database():
    """Check database status."""
    try:
        from app.database import check_db_connection
        
        console.print("[yellow]Checking database connection...[/yellow]")
        
        healthy = await check_db_connection()
        
        if healthy:
            console.print("[green]✓ Database connection is healthy![/green]")
            
            # Show basic stats
            await _show_database_stats()
        else:
            console.print("[red]✗ Database connection failed![/red]")
    
    except Exception as e:
        console.print(f"[red]Database check failed: {str(e)}[/red]")
        logger.error("Database check failed", error=str(e))
    
    finally:
        await close_db()


async def _show_database_stats():
    """Show database statistics."""
    try:
        from sqlalchemy import text
        
        async with engine.begin() as conn:
            # Check if tables exist
            tables_result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """))
            tables = [row[0] for row in tables_result.fetchall()]
            
            # Show table info
            table = Table(title="Database Tables")
            table.add_column("Table", style="cyan")
            table.add_column("Status", style="green")
            
            expected_tables = [
                "users", "conversations", "messages", "documents", 
                "profiles", "prompts", "analytics"
            ]
            
            for table_name in expected_tables:
                status = "✓ Exists" if table_name in tables else "✗ Missing"
                style = "green" if table_name in tables else "red"
                table.add_row(table_name, f"[{style}]{status}[/{style}]")
            
            console.print(table)
            
            # Check extensions
            ext_result = await conn.execute(text("""
                SELECT extname FROM pg_extension WHERE extname = 'vector'
            """))
            vector_ext = ext_result.fetchone()
            
            if vector_ext:
                console.print("[green]✓ pgvector extension is installed[/green]")
            else:
                console.print("[red]✗ pgvector extension is not installed[/red]")
    
    except Exception as e:
        console.print(f"[yellow]Could not retrieve database stats: {str(e)}[/yellow]")


@cli.command()
@click.option("--username", required=True, help="Username for the superuser")
@click.option("--email", required=True, help="Email for the superuser")
@click.option("--password", prompt=True, hide_input=True, help="Password for the superuser")
def create_superuser(username: str, email: str, password: str):
    """Create a superuser account."""
    asyncio.run(_create_superuser(username, email, password))


async def _create_superuser(username: str, email: str, password: str):
    """Create superuser."""
    try:
        from app.database import get_db
        from app.services.auth_service import AuthService
        from app.schemas.user import UserCreate
        
        console.print(f"[yellow]Creating superuser '{username}'...[/yellow]")
        
        async for db in get_db():
            auth_service = AuthService(db)
            
            # Check if user exists
            existing_user = await auth_service.get_user_by_username(username)
            if existing_user:
                console.print(f"[red]User '{username}' already exists![/red]")
                return
            
            # Create user
            user_data = UserCreate(
                username=username,
                email=email,
                password=password,
                full_name=f"Superuser {username}",
                is_active=True
            )
            
            user = await auth_service.create_user(user_data)
            
            # Make superuser
            user.is_superuser = True
            await db.commit()
            
            console.print(f"[green]✓ Superuser '{username}' created successfully![/green]")
            break
    
    except Exception as e:
        console.print(f"[red]Superuser creation failed: {str(e)}[/red]")
        logger.error("Superuser creation failed", error=str(e))


@cli.command()
def show_config():
    """Show current configuration."""
    config_table = Table(title="Chat API Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    
    # Show selected config values
    configs = [
        ("API Title", settings.api_title),
        ("API Version", settings.api_version),
        ("Debug Mode", str(settings.debug)),
        ("Log Level", settings.log_level),
        ("Database URL", str(settings.database_url).replace(settings.database_url.password or "", "***")),
        ("LLM Model", settings.llm_model),
        ("Vector Dimension", str(settings.vector_dimension)),
        ("Max File Size", f"{settings.max_file_size_mb} MB"),
        ("Allowed File Types", ", ".join(settings.allowed_file_types)),
    ]
    
    for key, value in configs:
        config_table.add_row(key, str(value))
    
    console.print(config_table)


@cli.command()
def cleanup_analytics():
    """Clean up old analytics data."""
    asyncio.run(_cleanup_analytics())


async def _cleanup_analytics():
    """Clean up analytics."""
    try:
        from app.database import get_db
        from app.services.analytics_service import AnalyticsService
        
        console.print("[yellow]Cleaning up old analytics data...[/yellow]")
        
        async for db in get_db():
            analytics_service = AnalyticsService(db)
            deleted_count = await analytics_service.cleanup_old_analytics(days_to_keep=90)
            
            console.print(f"[green]✓ Cleaned up {deleted_count} old analytics records[/green]")
            break
    
    except Exception as e:
        console.print(f"[red]Analytics cleanup failed: {str(e)}[/red]")
        logger.error("Analytics cleanup failed", error=str(e))


@cli.command()
def show_stats():
    """Show system statistics."""
    asyncio.run(_show_stats())


async def _show_stats():
    """Show system statistics."""
    try:
        from app.database import get_db
        from app.services.vector_service import VectorService
        from sqlalchemy import select, func
        from app.models.user import User
        from app.models.conversation import Conversation
        from app.models.message import Message
        from app.models.document import Document
        
        console.print("[yellow]Gathering system statistics...[/yellow]")
        
        async for db in get_db():
            # User stats
            user_count_result = await db.execute(select(func.count(User.id)))
            user_count = user_count_result.scalar()
            
            active_user_count_result = await db.execute(
                select(func.count(User.id)).where(User.is_active == True)
            )
            active_user_count = active_user_count_result.scalar()
            
            # Conversation stats
            conv_count_result = await db.execute(select(func.count(Conversation.id)))
            conv_count = conv_count_result.scalar()
            
            # Message stats
            msg_count_result = await db.execute(select(func.count(Message.id)))
            msg_count = msg_count_result.scalar()
            
            # Document stats
            doc_count_result = await db.execute(select(func.count(Document.id)))
            doc_count = doc_count_result.scalar()
            
            # Vector stats
            vector_service = VectorService(db)
            vector_stats = await vector_service.get_vector_stats()
            
            # Create stats table
            stats_table = Table(title="System Statistics")
            stats_table.add_column("Metric", style="cyan")
            stats_table.add_column("Count", style="green")
            
            stats = [
                ("Total Users", str(user_count)),
                ("Active Users", str(active_user_count)),
                ("Total Conversations", str(conv_count)),
                ("Total Messages", str(msg_count)),
                ("Total Documents", str(doc_count)),
                ("Documents with Embeddings", str(vector_stats.get("documents_with_embeddings", 0))),
                ("Messages with Embeddings", str(vector_stats.get("messages_with_embeddings", 0))),
                ("Vector Dimension", str(vector_stats.get("vector_dimension", 0))),
            ]
            
            for metric, count in stats:
                stats_table.add_row(metric, count)
            
            console.print(stats_table)
            break
    
    except Exception as e:
        console.print(f"[red]Failed to gather statistics: {str(e)}[/red]")
        logger.error("Statistics gathering failed", error=str(e))


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def runserver(host: str, port: int, reload: bool):
    """Run the development server."""
    import uvicorn
    
    console.print(Panel.fit(
        f"[bold blue]Starting Chat API Server[/bold blue]\n\n"
        f"Host: {host}\n"
        f"Port: {port}\n"
        f"Reload: {reload}\n"
        f"Debug: {settings.debug}",
        title="Server Info"
    ))
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=settings.log_level.lower()
    )


def main():
    """Entry point for the management CLI."""
    cli()


if __name__ == "__main__":
    main()