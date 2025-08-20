"""Interactive chat CLI interface."""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional
import httpx
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.text import Text

from chat.config import settings

app = typer.Typer(help="Interactive AI Chatbot CLI")
console = Console()


class ChatClient:
    """HTTP client for chat API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", token: Optional[str] = None):
        """Initialize chat client.
        
        Args:
            base_url: API base URL
            token: Authentication token
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Headers
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    async def login(self, username: str, password: str) -> Optional[str]:
        """Login and get access token.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Access token if successful
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                if token:
                    self.token = token
                    self.headers["Authorization"] = f"Bearer {token}"
                return token
            else:
                return None
                
        except Exception:
            return None
    
    async def register(self, username: str, email: str, password: str, full_name: Optional[str] = None) -> bool:
        """Register a new user.
        
        Args:
            username: Username
            email: Email
            password: Password
            full_name: Full name
            
        Returns:
            True if successful
        """
        try:
            data = {
                "username": username,
                "email": email,
                "password": password,
            }
            if full_name:
                data["full_name"] = full_name
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/register",
                json=data
            )
            
            return response.status_code == 201
            
        except Exception:
            return False
    
    async def send_message(self, message: str, conversation_id: Optional[str] = None) -> Optional[dict]:
        """Send a chat message.
        
        Args:
            message: Message content
            conversation_id: Optional conversation ID
            
        Returns:
            Response data if successful
        """
        try:
            data = {"message": message}
            if conversation_id:
                data["conversation_id"] = conversation_id
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/chat/",
                json=data,
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception:
            return None
    
    async def stream_message(self, message: str, conversation_id: Optional[str] = None):
        """Send a chat message with streaming response.
        
        Args:
            message: Message content
            conversation_id: Optional conversation ID
            
        Yields:
            Response chunks
        """
        try:
            data = {"message": message}
            if conversation_id:
                data["conversation_id"] = conversation_id
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/v1/chat/stream",
                json=data,
                headers=self.headers
            ) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunk_data = line[6:]  # Remove "data: " prefix
                            try:
                                yield json.loads(chunk_data)
                            except json.JSONDecodeError:
                                continue
                        
        except Exception as e:
            yield {"error": str(e)}
    
    async def list_conversations(self) -> list:
        """List user conversations.
        
        Returns:
            List of conversations
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/chat/conversations",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception:
            return []
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()


def load_token() -> Optional[str]:
    """Load saved token from file."""
    token_file = Path.home() / ".chat_token"
    if token_file.exists():
        return token_file.read_text().strip()
    return None


def save_token(token: str):
    """Save token to file."""
    token_file = Path.home() / ".chat_token"
    token_file.write_text(token)


def clear_token():
    """Clear saved token."""
    token_file = Path.home() / ".chat_token"
    if token_file.exists():
        token_file.unlink()


@app.command()
def login(
    username: str = typer.Option(..., "--username", "-u", help="Username"),
    password: str = typer.Option(..., "--password", "-p", hide_input=True, help="Password"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="Server URL"),
):
    """Login to the chat service."""
    async def _login():
        client = ChatClient(server)
        
        token = await client.login(username, password)
        if token:
            save_token(token)
            console.print("[green]Login successful![/green]")
        else:
            console.print("[red]Login failed. Please check your credentials.[/red]")
        
        await client.close()
    
    asyncio.run(_login())


@app.command()
def register(
    username: str = typer.Option(..., "--username", "-u", help="Username"),
    email: str = typer.Option(..., "--email", "-e", help="Email address"),
    password: str = typer.Option(..., "--password", "-p", hide_input=True, help="Password"),
    full_name: str = typer.Option(None, "--name", "-n", help="Full name"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="Server URL"),
):
    """Register a new account."""
    async def _register():
        client = ChatClient(server)
        
        success = await client.register(username, email, password, full_name)
        if success:
            console.print("[green]Registration successful! You can now login.[/green]")
        else:
            console.print("[red]Registration failed. Username or email may already exist.[/red]")
        
        await client.close()
    
    asyncio.run(_register())


@app.command()
def logout():
    """Logout and clear saved token."""
    clear_token()
    console.print("[green]Logged out successfully.[/green]")


@app.command()
def chat(
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="Server URL"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Enable streaming responses"),
):
    """Start interactive chat session."""
    async def _chat():
        # Load token
        token = load_token()
        if not token:
            console.print("[red]Please login first using 'chat-cli login'[/red]")
            return
        
        client = ChatClient(server, token)
        conversation_id = None
        
        console.print(Panel.fit(
            "[bold blue]AI Chatbot CLI[/bold blue]\n"
            "Type 'exit' or 'quit' to end the session\n"
            "Type '/new' to start a new conversation\n"
            "Type '/list' to list conversations",
            title="Welcome"
        ))
        
        try:
            while True:
                # Get user input
                user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
                
                if user_input.lower() in ["exit", "quit"]:
                    break
                elif user_input == "/new":
                    conversation_id = None
                    console.print("[green]Started new conversation[/green]")
                    continue
                elif user_input == "/list":
                    conversations = await client.list_conversations()
                    if conversations:
                        console.print("[bold]Your conversations:[/bold]")
                        for conv in conversations[:10]:  # Show last 10
                            title = conv.get("title", "Untitled")
                            conv_id = conv.get("id", "")[:8]
                            console.print(f"• {title} ({conv_id})")
                    else:
                        console.print("[yellow]No conversations found[/yellow]")
                    continue
                
                if not user_input.strip():
                    continue
                
                # Send message
                if stream:
                    # Streaming response
                    console.print("[bold green]Assistant[/bold green]:")
                    
                    response_text = ""
                    with Live(console=console, refresh_per_second=10) as live:
                        async for chunk in client.stream_message(user_input, conversation_id):
                            if "error" in chunk:
                                live.update(Text(f"Error: {chunk['error']}", style="red"))
                                break
                            elif chunk.get("done"):
                                # Response complete
                                break
                            else:
                                content = chunk.get("content", "")
                                response_text += content
                                conversation_id = chunk.get("conversation_id")
                                
                                # Update display
                                live.update(Markdown(response_text))
                    
                    console.print()  # Add newline
                    
                else:
                    # Non-streaming response
                    response = await client.send_message(user_input, conversation_id)
                    if response:
                        conversation_id = response.get("conversation_id")
                        message = response.get("message", {})
                        content = message.get("content", "")
                        
                        console.print("[bold green]Assistant[/bold green]:")
                        console.print(Markdown(content))
                        console.print()
                    else:
                        console.print("[red]Failed to get response[/red]")
                        
        except KeyboardInterrupt:
            console.print("\n[yellow]Chat session interrupted[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
        finally:
            await client.close()
    
    asyncio.run(_chat())


@app.command()
def conversations(
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="Server URL"),
):
    """List all conversations."""
    async def _list_conversations():
        token = load_token()
        if not token:
            console.print("[red]Please login first using 'chat-cli login'[/red]")
            return
        
        client = ChatClient(server, token)
        
        try:
            conversations = await client.list_conversations()
            
            if conversations:
                console.print("[bold]Your conversations:[/bold]")
                for conv in conversations:
                    title = conv.get("title", "Untitled")
                    conv_id = conv.get("id", "")
                    created = conv.get("created_at", "")
                    updated = conv.get("updated_at", "")
                    
                    console.print(Panel(
                        f"[bold]{title}[/bold]\n"
                        f"ID: {conv_id}\n"
                        f"Created: {created}\n"
                        f"Updated: {updated}",
                        width=80
                    ))
            else:
                console.print("[yellow]No conversations found[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
        finally:
            await client.close()
    
    asyncio.run(_list_conversations())


if __name__ == "__main__":
    app()