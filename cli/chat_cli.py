"""CLI chat interface for testing and interaction."""

import asyncio
import os
import sys
from typing import Optional
import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

console = Console()


class ChatClient:
    """HTTP client for Chat API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.client = httpx.AsyncClient()
    
    async def login(self, username: str, password: str) -> bool:
        """Login and get access token."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/login",
                data={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                return True
            else:
                console.print(f"[red]Login failed: {response.text}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]Login error: {str(e)}[/red]")
            return False
    
    async def register(self, username: str, email: str, password: str, full_name: str = "") -> bool:
        """Register a new user."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/register",
                json={
                    "username": username,
                    "email": email,
                    "password": password,
                    "full_name": full_name
                }
            )
            
            if response.status_code == 201:
                console.print("[green]Registration successful![/green]")
                return True
            else:
                console.print(f"[red]Registration failed: {response.text}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]Registration error: {str(e)}[/red]")
            return False
    
    async def send_message(self, message: str, conversation_id: Optional[int] = None) -> dict:
        """Send a message and get response."""
        if not self.token:
            raise ValueError("Not authenticated")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"message": message}
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/chat/message",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Message failed: {response.text}")
    
    async def get_conversations(self) -> list:
        """Get user conversations."""
        if not self.token:
            raise ValueError("Not authenticated")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v1/conversations/",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get conversations: {response.text}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


@click.group()
def cli():
    """Chat CLI - Interactive chat interface."""
    pass


@cli.command()
@click.option("--url", default="http://localhost:8000", help="API base URL")
@click.option("--username", help="Username for login")
@click.option("--password", help="Password for login")
def chat(url: str, username: Optional[str], password: Optional[str]):
    """Start interactive chat session."""
    asyncio.run(_chat_session(url, username, password))


async def _chat_session(url: str, username: Optional[str], password: Optional[str]):
    """Main chat session."""
    client = ChatClient(url)
    
    try:
        # Show welcome
        console.print(Panel.fit(
            "[bold blue]Chat API CLI[/bold blue]\n"
            "Type 'help' for commands, 'quit' to exit",
            title="Welcome"
        ))
        
        # Authentication
        if not username:
            username = Prompt.ask("Username")
        if not password:
            password = Prompt.ask("Password", password=True)
        
        with console.status("[bold green]Logging in..."):
            if not await client.login(username, password):
                return
        
        console.print("[green]✓ Logged in successfully![/green]")
        
        # Show conversations
        try:
            conversations = await client.get_conversations()
            if conversations:
                table = Table(title="Recent Conversations")
                table.add_column("ID", style="cyan")
                table.add_column("Title", style="magenta")
                table.add_column("Messages", style="green")
                table.add_column("Last Activity", style="yellow")
                
                for conv in conversations[:5]:  # Show last 5
                    table.add_row(
                        str(conv["id"]),
                        conv["title"][:50] + "..." if len(conv["title"]) > 50 else conv["title"],
                        str(conv["message_count"]),
                        conv.get("last_message_at", "N/A")
                    )
                
                console.print(table)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load conversations: {str(e)}[/yellow]")
        
        # Chat loop
        conversation_id = None
        
        while True:
            try:
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
                
                if not user_input.strip():
                    continue
                
                # Handle commands
                if user_input.lower() in ["quit", "exit", "q"]:
                    break
                elif user_input.lower() == "help":
                    _show_help()
                    continue
                elif user_input.lower() == "clear":
                    console.clear()
                    continue
                elif user_input.lower() == "new":
                    conversation_id = None
                    console.print("[green]✓ Starting new conversation[/green]")
                    continue
                elif user_input.lower() == "conversations":
                    await _show_conversations(client)
                    continue
                
                # Send message
                with Live(Spinner("dots", text="[bold green]Thinking..."), console=console):
                    response = await client.send_message(user_input, conversation_id)
                
                # Update conversation ID
                conversation_id = response["conversation_id"]
                
                # Display response
                console.print("\n[bold green]Assistant[/bold green]:")
                console.print(Panel(
                    Markdown(response["message"]),
                    title=f"Response (Tokens: {response['token_count']}, "
                          f"Time: {response['processing_time']:.2f}s)",
                    border_style="green"
                ))
                
                # Show sources if available
                if response.get("sources"):
                    _show_sources(response["sources"])
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'quit' to exit[/yellow]")
                continue
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                continue
    
    finally:
        await client.close()
        console.print("\n[blue]Goodbye![/blue]")


def _show_help():
    """Show help information."""
    help_text = """
[bold]Available Commands:[/bold]

• [cyan]help[/cyan] - Show this help
• [cyan]quit[/cyan], [cyan]exit[/cyan], [cyan]q[/cyan] - Exit the chat
• [cyan]clear[/cyan] - Clear the screen
• [cyan]new[/cyan] - Start a new conversation
• [cyan]conversations[/cyan] - List recent conversations

[bold]Tips:[/bold]
• Type naturally to chat with the AI
• Use Ctrl+C to interrupt (but use 'quit' to exit properly)
• The AI has access to uploaded documents for context
"""
    console.print(Panel(help_text, title="Help", border_style="blue"))


async def _show_conversations(client: ChatClient):
    """Show user conversations."""
    try:
        conversations = await client.get_conversations()
        
        if not conversations:
            console.print("[yellow]No conversations found[/yellow]")
            return
        
        table = Table(title="Your Conversations")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="magenta")
        table.add_column("Messages", style="green")
        table.add_column("Tokens", style="blue")
        table.add_column("Created", style="yellow")
        
        for conv in conversations:
            table.add_row(
                str(conv["id"]),
                conv["title"][:50] + "..." if len(conv["title"]) > 50 else conv["title"],
                str(conv["message_count"]),
                str(conv["total_tokens"]),
                conv["created_at"][:10]  # Just the date
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error loading conversations: {str(e)}[/red]")


def _show_sources(sources: list):
    """Show document sources."""
    if not sources:
        return
    
    console.print("\n[bold blue]📚 Sources:[/bold blue]")
    for i, source in enumerate(sources, 1):
        console.print(f"  {i}. {source['filename']} (Score: {source['similarity_score']:.2f})")


@cli.command()
@click.option("--url", default="http://localhost:8000", help="API base URL")
def register(url: str):
    """Register a new user."""
    asyncio.run(_register_user(url))


async def _register_user(url: str):
    """Register a new user."""
    client = ChatClient(url)
    
    try:
        console.print(Panel.fit(
            "[bold blue]User Registration[/bold blue]",
            title="Chat API"
        ))
        
        username = Prompt.ask("Username")
        email = Prompt.ask("Email")
        full_name = Prompt.ask("Full Name (optional)", default="")
        password = Prompt.ask("Password", password=True)
        confirm_password = Prompt.ask("Confirm Password", password=True)
        
        if password != confirm_password:
            console.print("[red]Passwords do not match![/red]")
            return
        
        with console.status("[bold green]Creating account..."):
            success = await client.register(username, email, password, full_name)
        
        if success:
            console.print("\n[green]✓ Account created successfully![/green]")
            
            if Confirm.ask("Would you like to start chatting now?"):
                await _chat_session(url, username, password)
    
    finally:
        await client.close()


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()