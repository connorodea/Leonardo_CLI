#!/usr/bin/env python3
"""
Advanced features for Leonardo CLI - Additional commands and utilities
"""

import click
import json
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from typing import Dict, Any, List

console = Console()

class TemplateManager:
    """Enhanced template manager with more features"""
    
    TEMPLATES_DIR = os.path.expanduser("~/.leonardo-cli/templates")
    
    @classmethod
    def ensure_templates_dir(cls):
        """Ensure the templates directory exists."""
        os.makedirs(cls.TEMPLATES_DIR, exist_ok=True)
    
    @classmethod
    def save_template(cls, name: str, data: Dict[str, Any]):
        """Save a template to disk."""
        cls.ensure_templates_dir()
        template_path = os.path.join(cls.TEMPLATES_DIR, f"{name}.json")
        
        with open(template_path, "w") as f:
            json.dump(data, f, indent=2)
        
        console.print(f"[bold green]Template '{name}' saved successfully![/bold green]")
    
    @classmethod
    def load_template(cls, name: str) -> Dict[str, Any]:
        """Load a template from disk."""
        template_path = os.path.join(cls.TEMPLATES_DIR, f"{name}.json")
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template '{name}' not found")
        
        with open(template_path, "r") as f:
            return json.load(f)
    
    @classmethod
    def list_templates(cls) -> List[str]:
        """List all available templates."""
        cls.ensure_templates_dir()
        
        templates = []
        for filename in os.listdir(cls.TEMPLATES_DIR):
            if filename.endswith(".json"):
                templates.append(filename[:-5])  # Remove .json extension
        
        return templates
    
    @classmethod
    def delete_template(cls, name: str) -> bool:
        """Delete a template."""
        template_path = os.path.join(cls.TEMPLATES_DIR, f"{name}.json")
        
        if not os.path.exists(template_path):
            return False
        
        os.remove(template_path)
        return True

class BatchProcessor:
    """Process multiple generations in batch"""
    
    @staticmethod
    def process_batch(prompts: List[str], settings: Dict[str, Any], client):
        """Process a batch of prompts with the same settings"""
        results = []
        
        for i, prompt in enumerate(prompts):
            console.print(f"[bold blue]Processing prompt {i+1}/{len(prompts)}: {prompt[:50]}...[/bold blue]")
            
            try:
                response = client.create_generation(prompt=prompt, **settings)
                generation_id = response.get("sdGenerationJob", {}).get("generationId")
                
                if generation_id:
                    results.append({
                        "prompt": prompt,
                        "generation_id": generation_id,
                        "status": "started"
                    })
                else:
                    results.append({
                        "prompt": prompt,
                        "generation_id": None,
                        "status": "failed"
                    })
            except Exception as e:
                console.print(f"[bold red]Error with prompt '{prompt}': {str(e)}[/bold red]")
                results.append({
                    "prompt": prompt,
                    "generation_id": None,
                    "status": "error",
                    "error": str(e)
                })
        
        return results

# Add these commands to your main CLI

@click.command()
@click.option("--name", required=True, help="Name for the template")
@click.option("--prompt", required=True, help="The prompt to save")
@click.option("--model-id", help="Model ID")
@click.option("--width", type=int, default=512, help="Image width")
@click.option("--height", type=int, default=512, help="Image height")
@click.option("--alchemy", is_flag=True, help="Enable Alchemy")
@click.option("--phoenix", is_flag=True, help="Use Phoenix model")
@click.option("--contrast", type=float, help="Phoenix contrast")
@click.option("--preset-style", help="Preset style")
def save_template(name, prompt, model_id, width, height, alchemy, phoenix, contrast, preset_style):
    """Save generation settings as a reusable template."""
    
    template_data = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "alchemy": alchemy,
        "phoenix": phoenix
    }
    
    if model_id:
        template_data["model_id"] = model_id
    if contrast:
        template_data["contrast"] = contrast
    if preset_style:
        template_data["preset_style"] = preset_style
    
    TemplateManager.save_template(name, template_data)

@click.command()
def list_templates():
    """List all saved templates."""
    templates = TemplateManager.list_templates()
    
    if not templates:
        console.print("[bold yellow]No templates found.[/bold yellow]")
        return
    
    table = Table(title="Saved Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Prompt", style="green")
    table.add_column("Settings", style="magenta")
    
    for template_name in templates:
        try:
            template_data = TemplateManager.load_template(template_name)
            prompt = template_data.get("prompt", "N/A")
            
            settings = []
            if template_data.get("alchemy"):
                settings.append("Alchemy")
            if template_data.get("phoenix"):
                settings.append("Phoenix")
            if template_data.get("width") and template_data.get("height"):
                settings.append(f"{template_data['width']}x{template_data['height']}")
            
            table.add_row(
                template_name,
                prompt[:50] + "..." if len(prompt) > 50 else prompt,
                ", ".join(settings) if settings else "Default"
            )
        except Exception as e:
            table.add_row(template_name, "Error loading", str(e))
    
    console.print(table)

@click.command()
@click.argument("template_name")
@click.option("--output-dir", default="./leonardo-output", help="Directory to save images")
@click.option("--num", default=1, help="Number of images to generate")
def use_template(template_name, output_dir, num):
    """Generate images using a saved template."""
    try:
        template_data = TemplateManager.load_template(template_name)
        
        # Display template info
        console.print(Panel(
            f"[bold]Template: {template_name}[/bold]\n"
            f"Prompt: {template_data.get('prompt', 'N/A')}\n"
            f"Size: {template_data.get('width', 512)}x{template_data.get('height', 512)}\n"
            f"Alchemy: {'Yes' if template_data.get('alchemy') else 'No'}\n"
            f"Phoenix: {'Yes' if template_data.get('phoenix') else 'No'}",
            title="Template Settings"
        ))
        
        if not Confirm.ask("Generate images with these settings?"):
            console.print("[bold yellow]Generation cancelled.[/bold yellow]")
            return
        
        # Import and use the generate function logic here
        console.print("[bold blue]Generating images from template...[/bold blue]")
        console.print("[bold green]Template generation would start here![/bold green]")
        
    except FileNotFoundError:
        console.print(f"[bold red]Template '{template_name}' not found.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Error loading template: {str(e)}[/bold red]")

@click.command()
@click.argument("template_name")
def delete_template(template_name):
    """Delete a saved template."""
    if TemplateManager.delete_template(template_name):
        console.print(f"[bold green]Template '{template_name}' deleted successfully![/bold green]")
    else:
        console.print(f"[bold red]Template '{template_name}' not found.[/bold red]")

@click.command()
@click.option("--file", type=click.Path(exists=True), required=True, help="File containing prompts (one per line)")
@click.option("--model-id", help="Model ID to use for all generations")
@click.option("--width", default=512, help="Image width")
@click.option("--height", default=512, help="Image height")
@click.option("--alchemy", is_flag=True, help="Enable Alchemy")
@click.option("--output-dir", default="./leonardo-batch-output", help="Directory to save images")
def batch_generate(file, model_id, width, height, alchemy, output_dir):
    """Generate images for multiple prompts from a file."""
    
    # Read prompts from file
    try:
        with open(file, 'r') as f:
            prompts = [line.strip() for line in f if line.strip()]
    except Exception as e:
        console.print(f"[bold red]Error reading file: {str(e)}[/bold red]")
        return
    
    if not prompts:
        console.print("[bold red]No prompts found in file.[/bold red]")
        return
    
    console.print(f"[bold blue]Found {len(prompts)} prompts to process[/bold blue]")
    
    # Show preview
    table = Table(title="Batch Generation Preview")
    table.add_column("Index", style="cyan")
    table.add_column("Prompt", style="green")
    
    for i, prompt in enumerate(prompts[:5]):  # Show first 5
        table.add_row(str(i+1), prompt[:60] + "..." if len(prompt) > 60 else prompt)
    
    if len(prompts) > 5:
        table.add_row("...", f"... and {len(prompts) - 5} more prompts")
    
    console.print(table)
    
    if not Confirm.ask(f"Process all {len(prompts)} prompts?"):
        console.print("[bold yellow]Batch generation cancelled.[/bold yellow]")
        return
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    console.print("[bold green]Batch generation would start here![/bold green]")
    console.print(f"Results would be saved to: {output_path}")

@click.command()
@click.option("--generation-id", required=True, help="Generation ID to download")
@click.option("--output-dir", default="./leonardo-downloads", help="Directory to save images")
def download(generation_id, output_dir):
    """Download images from a completed generation."""
    from leonardo_cli import get_client
    
    client = get_client()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        with console.status(f"[bold blue]Fetching generation {generation_id}...[/bold blue]"):
            generation = client.get_generation(generation_id)
        
        status = generation.get("status", "UNKNOWN")
        console.print(f"Generation Status: [bold]{status}[/bold]")
        
        if status != "COMPLETE":
            console.print(f"[bold yellow]Generation is not complete (status: {status})[/bold yellow]")
            return
        
        images = generation.get("generations", [])
        if not images:
            console.print("[bold yellow]No images found in generation.[/bold yellow]")
            return
        
        console.print(f"[bold blue]Downloading {len(images)} image(s)...[/bold blue]")
        
        for i, image in enumerate(images):
            image_url = image.get("url")
            image_id = image.get("id")
            
            if image_url:
                import requests
                response = requests.get(image_url)
                response.raise_for_status()
                
                output_file = output_path / f"{generation_id}_{i}.png"
                with open(output_file, "wb") as f:
                    f.write(response.content)
                
                console.print(f"✅ Image {i+1} saved: [bold]{output_file}[/bold]")
            else:
                console.print(f"❌ Image {i+1} has no URL")
        
        console.print(f"[bold green]Download complete! Images saved to {output_path}[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Error downloading generation: {str(e)}[/bold red]")

# Example of how to add these to your main CLI:
"""
# Add these imports to your main leonardo_cli.py file:
from advanced_features import (
    save_template, list_templates, use_template, delete_template,
    batch_generate, download
)

# Then add these commands to your CLI group:
cli.add_command(save_template)
cli.add_command(list_templates)
cli.add_command(use_template)
cli.add_command(delete_template)
cli.add_command(batch_generate)
cli.add_command(download)
"""

if __name__ == "__main__":
    console.print("[bold green]Advanced Features Module[/bold green]")
    console.print("This module contains additional commands for the Leonardo CLI.")
    console.print("Import these functions into your main CLI to use them.")
