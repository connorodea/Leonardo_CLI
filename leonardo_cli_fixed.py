#!/usr/bin/env python3
"""
Leonardo AI CLI - Enhanced version with advanced features like ControlNet/Image Guidance,
Image-to-Image generation, and support for Phoenix model parameters.
"""

import shlex
import os
import sys
import time
import json
import click
import requests
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

console = Console()

# Constants
API_BASE_URL = "https://cloud.leonardo.ai/api/rest/v1"
CONFIG_PATH = os.path.expanduser("~/.leonardo-cli/config.json")


class LeonardoClient:
    """Client for interacting with the Leonardo AI API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}"
        }

    def get_user_info(self) -> Dict[str, Any]:
        """Get information about the authenticated user."""
        response = requests.get(f"{API_BASE_URL}/me", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def list_models(self) -> Dict[str, Any]:
        """List available AI models."""
        # Try the newer endpoint structure first
        try:
            response = requests.get(f"{API_BASE_URL}/platformModels", headers=self.headers)
            response.raise_for_status()
            result = response.json()
            # Format to match expected structure
            return {"models": result.get("platformModels", [])}
        except Exception as e:
            # Log the error but do not fail
            console.print(f"[bold yellow]Warning: Could not fetch models using platformModels endpoint: {str(e)}[/bold yellow]")
            # Try legacy endpoint as fallback
            try:
                response = requests.get(f"{API_BASE_URL}/models", headers=self.headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                console.print(f"[bold yellow]Warning: Could not fetch models using legacy endpoint: {str(e)}[/bold yellow]")
                # Return empty result if both fail
                return {"models": []}
        
    def list_platform_models(self) -> Dict[str, Any]:
        """List platform models."""
        response = requests.get(f"{API_BASE_URL}/platformModels", headers=self.headers)
        response.raise_for_status()
        return response.json()
        
    def list_custom_models(self) -> Dict[str, Any]:
        """List user's custom models."""
        response = requests.get(f"{API_BASE_URL}/me/models", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def create_generation(self, 
                         prompt: str, 
                         model_id: str = None, 
                         num_images: int = 1, 
                         width: int = 512, 
                         height: int = 512, 
                         negative_prompt: str = None,
                         guidance_scale: float = 7.0, 
                         preset_style: str = None,
                         alchemy: bool = False, 
                         photoreal: bool = False,
                         photoreal_version: str = None,
                         init_image_id: str = None,
                         init_strength: float = None,
                         init_generation_image_id: str = None,
                         image_prompts: List[str] = None,
                         controlnets: List[Dict[str, Any]] = None,
                         is_phoenix: bool = False,
                         contrast: float = None) -> Dict[str, Any]:
        """Generate images with advanced parameters."""
        payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_images": num_images
        }
        
        # Add modelId if provided
        if model_id:
            payload["modelId"] = model_id
            
        # Add optional parameters if provided
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        if guidance_scale is not None:
            payload["guidance_scale"] = guidance_scale
            
        if preset_style:
            payload["presetStyle"] = preset_style
            
        if alchemy:
            payload["alchemy"] = True
            
        if photoreal:
            payload["photoReal"] = True
            
            if photoreal_version:
                payload["photoRealVersion"] = photoreal_version
        
        # Image to Image guidance
        if init_image_id:
            payload["init_image_id"] = init_image_id
            
            if init_strength is not None:
                payload["init_strength"] = init_strength
        
        # Image from generated image
        if init_generation_image_id:
            payload["init_generation_image_id"] = init_generation_image_id
        
        # Image prompts
        if image_prompts:
            payload["imagePrompts"] = image_prompts
        
        # ControlNet / Image Guidance
        if controlnets:
            payload["controlnets"] = controlnets
        
        # Phoenix model specific parameters
        if is_phoenix:
            # Set isPhoenix flag only (model_id is already set)
            payload["isPhoenix"] = True
            
            if contrast is not None:
                payload["contrast"] = contrast
            
            # Remove any conflicting parameters
            payload.pop("photoReal", None)
            payload.pop("photoRealVersion", None)
        
        response = requests.post(f"{API_BASE_URL}/generations", 
                               headers=self.headers, 
                               json=payload)
        response.raise_for_status()
        return response.json()

    def get_generation(self, generation_id: str) -> Dict[str, Any]:
        """Get a specific generation by ID."""
        response = requests.get(f"{API_BASE_URL}/generations/{generation_id}", 
                              headers=self.headers)
        response.raise_for_status()
        return response.json()

    def wait_for_generation(self, generation_id: str, timeout: int = 120) -> Dict[str, Any]:
        """Wait for a generation to complete and return the result."""
        start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[yellow]Waiting for generation...", total=None)
            
            while time.time() - start_time < timeout:
                try:
                    generation = self.get_generation(generation_id)
                    status = generation.get("status", "")
                    
                    if status == "COMPLETE":
                        progress.update(task, description="[green]Generation complete!")
                        return generation
                    elif status == "FAILED":
                        progress.update(task, description="[red]Generation failed!")
                        raise Exception(f"Generation failed: {generation.get('error', 'Unknown error')}")
                    
                    # Update progress message
                    elapsed = int(time.time() - start_time)
                    progress.update(task, description=f"[yellow]Waiting for generation... ({elapsed}s)")
                    
                    # Wait before checking again
                    time.sleep(3)
                except Exception as e:
                    progress.update(task, description=f"[red]Error checking status: {str(e)}")
                    time.sleep(5)
            
            progress.update(task, description="[red]Generation timed out!")
            raise Exception(f"Generation timed out after {timeout} seconds")


def get_client(profile: str = None) -> LeonardoClient:
    """Get a configured Leonardo client with the specified or active profile."""
    # For now, we'll use environment variable or prompt for API key
    api_key = os.getenv('LEONARDO_API_KEY')
    
    if not api_key:
        console.print("[bold red]No API key found![/bold red]")
        console.print("Please set LEONARDO_API_KEY environment variable or run: leonardo-cli configure")
        sys.exit(1)
        
    return LeonardoClient(api_key)


@click.group()
def cli():
    """Leonardo AI command-line tool with advanced features."""
    pass


@cli.command()
@click.argument("prompt", nargs=-1, required=True)
@click.option("--model-id", help="The ID of the model to use")
@click.option("--num", default=1, help="Number of images to generate")
@click.option("--width", default=512, help="Width of the generated image")
@click.option("--height", default=512, help="Height of the generated image")
@click.option("--output-dir", default="./leonardo-output", help="Directory to save images")
@click.option("--timeout", default=120, help="Timeout in seconds to wait for generation")
@click.option("--negative-prompt", help="Negative prompt to specify what not to include")
@click.option("--guidance-scale", type=float, help="Guidance scale (default: 7.0)")
@click.option("--preset-style", help="Preset style (e.g., CINEMATIC, PHOTOGRAPHIC)")
@click.option("--alchemy/--no-alchemy", default=False, help="Enable Alchemy for better quality")
@click.option("--photoreal/--no-photoreal", default=False, help="Enable PhotoReal mode")
@click.option("--photoreal-version", help="PhotoReal version (e.g., 'v2')")
@click.option("--phoenix/--no-phoenix", default=False, help="Use Phoenix model")
@click.option("--contrast", type=float, help="Contrast value for Phoenix model (1.0-4.5)")
@click.option("--estimate-cost", is_flag=True, help="Estimate cost without generating")
def generate(prompt, model_id, num, width, height, output_dir, timeout, 
             negative_prompt, guidance_scale, preset_style, alchemy, photoreal, photoreal_version,
             phoenix, contrast, estimate_cost):
    """Generate images from a text prompt with advanced options."""
    # Convert prompt tuple to a single string
    prompt = " ".join(prompt)
    
    client = get_client()
    
    # Phoenix model settings
    if phoenix:
        if not contrast:
            contrast = 3.5  # Default contrast for Phoenix
        if alchemy and contrast < 2.5:
            console.print("[bold yellow]When using Phoenix with Alchemy, contrast must be 2.5 or higher. Setting to 2.5.[/bold yellow]")
            contrast = 2.5
        valid_contrasts = [1.0, 1.3, 1.8, 2.5, 3.0, 3.5, 4.0, 4.5]
        if contrast not in valid_contrasts:
            nearest = min(valid_contrasts, key=lambda x: abs(x - contrast))
            console.print(f"[bold yellow]Contrast value {contrast} is not valid for Phoenix. Using nearest valid value: {nearest}[/bold yellow]")
            contrast = nearest
        
        # Set Phoenix model ID
        model_id = "6b645e3a-d64f-4341-a6d8-7a3690fbf042"  # Leonardo Phoenix model ID
        console.print(f"Using Phoenix model (ID: {model_id})")
    
    # If no model_id provided, get the default one
    if not model_id and not photoreal and not phoenix:
        with console.status("[bold blue]Fetching available models...[/bold blue]"):
            models_data = client.list_models()
            # Use the first available model as default
            models = models_data.get("models", [])
            if not models:
                console.print("[bold red]No models available![/bold red]")
                return
            model_id = models[0]["id"]
            console.print(f"Using model: [bold]{models[0]['name']}[/bold] ({model_id})")
    
    # Create the output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Show settings panel
    settings_table = Table(title="Generation Settings", show_header=False)
    settings_table.add_column("Setting", style="cyan")
    settings_table.add_column("Value", style="green")
    
    settings_table.add_row("Prompt", prompt)
    
    if phoenix:
        settings_table.add_row("Model", "Leonardo Phoenix")
        settings_table.add_row("Contrast", str(contrast))
    else:
        settings_table.add_row("Model ID", model_id if model_id else "None (using PhotoReal)" if photoreal else "None")
    
    settings_table.add_row("Size", f"{width}x{height}")
    settings_table.add_row("Count", str(num))
    
    if negative_prompt:
        settings_table.add_row("Negative Prompt", negative_prompt)
    
    if guidance_scale is not None:
        settings_table.add_row("Guidance Scale", str(guidance_scale))
    
    if preset_style:
        settings_table.add_row("Preset Style", preset_style)
    
    settings_table.add_row("Alchemy", "Enabled" if alchemy else "Disabled")
    
    if not phoenix:
        settings_table.add_row("PhotoReal", "Enabled" if photoreal else "Disabled")
        
        if photoreal and photoreal_version:
            settings_table.add_row("PhotoReal Version", photoreal_version)
    
    console.print(settings_table)
    
    # Generate the images
    console.print(f"[bold blue]Generating {num} image(s)...[/bold blue]")
    
    try:
        # Create the generation with advanced parameters
        response = client.create_generation(
            prompt=prompt, 
            model_id=model_id,
            num_images=num, 
            width=width, 
            height=height,
            negative_prompt=negative_prompt,
            guidance_scale=guidance_scale,
            preset_style=preset_style,
            alchemy=alchemy,
            photoreal=photoreal,
            photoreal_version=photoreal_version,
            is_phoenix=phoenix,
            contrast=contrast if phoenix else None
        )
        
        generation_id = response.get("sdGenerationJob", {}).get("generationId")
        
        if not generation_id:
            console.print("[bold red]Failed to start generation. No generation ID returned.[/bold red]")
            return
        
        console.print(f"Generation started with ID: [bold]{generation_id}[/bold]")
        
        # Wait for the generation to complete
        generation = client.wait_for_generation(generation_id, timeout)
        
        # Get the generated images
        images = generation.get("generations", [])
        if not images:
            console.print("[bold yellow]No images were generated.[/bold yellow]")
            return
        
        console.print(f"[bold green]Successfully generated {len(images)} image(s)![/bold green]")
        
        # Download and save the images
        for i, image in enumerate(images):
            image_url = image.get("url")
            image_id = image.get("id")
            
            if image_url:
                # Download the image
                response = requests.get(image_url)
                response.raise_for_status()
                
                # Save the image
                output_file = output_path / f"{generation_id}_{i}.png"
                with open(output_file, "wb") as f:
                    f.write(response.content)
                
                console.print(f"Image {i+1} saved to: [bold]{output_file}[/bold]")
                console.print(f"Image ID: [bold]{image_id}[/bold] (Use this ID for video or variations)")
            else:
                console.print(f"[bold yellow]Image {i+1} has no URL.[/bold yellow]")
    
    except Exception as e:
        console.print(f"[bold red]Error generating images: {str(e)}[/bold red]")


@cli.command()
def models():
    """List available AI models."""
    client = get_client()
    
    with console.status("[bold blue]Fetching available models...[/bold blue]"):
        models_data = client.list_models()
    
    table = Table(title="Available Models")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Description", style="magenta")
    
    for model in models_data.get("models", []):
        table.add_row(
            model.get("id", "N/A"),
            model.get("name", "N/A"),
            model.get("description", "N/A")
        )
    
    console.print(table)


@cli.command()
def user():
    """Get information about your account."""
    client = get_client()
    with console.status("[bold blue]Fetching user information...[/bold blue]"):
        user_info = client.get_user_info()
    
    # Create a rich table to display user info
    table = Table(title="User Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    user_data = user_info.get("user", {})
    
    table.add_row("User ID", user_data.get("id", "N/A"))
    table.add_row("Username", user_data.get("username", "N/A"))
    table.add_row("Email", user_data.get("email", "N/A"))
    
    console.print(table)


if __name__ == "__main__":
    cli()
