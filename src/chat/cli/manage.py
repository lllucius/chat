"""Management CLI for administrative tasks."""

import asyncio
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy import select, func

from chat.core import init_db, close_db, get_db_session
from chat.models import User, Conversation, Message, Document
from chat.services import auth_service, document_service
from chat.config import settings

app = typer.Typer(help="Management CLI for AI Chatbot")
console = Console()


@app.command()
def init_database():
    """Initialize the database."""
    async def _init():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Initializing database...", total=None)
            
            try:
                await init_db()
                progress.update(task, description="✅ Database initialized successfully")
                console.print("[green]Database initialization completed![/green]")
            except Exception as e:
                progress.update(task, description="❌ Database initialization failed")
                console.print(f"[red]Error: {e}[/red]")
            finally:
                await close_db()
    
    asyncio.run(_init())


@app.command()
def create_admin(
    username: str = typer.Option(..., "--username", "-u", help="Admin username"),
    email: str = typer.Option(..., "--email", "-e", help="Admin email"),
    password: str = typer.Option(..., "--password", "-p", hide_input=True, help="Admin password"),
    full_name: str = typer.Option(None, "--name", "-n", help="Full name"),
):
    """Create an admin user."""
    async def _create_admin():
        await init_db()
        
        try:
            async with get_db_session() as db_session:
                # Check if user already exists
                existing_user = await auth_service.get_user_by_username(username, db_session)
                if existing_user:
                    console.print(f"[red]User {username} already exists[/red]")
                    return
                
                # Create admin user
                from chat.models import UserCreate
                user_data = UserCreate(
                    username=username,
                    email=email,
                    password=password,
                    full_name=full_name,
                )
                
                user = await auth_service.create_user(user_data, db_session)
                
                # Make user admin
                await auth_service.update_user(
                    user.id, {"is_admin": True}, db_session
                )
                
                console.print(f"[green]Admin user {username} created successfully![/green]")
                
        except Exception as e:
            console.print(f"[red]Error creating admin user: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_create_admin())


@app.command()
def list_users(
    limit: int = typer.Option(50, "--limit", "-l", help="Number of users to show"),
    admin_only: bool = typer.Option(False, "--admin-only", help="Show only admin users"),
):
    """List users."""
    async def _list_users():
        await init_db()
        
        try:
            async with get_db_session() as db_session:
                query = select(User).order_by(User.created_at.desc()).limit(limit)
                
                if admin_only:
                    query = query.where(User.is_admin == True)
                
                result = await db_session.execute(query)
                users = result.scalars().all()
                
                if users:
                    table = Table(title="Users")
                    table.add_column("ID", style="cyan")
                    table.add_column("Username", style="green")
                    table.add_column("Email", style="blue")
                    table.add_column("Full Name")
                    table.add_column("Active", style="green")
                    table.add_column("Admin", style="red")
                    table.add_column("Created", style="dim")
                    
                    for user in users:
                        table.add_row(
                            str(user.id)[:8],
                            user.username,
                            user.email,
                            user.full_name or "-",
                            "✅" if user.is_active else "❌",
                            "✅" if user.is_admin else "❌",
                            user.created_at.strftime("%Y-%m-%d %H:%M"),
                        )
                    
                    console.print(table)
                else:
                    console.print("[yellow]No users found[/yellow]")
                    
        except Exception as e:
            console.print(f"[red]Error listing users: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_list_users())


@app.command()
def deactivate_user(
    username: str = typer.Argument(..., help="Username to deactivate"),
):
    """Deactivate a user."""
    async def _deactivate_user():
        await init_db()
        
        try:
            async with get_db_session() as db_session:
                user = await auth_service.get_user_by_username(username, db_session)
                if not user:
                    console.print(f"[red]User {username} not found[/red]")
                    return
                
                success = await auth_service.deactivate_user(str(user.id), db_session)
                if success:
                    console.print(f"[green]User {username} deactivated successfully[/green]")
                else:
                    console.print(f"[red]Failed to deactivate user {username}[/red]")
                    
        except Exception as e:
            console.print(f"[red]Error deactivating user: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_deactivate_user())


@app.command()
def stats():
    """Show system statistics."""
    async def _stats():
        await init_db()
        
        try:
            async with get_db_session() as db_session:
                # Count users
                users_result = await db_session.execute(select(func.count(User.id)))
                total_users = users_result.scalar()
                
                active_users_result = await db_session.execute(
                    select(func.count(User.id)).where(User.is_active == True)
                )
                active_users = active_users_result.scalar()
                
                admin_users_result = await db_session.execute(
                    select(func.count(User.id)).where(User.is_admin == True)
                )
                admin_users = admin_users_result.scalar()
                
                # Count conversations
                conversations_result = await db_session.execute(select(func.count(Conversation.id)))
                total_conversations = conversations_result.scalar()
                
                # Count messages
                messages_result = await db_session.execute(select(func.count(Message.id)))
                total_messages = messages_result.scalar()
                
                # Count documents
                documents_result = await db_session.execute(select(func.count(Document.id)))
                total_documents = documents_result.scalar()
                
                # Create table
                table = Table(title="System Statistics")
                table.add_column("Metric", style="cyan")
                table.add_column("Count", style="green", justify="right")
                
                table.add_row("Total Users", str(total_users))
                table.add_row("Active Users", str(active_users))
                table.add_row("Admin Users", str(admin_users))
                table.add_row("Conversations", str(total_conversations))
                table.add_row("Messages", str(total_messages))
                table.add_row("Documents", str(total_documents))
                
                console.print(table)
                
        except Exception as e:
            console.print(f"[red]Error getting statistics: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_stats())


@app.command()
def cleanup_documents(
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Show what would be deleted without actually deleting"),
):
    """Clean up failed or orphaned documents."""
    async def _cleanup():
        await init_db()
        
        try:
            async with get_db_session() as db_session:
                # Find failed documents
                failed_docs_result = await db_session.execute(
                    select(Document).where(Document.status == "failed")
                )
                failed_docs = failed_docs_result.scalars().all()
                
                # Find documents with missing files
                orphaned_docs = []
                all_docs_result = await db_session.execute(select(Document))
                all_docs = all_docs_result.scalars().all()
                
                for doc in all_docs:
                    if doc.file_path and not Path(doc.file_path).exists():
                        orphaned_docs.append(doc)
                
                total_to_delete = len(failed_docs) + len(orphaned_docs)
                
                if total_to_delete == 0:
                    console.print("[green]No documents need cleanup[/green]")
                    return
                
                console.print(f"Found {len(failed_docs)} failed documents")
                console.print(f"Found {len(orphaned_docs)} orphaned documents")
                console.print(f"Total documents to clean up: {total_to_delete}")
                
                if dry_run:
                    console.print("[yellow]This is a dry run. Use --execute to actually delete documents.[/yellow]")
                    
                    # Show details
                    if failed_docs:
                        console.print("\n[red]Failed documents:[/red]")
                        for doc in failed_docs:
                            console.print(f"  • {doc.filename} ({doc.id})")
                    
                    if orphaned_docs:
                        console.print("\n[yellow]Orphaned documents:[/yellow]")
                        for doc in orphaned_docs:
                            console.print(f"  • {doc.filename} ({doc.id})")
                else:
                    # Actual cleanup
                    deleted_count = 0
                    
                    for doc in failed_docs + orphaned_docs:
                        try:
                            # Delete file if it exists
                            if doc.file_path and Path(doc.file_path).exists():
                                Path(doc.file_path).unlink()
                            
                            # Delete from database
                            await db_session.delete(doc)
                            deleted_count += 1
                            
                        except Exception as e:
                            console.print(f"[red]Failed to delete {doc.filename}: {e}[/red]")
                    
                    await db_session.commit()
                    console.print(f"[green]Successfully deleted {deleted_count} documents[/green]")
                
        except Exception as e:
            console.print(f"[red]Error during cleanup: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_cleanup())


@app.command()
def export_data(
    output_dir: Path = typer.Option("./export", "--output", "-o", help="Output directory"),
    include_documents: bool = typer.Option(False, "--include-docs", help="Include document files"),
):
    """Export system data."""
    async def _export():
        output_dir.mkdir(exist_ok=True)
        await init_db()
        
        try:
            async with get_db_session() as db_session:
                console.print(f"[blue]Exporting data to {output_dir}[/blue]")
                
                # Export users (without passwords)
                users_result = await db_session.execute(select(User))
                users = users_result.scalars().all()
                
                users_data = []
                for user in users:
                    users_data.append({
                        "id": str(user.id),
                        "username": user.username,
                        "email": user.email,
                        "full_name": user.full_name,
                        "is_active": user.is_active,
                        "is_admin": user.is_admin,
                        "created_at": user.created_at.isoformat(),
                    })
                
                # Export conversations
                conversations_result = await db_session.execute(select(Conversation))
                conversations = conversations_result.scalars().all()
                
                conversations_data = []
                for conv in conversations:
                    conversations_data.append({
                        "id": str(conv.id),
                        "user_id": str(conv.user_id),
                        "title": conv.title,
                        "status": conv.status,
                        "created_at": conv.created_at.isoformat(),
                    })
                
                # Export messages
                messages_result = await db_session.execute(select(Message))
                messages = messages_result.scalars().all()
                
                messages_data = []
                for msg in messages:
                    messages_data.append({
                        "id": str(msg.id),
                        "conversation_id": str(msg.conversation_id),
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                    })
                
                # Export documents metadata
                documents_result = await db_session.execute(select(Document))
                documents = documents_result.scalars().all()
                
                documents_data = []
                for doc in documents:
                    doc_data = {
                        "id": str(doc.id),
                        "user_id": str(doc.user_id),
                        "filename": doc.filename,
                        "file_type": doc.file_type,
                        "file_size": doc.file_size,
                        "status": doc.status,
                        "created_at": doc.created_at.isoformat(),
                    }
                    
                    # Copy document file if requested
                    if include_documents and doc.file_path and Path(doc.file_path).exists():
                        docs_dir = output_dir / "documents"
                        docs_dir.mkdir(exist_ok=True)
                        
                        import shutil
                        dest_path = docs_dir / f"{doc.id}_{doc.filename}"
                        shutil.copy2(doc.file_path, dest_path)
                        doc_data["exported_file"] = str(dest_path)
                    
                    documents_data.append(doc_data)
                
                # Write JSON files
                import json
                
                (output_dir / "users.json").write_text(
                    json.dumps(users_data, indent=2)
                )
                (output_dir / "conversations.json").write_text(
                    json.dumps(conversations_data, indent=2)
                )
                (output_dir / "messages.json").write_text(
                    json.dumps(messages_data, indent=2)
                )
                (output_dir / "documents.json").write_text(
                    json.dumps(documents_data, indent=2)
                )
                
                console.print(f"[green]Data exported successfully to {output_dir}[/green]")
                console.print(f"  • {len(users_data)} users")
                console.print(f"  • {len(conversations_data)} conversations") 
                console.print(f"  • {len(messages_data)} messages")
                console.print(f"  • {len(documents_data)} documents")
                
        except Exception as e:
            console.print(f"[red]Error during export: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_export())


@app.command()
def config():
    """Show current configuration."""
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    # Show key settings (without sensitive data)
    config_items = [
        ("Environment", settings.environment),
        ("API Host", settings.api_host),
        ("API Port", str(settings.api_port)),
        ("Debug Mode", str(settings.debug)),
        ("OpenAI Model", settings.openai_model),
        ("Vector Store Type", settings.vector_store_type),
        ("Max File Size", f"{settings.max_file_size // 1024 // 1024} MB"),
        ("Chunk Size", str(settings.chunk_size)),
        ("Log Level", settings.log_level),
    ]
    
    for setting, value in config_items:
        table.add_row(setting, value)
    
    console.print(table)


if __name__ == "__main__":
    app()