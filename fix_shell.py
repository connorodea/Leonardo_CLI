import os

# Path to the CLI script
script_path = 'leonardo_cli.py'

# Read the file content
with open(script_path, 'r') as f:
    content = f.read()

# Add shlex import at the top level
if 'import shlex' not in content:
    content = content.replace('import click', 'import shlex\nimport click')

# Fix the shell function
shell_func = '''
@cli.command()
def shell():
    """Launch an interactive shell for executing commands."""
    # Create a custom click context to run commands
    ctx = click.Context(cli, info_name="leonardo-cli", parent=None)
    
    console.print("[bold green]Leonardo AI CLI Interactive Shell[/bold green]")
    console.print("Type 'help' to see available commands, 'exit' to quit.")
    
    # Get active profile for shell welcome message
    active_profile = get_active_profile()
    console.print(f"Using profile: [italic cyan]{active_profile}[/italic cyan]")
    
    while True:
        try:
            # Get command from user
            command = input("\\n[leonardo-cli]> ")
            
            # Handle shell-specific commands
            if command.lower() in ("exit", "quit"):
                console.print("[bold green]Exiting shell. Goodbye![/bold green]")
                break
            elif command.lower() == "help":
                console.print("\\n[bold cyan]Available Commands:[/bold cyan]")
                console.print("  generate <prompt>        Generate images from a text prompt")
                console.print("  video --image-id <id>    Generate video from an image")
                console.print("  img2img                  Create image from initial image")
                console.print("  image-guidance           Use ControlNet features")
                console.print("  variation <id> --type <type>  Create a variation of an image")
                console.print("  estimate                 Estimate generation cost")
                console.print("  user                     Get user information")
                console.print("  models                   List available models")
                console.print("  profiles                 List configuration profiles")
                console.print("  use-profile <n>          Switch to a different profile")
                console.print("  usage                    Show API token usage")
                console.print("  exit                     Exit the shell")
                continue
            elif not command.strip():
                continue
            
            # Split the command respecting quotes
            try:
                args = shlex.split(command)
            except ValueError as e:
                console.print(f"[bold red]Error parsing command: {str(e)}[/bold red]")
                continue
                
            if not args:
                continue
                
            cmd_name = args[0]
            cmd_args = args[1:]
            
            # Find the command in the CLI group
            if cmd_name not in cli.commands:
                console.print(f"[bold red]Unknown command: {cmd_name}[/bold red]")
                console.print("Type 'help' to see available commands.")
                continue
            
            # Run the command
            result = cli.commands[cmd_name].main(cmd_args, standalone_mode=False, parent=ctx)
            
        except click.exceptions.Exit:
            # Command executed successfully
            pass
        except click.exceptions.UsageError as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")
        except click.exceptions.Abort:
            console.print("\\n[bold yellow]Operation aborted.[/bold yellow]")
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")
'''

# Find and replace the shell function
import re
pattern = r'@cli\.command$$$$\ndef shell$$$$:[^@]*'
replacement = shell_func.strip()
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back the updated content
with open(script_path, 'w') as f:
    f.write(content)

print("Fixed the shell function and added shlex import!")
