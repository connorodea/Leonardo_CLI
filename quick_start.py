#!/usr/bin/env python3
"""
Quick start script for Leonardo CLI - Interactive setup and first generation
"""

import os
import sys
import subprocess
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

console = Console()

def check_dependencies():
    """Check if all required dependencies are installed"""
    console.print("[bold blue]Checking dependencies...[/bold blue]")
    
    required = ['click', 'requests', 'rich']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            console.print(f"✅ {package}")
        except ImportError:
            console.print(f"❌ {package}")
            missing.append(package)
    
    if missing:
        console.print(f"\n[bold red]Missing packages: {', '.join(missing)}[/bold red]")
        if Confirm.ask("Install missing packages?"):
            for package in missing:
                subprocess.run([sys.executable, "-m", "pip", "install", package])
            console.print("[bold green]Packages installed![/bold green]")
        else:
            console.print("[bold yellow]Please install missing packages manually.[/bold yellow]")
            return False
    
    return True

def setup_api_key():
    """Interactive API key setup"""
    console.print("\n[bold blue]API Key Setup[/bold blue]")
    
    current_key = os.getenv('LEONARDO_API_KEY')
    if current_key:
        console.print(f"✅ API key already set: {current_key[:8]}...{current_key[-4:]}")
        if not Confirm.ask("Update API key?"):
            return current_key
    
    console.print(Panel(
        "To get your Leonardo AI API key:\n"
        "1. Go to https://app.leonardo.ai/\n"
        "2. Sign in to your account\n"
        "3. Go to API section in your profile\n"
        "4. Generate or copy your API key",
        title="Getting Your API Key"
    ))
    
    api_key = Prompt.ask("Enter your Leonardo AI API key", password=True)
    
    if api_key:
        # Set for current session
        os.environ['LEONARDO_API_KEY'] = api_key
        
        # Offer to save permanently
        if Confirm.ask("Save API key to your shell profile (.bashrc/.zshrc)?"):
            shell_profile = Path.home() / ".bashrc"
            if not shell_profile.exists():
                shell_profile = Path.home() / ".zshrc"
            
            try:
                with open(shell_profile, "a") as f:
                    f.write(f'\nexport LEONARDO_API_KEY="{api_key}"\n')
                console.print(f"[bold green]API key saved to {shell_profile}[/bold green]")
                console.print("[bold yellow]Restart your terminal or run 'source ~/.bashrc' to load it[/bold yellow]")
            except Exception as e:
                console.print(f"[bold red]Could not save to shell profile: {e}[/bold red]")
        
        return api_key
    
    return None

def test_api_connection(api_key):
    """Test the API connection"""
    console.print("\n[bold blue]Testing API connection...[/bold blue]")
    
    try:
        # Import and test the client
        sys.path.append('.')
        from leonardo_cli_fixed import LeonardoClient
        
        client = LeonardoClient(api_key)
        user_info = client.get_user_info()
        
        console.print("[bold green]✅ API connection successful![/bold green]")
        
        # Display user info
        table = Table(title="Your Account Info")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        user_data = user_info.get("user", {})
        table.add_row("Username", user_data.get("username", "N/A"))
        table.add_row("Email", user_data.get("email", "N/A"))
        
        subscription = user_info.get("subscription", {})
        if subscription:
            table.add_row("Plan", subscription.get("plan", "N/A"))
            table.add_row("Tokens Remaining", str(subscription.get("tokensRemaining", "N/A")))
        
        console.print(table)
        return True
        
    except Exception as e:
        console.print(f"[bold red]❌ API connection failed: {str(e)}[/bold red]")
        return False

def first_generation():
    """Guide user through their first image generation"""
    console.print("\n[bold blue]Let's generate your first image![/bold blue]")
    
    # Suggest some prompts
    suggested_prompts = [
        "a beautiful sunset over mountains",
        "a futuristic cityscape at night",
        "a magical forest with glowing mushrooms",
        "a cute robot in a garden",
        "an abstract digital art piece"
    ]
    
    console.print("\n[bold cyan]Suggested prompts:[/bold cyan]")
    for i, prompt in enumerate(suggested_prompts, 1):
        console.print(f"  {i}. {prompt}")
    
    choice = Prompt.ask(
        "\nChoose a number (1-5) or enter your own prompt",
        default="1"
    )
    
    if choice.isdigit() and 1 <= int(choice) <= 5:
        prompt = suggested_prompts[int(choice) - 1]
    else:
        prompt = choice
    
    console.print(f"\n[bold green]Great! We'll generate: '{prompt}'[/bold green]")
    
    # Ask about settings
    use_alchemy = Confirm.ask("Use Alchemy for higher quality? (costs more tokens)", default=True)
    use_phoenix = Confirm.ask("Use Phoenix model? (latest model)", default=False)
    
    # Build command
    cmd = [
        "python3", "leonardo_cli_fixed.py", "generate", prompt,
        "--width", "1024", "--height", "1024"
    ]
    
    if use_alchemy:
        cmd.append("--alchemy")
    
    if use_phoenix:
        cmd.extend(["--phoenix", "--contrast", "3.5"])
    
    console.print(f"\n[bold blue]Running: {' '.join(cmd)}[/bold blue]")
    
    if Confirm.ask("Start generation?"):
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Generation cancelled.[/bold yellow]")
        except Exception as e:
            console.print(f"\n[bold red]Error: {str(e)}[/bold red]")

def show_next_steps():
    """Show what users can do next"""
    console.print("\n" + "="*60)
    console.print("[bold green]🎉 Setup Complete![/bold green]")
    
    console.print("\n[bold cyan]What you can do next:[/bold cyan]")
    
    commands = [
        ("Generate images", "python3 leonardo_cli_fixed.py generate 'your prompt'"),
        ("List models", "python3 leonardo_cli_fixed.py models"),
        ("Check account", "python3 leonardo_cli_fixed.py user"),
        ("Interactive shell", "python3 leonardo_cli_fixed.py shell"),
        ("Get help", "python3 leonardo_cli_fixed.py --help")
    ]
    
    table = Table()
    table.add_column("Action", style="cyan")
    table.add_column("Command", style="green")
    
    for action, command in commands:
        table.add_row(action, command)
    
    console.print(table)
    
    console.print("\n[bold yellow]Pro Tips:[/bold yellow]")
    console.print("• Use --alchemy for higher quality (costs more tokens)")
    console.print("• Use --phoenix for the latest model")
    console.print("• Try different aspect ratios with --width and --height")
    console.print("• Use the shell mode for interactive use")

def main():
    """Main quick start flow"""
    console.print(Panel(
        "[bold blue]Leonardo AI CLI Quick Start[/bold blue]\n"
        "This script will help you set up and test the Leonardo CLI",
        title="Welcome!"
    ))
    
    # Step 1: Check dependencies
    if not check_dependencies():
        return
    
    # Step 2: Setup API key
    api_key = setup_api_key()
    if not api_key:
        console.print("[bold red]API key is required to continue.[/bold red]")
        return
    
    # Step 3: Test connection
    if not test_api_connection(api_key):
        console.print("[bold red]Please check your API key and try again.[/bold red]")
        return
    
    # Step 4: First generation
    if Confirm.ask("\nWould you like to generate your first image?"):
        first_generation()
    
    # Step 5: Show next steps
    show_next_steps()

if __name__ == "__main__":
    main()
