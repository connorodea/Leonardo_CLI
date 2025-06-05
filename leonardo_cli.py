#!/Users/connorodea/.venv/leonardo-cli/bin/python
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
        
    def upload_init_image(self, image_path: str) -> Dict[str, Any]:
        """Upload an image to use as initialization for generation or motion."""
        # Get file extension
        file_ext = os.path.splitext(image_path)[1][1:].lower()
        if file_ext not in ["png", "jpg", "jpeg", "webp"]:
            raise ValueError(f"Unsupported file extension: {file_ext}. Only png, jpg, jpeg, and webp are supported.")
        
        # Step 1: Get a presigned URL for uploading
        response = requests.post(
            f"{API_BASE_URL}/init-image", 
            headers=self.headers,
            json={"extension": file_ext}
        )
        response.raise_for_status()
        
        upload_data = response.json()
        
        # Step 2: Upload the image to the presigned URL
        with open(image_path, "rb") as f:
            image_data = f.read()
            
        # Extract the upload URL and fields
        upload_url = upload_data.get("uploadInitImage", {}).get("url", "")
        upload_fields = upload_data.get("uploadInitImage", {}).get("fields", {})
        
        # Prepare the form data for upload
        files = {'file': ('image.' + file_ext, image_data)}
        
        # Convert fields to form data
        form_data = {}
        for key, value in upload_fields.items():
            form_data[key] = value
        
        # Upload the image (no auth headers needed)
        upload_response = requests.post(
            upload_url,
            data=form_data,
            files=files
        )
        
        # Check response (should be 204 No Content)
        if upload_response.status_code != 204:
            raise Exception(f"Failed to upload image: {upload_response.text}")
        
        # Return the image ID
        return {
            "id": upload_data.get("uploadInitImage", {}).get("id", ""),
            "key": upload_data.get("uploadInitImage", {}).get("key", "")
        }
    
    def create_motion_generation(self, image_id: str, motion_strength: int = 3, 
                                is_init_image: bool = False) -> Dict[str, Any]:
        """Generate a motion video from an image using SVD."""
        payload = {
            "imageId": image_id,
            "motionStrength": motion_strength,
            "isInitImage": is_init_image,
            "isPublic": True  # Can be made configurable if needed
        }
        
        response = requests.post(
            f"{API_BASE_URL}/generations-motion-svd",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def get_motion_generation(self, generation_id: str) -> Dict[str, Any]:
        """Get information about a motion generation."""
        response = requests.get(
            f"{API_BASE_URL}/generations-motion-svd/{generation_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_motion_generation(self, generation_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for a motion generation to complete and return the result."""
        start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[yellow]Waiting for video generation...", total=None)
            
            while time.time() - start_time < timeout:
                try:
                    generation = self.get_motion_generation(generation_id)
                    status = generation.get("status", "")
                    
                    if status == "COMPLETE":
                        progress.update(task, description="[green]Video generation complete!")
                        return generation
                    elif status == "FAILED":
                        progress.update(task, description="[red]Video generation failed!")
                        raise Exception(f"Generation failed: {generation.get('error', 'Unknown error')}")
                    
                    # Update progress message
                    elapsed = int(time.time() - start_time)
                    progress.update(task, description=f"[yellow]Waiting for video generation... ({elapsed}s)")
                    
                    # Wait before checking again
                    time.sleep(3)
                except Exception as e:
                    progress.update(task, description=f"[red]Error checking status: {str(e)}")
                    time.sleep(5)
            
            progress.update(task, description="[red]Video generation timed out!")
            raise Exception(f"Motion generation timed out after {timeout} seconds")
    
    def create_image_variation(self, image_id: str, variation_type: str = "upscale", 
                              is_variation: bool = False) -> Dict[str, Any]:
        """Create a variation of an existing image (upscale, unzoom, etc.)."""
        # Supported variation types: "upscale", "unzoom", "no_background"
        endpoint = f"{API_BASE_URL}/variations/{variation_type}"
        
        payload = {
            "id": image_id,
            "isVariation": is_variation  # Set to True if image_id is from a previous variation
        }
        
        response = requests.post(endpoint, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()
        
    def get_variation(self, variation_id: str, variation_type: str = "upscale") -> Dict[str, Any]:
        """Get information about an image variation by ID."""
        endpoint = f"{API_BASE_URL}/variations/{variation_type}/{variation_id}"
        
        response = requests.get(endpoint, headers=self.headers)
        response.raise_for_status()
        return response.json()
        
    def wait_for_variation(self, variation_id: str, variation_type: str = "upscale", timeout: int = 120) -> Dict[str, Any]:
        """Wait for an image variation to complete and return the result."""
        start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"[yellow]Waiting for {variation_type} to complete...", total=None)
            
            while time.time() - start_time < timeout:
                try:
                    variation = self.get_variation(variation_id, variation_type)
                    status = variation.get("status", "")
                    
                    if status == "COMPLETE":
                        progress.update(task, description=f"[green]{variation_type.capitalize()} complete!")
                        return variation
                    elif status == "FAILED":
                        progress.update(task, description=f"[red]{variation_type.capitalize()} failed!")
                        raise Exception(f"Variation failed: {variation.get('error', 'Unknown error')}")
                    
                    # Update progress message
                    elapsed = int(time.time() - start_time)
                    progress.update(task, description=f"[yellow]Waiting for {variation_type} to complete... ({elapsed}s)")
                    
                    # Wait before checking again
                    time.sleep(3)
                except Exception as e:
                    progress.update(task, description=f"[red]Error checking status: {str(e)}")
                    time.sleep(5)
            
            progress.update(task, description=f"[red]{variation_type.capitalize()} timed out!")
            raise Exception(f"Variation timed out after {timeout} seconds")

    def calculate_pricing(self, service_params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate pricing for a service."""
        payload = {
            "service": "IMAGE_GENERATION",
            "serviceParams": {
                "IMAGE_GENERATION": service_params
            }
        }
        
        response = requests.post(
            f"{API_BASE_URL}/pricing-calculator",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()


class TemplateManager:
    """Manage prompt templates for easy reuse."""
    
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
    
    @classmethod
    def load_template(cls, name: str) -> Optional[Dict[str, Any]]:
        """Load a template from disk."""
        template_path = os.path.join(cls.TEMPLATES_DIR, f"{name}.json")
        
        if not os.path.exists(template_path):
            return None
        
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


def ensure_config_dir():
    """Ensure the config directory exists."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)


def save_config(api_key: str, profile: str = "default"):
    """Save the API key to the config file with optional profile name."""
    ensure_config_dir()
    
    # Load existing config if it exists
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                config = {}
    
    # Initialize profiles section if it doesn't exist
    if "profiles" not in config:
        config["profiles"] = {}
    
    # Add or update the profile
    config["profiles"][profile] = {"api_key": api_key}
    
    # Set as active profile
    config["active_profile"] = profile
    
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def load_config() -> Optional[Dict[str, Any]]:
    """Load the config from file if it exists."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return None
    return None


def get_active_profile() -> str:
    """Get the name of the active profile from config."""
    config = load_config()
    if config and "active_profile" in config:
        return config["active_profile"]
    return "default"


def get_api_key(profile: str = None) -> Optional[str]:
    """Get the API key from the specified or active profile."""
    config = load_config()
    
    if not config or "profiles" not in config:
        return None
    
    # Use the specified profile or the active one
    profile_name = profile or config.get("active_profile", "default")
    
    # Get the profile
    profile_data = config["profiles"].get(profile_name)
    
    if not profile_data:
        return None
    
    return profile_data.get("api_key")


def get_client(profile: str = None) -> LeonardoClient:
    """Get a configured Leonardo client with the specified or active profile."""
    api_key = get_api_key(profile)
    
    if not api_key:
        console.print("[bold red]No API key configured![/bold red]")
        console.print("Please run: leonardo-cli configure")
        sys.exit(1)
        
    return LeonardoClient(api_key)


@click.group()
def cli():
    """Leonardo AI command-line tool with advanced features."""
    pass


@cli.command()
@click.option("--api-key", prompt="Enter your Leonardo AI API key", 
              help="Your Leonardo AI API key")
@click.option("--profile", default="default", help="Profile name to store the API key under")
def configure(api_key, profile):
    """Configure the CLI with your API key and optional profile name."""
    save_config(api_key, profile)
    console.print(f"[bold green]Configuration saved under profile '[italic]{profile}[/italic]'![/bold green]")
    
    # Test the API key
    client = LeonardoClient(api_key)
    try:
        user_info = client.get_user_info()
        console.print(f"[bold green]API key verified successfully![/bold green]")
        console.print(f"Logged in as: {user_info.get('user', {}).get('username', 'Unknown')}")
    except Exception as e:
        console.print(f"[bold red]Error verifying API key: {str(e)}[/bold red]")


@cli.command()
def profiles():
    """List available configuration profiles."""
    config = load_config()
    
    if not config or "profiles" not in config or not config["profiles"]:
        console.print("[bold yellow]No profiles configured. Run 'leonardo-cli configure' to create one.[/bold yellow]")
        return
    
    active_profile = config.get("active_profile", "default")
    
    table = Table(title="Configuration Profiles")
    table.add_column("Profile", style="cyan")
    table.add_column("API Key", style="green")
    table.add_column("Active", style="magenta")
    
    for profile_name, profile_data in config["profiles"].items():
        # Mask the API key for security
        api_key = profile_data.get("api_key", "")
        masked_key = f"{api_key[:8]}...{api_key[-8:]}" if len(api_key) > 16 else "********"
        
        is_active = "✓" if profile_name == active_profile else ""
        
        table.add_row(profile_name, masked_key, is_active)
    
    console.print(table)


@cli.command()
@click.argument("profile")
def use_profile(profile):
    """Set the active profile to use for API calls."""
    config = load_config()
    
    if not config or "profiles" not in config:
        console.print("[bold red]No profiles configured. Run 'leonardo-cli configure' first.[/bold red]")
        return
    
    if profile not in config["profiles"]:
        console.print(f"[bold red]Profile '{profile}' not found. Available profiles:[/bold red]")
        for p in config["profiles"].keys():
            console.print(f"  - {p}")
        return
    
    # Update the active profile
    config["active_profile"] = profile
    
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    
    console.print(f"[bold green]Now using profile: [italic]{profile}[/italic][/bold green]")


@cli.command()
@click.argument("profile")
def delete_profile(profile):
    """Delete a configuration profile."""
    config = load_config()
    
    if not config or "profiles" not in config:
        console.print("[bold red]No profiles configured.[/bold red]")
        return
    
    if profile not in config["profiles"]:
        console.print(f"[bold red]Profile '{profile}' not found.[/bold red]")
        return
    
    # Remove the profile
    del config["profiles"][profile]
    
    # If we deleted the active profile, switch to another one
    if config.get("active_profile") == profile:
        if config["profiles"]:
            config["active_profile"] = next(iter(config["profiles"].keys()))
        else:
            config.pop("active_profile", None)
    
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    
    console.print(f"[bold green]Profile '[italic]{profile}[/italic]' deleted.[/bold green]")
    
    if "active_profile" in config:
        console.print(f"Active profile is now: [italic]{config['active_profile']}[/italic]")


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
    
    # Add subscription info
    subscription = user_info.get("subscription", {})
    if subscription:
        table.add_row("Subscription Plan", subscription.get("plan", "N/A"))
        table.add_row("Tokens Remaining", str(subscription.get("tokensRemaining", "N/A")))
        table.add_row("Total Tokens", str(subscription.get("totalTokens", "N/A")))
        table.add_row("Tokens Used", str(subscription.get("tokensUsed", "N/A")))
        table.add_row("Next Renewal", subscription.get("nextRenewalDate", "N/A"))
    
    console.print(table)
    
    # Show usage chart if available
    if subscription and "tokensUsed" in subscription and "totalTokens" in subscription:
        tokens_used = subscription["tokensUsed"]
        total_tokens = subscription["totalTokens"]
        
        if total_tokens > 0:
            usage_percent = (tokens_used / total_tokens) * 100
            bar_width = 50
            filled_width = int((tokens_used / total_tokens) * bar_width)
            
            usage_bar = f"[{'#' * filled_width}{' ' * (bar_width - filled_width)}] {usage_percent:.1f}%"
            console.print("\n[bold]Token Usage:[/bold]")
            console.print(usage_bar)


@cli.command()
@click.option("--all", is_flag=True, help="Show all models, including platform and custom")
def models(all):
    """List available AI models."""
    client = get_client()
    
    if all:
        # Fetch platform models
        with console.status("[bold blue]Fetching platform models...[/bold blue]"):
            try:
                platform_models_data = client.list_platform_models()
                platform_models = platform_models_data.get("platformModels", [])
            except Exception as e:
                console.print(f"[bold yellow]Could not fetch platform models: {str(e)}[/bold yellow]")
                platform_models = []
        
        # Fetch custom models
        with console.status("[bold blue]Fetching custom models...[/bold blue]"):
            try:
                custom_models_data = client.list_custom_models()
                custom_models = custom_models_data.get("loras", [])
            except Exception as e:
                console.print(f"[bold yellow]Could not fetch custom models: {str(e)}[/bold yellow]")
                custom_models = []
        
        # Show platform models
        if platform_models:
            table = Table(title="Platform Models")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Description", style="magenta")
            
            for model in platform_models:
                table.add_row(
                    model.get("id", "N/A"),
                    model.get("name", "N/A"),
                    model.get("description", "N/A")
                )
            
            console.print(table)
        
        # Show custom models
        if custom_models:
            table = Table(title="Custom Models")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Status", style="magenta")
            
            for model in custom_models:
                table.add_row(
                    model.get("id", "N/A"),
                    model.get("name", "N/A"),
                    model.get("status", "N/A")
                )
            
            console.print(table)
        
        if not platform_models and not custom_models:
            console.print("[bold yellow]No models found.[/bold yellow]")
    else:
        # Use the standard list_models endpoint for backward compatibility
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

    """Generate images from a text prompt with advanced options."""
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
    
    # Phoenix model ID
    if phoenix:
        model_id = "6b645e3a-d64f-4341-a6d8-7a3690fbf042"  # Leonardo Phoenix model ID
        console.print(f"Using Phoenix model (ID: {model_id})")
    
    # Estimate cost if requested
    if estimate_cost:
        with console.status("[bold blue]Estimating cost...[/bold blue]"):
            # Prepare parameters for price calculation
            params = {
                "imageHeight": height,
                "imageWidth": width,
                "numImages": num,
                "inferenceSteps": 30,  # Default
                "promptMagic": False,
                "alchemyMode": alchemy,
                "highResolution": False,  # Not exposed in options
                "isModelCustom": False,  # Assuming platform model
                "isSDXL": False,  # Not determining this yet
                "isPhoenix": phoenix
            }
            
            try:
                pricing = client.calculate_pricing(params)
                cost = pricing.get("cost", 0)
                console.print(f"[bold green]Estimated cost: {cost} credits[/bold green]")
                
                # Ask for confirmation
                if not click.confirm("Do you want to proceed with the generation?"):
                    console.print("[bold yellow]Generation cancelled.[/bold yellow]")
                    return
            except Exception as e:
                console.print(f"[bold yellow]Could not estimate cost: {str(e)}[/bold yellow]")
                # Continue with generation if user wants
                if not click.confirm("Continue with generation anyway?"):
                    console.print("[bold yellow]Generation cancelled.[/bold yellow]")
                    return
    
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
@click.option("--init-image-path", type=click.Path(exists=True), help="Path to initial image")
@click.option("--init-prompt", help="The prompt for the modified image")
@click.option("--init-strength", type=float, default=0.5, help="Strength of initial image influence (0.0-1.0)")
@click.option("--model-id", help="The ID of the model to use")
@click.option("--width", default=512, help="Width of the generated image")
@click.option("--height", default=512, help="Height of the generated image")
@click.option("--output-dir", default="./leonardo-output", help="Directory to save images")
@click.option("--timeout", default=120, help="Timeout in seconds to wait for generation")
@click.option("--negative-prompt", help="Negative prompt to specify what not to include")
@click.option("--guidance-scale", type=float, help="Guidance scale (default: 7.0)")
@click.option("--preset-style", help="Preset style (e.g., CINEMATIC, PHOTOGRAPHIC)")
@click.option("--alchemy/--no-alchemy", default=False, help="Enable Alchemy for better quality")
def img2img(init_image_path, init_prompt, init_strength, model_id, width, height,
           output_dir, timeout, negative_prompt, guidance_scale, preset_style, alchemy):
    """Generate images from an initial image with a prompt (Image-to-Image)."""
    client = get_client()
    
    if not init_image_path:
        console.print("[bold red]Error: Initial image path is required![/bold red]")
        return
    
    if not init_prompt:
        console.print("[bold red]Error: Initial prompt is required![/bold red]")
        return
    
    # If no model_id provided, get the default one
    if not model_id:
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
    
    # Upload the initial image
    console.print(f"[bold blue]Uploading initial image: {init_image_path}[/bold blue]")
    with console.status("[bold blue]Uploading image...[/bold blue]"):
        upload_result = client.upload_init_image(init_image_path)
    
    init_image_id = upload_result.get("id")
    if not init_image_id:
        console.print("[bold red]Failed to upload initial image![/bold red]")
        return
    
    console.print(f"[bold green]Image uploaded successfully with ID: {init_image_id}[/bold green]")
    
    # Show settings panel
    settings_table = Table(title="Image-to-Image Generation Settings", show_header=False)
    settings_table.add_column("Setting", style="cyan")
    settings_table.add_column("Value", style="green")
    
    settings_table.add_row("Initial Image", init_image_path)
    settings_table.add_row("Prompt", init_prompt)
    settings_table.add_row("Init Strength", str(init_strength))
    settings_table.add_row("Model ID", model_id)
    settings_table.add_row("Size", f"{width}x{height}")
    
    if negative_prompt:
        settings_table.add_row("Negative Prompt", negative_prompt)
    
    if guidance_scale is not None:
        settings_table.add_row("Guidance Scale", str(guidance_scale))
    
    if preset_style:
        settings_table.add_row("Preset Style", preset_style)
    
    settings_table.add_row("Alchemy", "Enabled" if alchemy else "Disabled")
    
    console.print(settings_table)
    
    # Generate the image
    console.print(f"[bold blue]Generating image from initial image...[/bold blue]")
    
    try:
        # Create the generation with image-to-image parameters
        response = client.create_generation(
            prompt=init_prompt, 
            model_id=model_id,
            num_images=1, 
            width=width, 
            height=height,
            negative_prompt=negative_prompt,
            guidance_scale=guidance_scale,
            preset_style=preset_style,
            alchemy=alchemy,
            init_image_id=init_image_id,
            init_strength=init_strength
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
                output_file = output_path / f"img2img_{generation_id}_{i}.png"
                with open(output_file, "wb") as f:
                    f.write(response.content)
                
                console.print(f"Image saved to: [bold]{output_file}[/bold]")
                console.print(f"Image ID: [bold]{image_id}[/bold] (Use this ID for video or variations)")
            else:
                console.print(f"[bold yellow]Image has no URL.[/bold yellow]")
    
    except Exception as e:
        console.print(f"[bold red]Error generating image: {str(e)}[/bold red]")


@cli.command()
@click.option("--init-image-path", type=click.Path(exists=True), help="Path to style/content reference image")
@click.option("--init-image-id", help="ID of a previously generated/uploaded image to use as reference")
@click.option("--preprocessor-id", required=True, type=int, 
              help="ControlNet preprocessor ID (e.g., 67 for Style Reference, 133 for Character Reference)")
@click.option("--init-image-type", type=click.Choice(["UPLOADED", "GENERATED"]), default="UPLOADED",
              help="Type of image reference (UPLOADED or GENERATED)")
@click.option("--strength", type=click.Choice(["Low", "Mid", "High", "Ultra", "Max"]), default="High",
              help="Strength of influence (Low, Mid, High, Ultra, Max)")
@click.option("--prompt", required=True, help="The generation prompt")
@click.option("--model-id", required=True, help="The ID of the model to use")
@click.option("--width", default=512, help="Width of the generated image")
@click.option("--height", default=512, help="Height of the generated image")
@click.option("--output-dir", default="./leonardo-output", help="Directory to save images")
@click.option("--timeout", default=120, help="Timeout in seconds to wait for generation")
@click.option("--alchemy/--no-alchemy", default=True, help="Enable Alchemy for better quality")
@click.option("--preset-style", help="Preset style (e.g., CINEMATIC, PHOTOGRAPHIC)")
def image_guidance(init_image_path, init_image_id, preprocessor_id, init_image_type, strength,
                  prompt, model_id, width, height, output_dir, timeout, alchemy, preset_style):
    """Generate images using Image Guidance (ControlNet) features."""
    client = get_client()
    
    if not init_image_path and not init_image_id:
        console.print("[bold red]Error: Either --init-image-path or --init-image-id must be provided![/bold red]")
        return
    
    if init_image_path and init_image_id:
        console.print("[bold yellow]Warning: Both image path and ID provided. Using image ID.[/bold yellow]")
    
    # Create the output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Upload the image if path is provided
    if not init_image_id and init_image_path:
        console.print(f"[bold blue]Uploading image: {init_image_path}[/bold blue]")
        with console.status("[bold blue]Uploading image...[/bold blue]"):
            upload_result = client.upload_init_image(init_image_path)
        
        init_image_id = upload_result.get("id")
        if not init_image_id:
            console.print("[bold red]Failed to upload image![/bold red]")
            return
        
        console.print(f"[bold green]Image uploaded successfully with ID: {init_image_id}[/bold green]")
    
    # Prepare controlnets
    controlnets = [{
        "initImageId": init_image_id,
        "initImageType": init_image_type,
        "preprocessorId": preprocessor_id,
        "strengthType": strength
    }]
    
    # Show settings panel
    settings_table = Table(title="Image Guidance Generation Settings", show_header=False)
    settings_table.add_column("Setting", style="cyan")
    settings_table.add_column("Value", style="green")
    
    settings_table.add_row("Prompt", prompt)
    settings_table.add_row("Model ID", model_id)
    settings_table.add_row("Size", f"{width}x{height}")
    settings_table.add_row("Image ID", init_image_id)
    settings_table.add_row("Preprocessor ID", str(preprocessor_id))
    settings_table.add_row("Image Type", init_image_type)
    settings_table.add_row("Strength", strength)
    settings_table.add_row("Alchemy", "Enabled" if alchemy else "Disabled")
    
    if preset_style:
        settings_table.add_row("Preset Style", preset_style)
    
    console.print(settings_table)
    
    # Generate the image
    console.print(f"[bold blue]Generating image with Image Guidance...[/bold blue]")
    
    try:
        # Create the generation with image guidance parameters
        response = client.create_generation(
            prompt=prompt, 
            model_id=model_id,
            num_images=1, 
            width=width, 
            height=height,
            alchemy=alchemy,
            preset_style=preset_style,
            controlnets=controlnets
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
                output_file = output_path / f"guidance_{generation_id}_{i}.png"
                with open(output_file, "wb") as f:
                    f.write(response.content)
                
                console.print(f"Image saved to: [bold]{output_file}[/bold]")
                console.print(f"Image ID: [bold]{image_id}[/bold] (Use this ID for video or variations)")
            else:
                console.print(f"[bold yellow]Image has no URL.[/bold yellow]")
    
    except Exception as e:
        console.print(f"[bold red]Error generating image: {str(e)}[/bold red]")


@cli.command()
@click.option("--image-id", help="ID of a previously generated image", required=False)
@click.option("--image-path", help="Path to an image file to upload", required=False)
@click.option("--motion-strength", default=3, help="Strength of motion effect (1-5)")
@click.option("--output-dir", default="./leonardo-output", help="Directory to save video")
@click.option("--timeout", default=300, help="Timeout in seconds to wait for generation")
def video(image_id, image_path, motion_strength, output_dir, timeout):
    """Generate a video from an image using Leonardo's Motion feature."""
    client = get_client()
    
    if not image_id and not image_path:
        console.print("[bold red]Error: Either --image-id or --image-path must be provided![/bold red]")
        return
    
    if image_id and image_path:
        console.print("[bold yellow]Warning: Both image ID and path provided. Using image ID.[/bold yellow]")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Upload image if path is provided
        is_init_image = False
        if not image_id and image_path:
            console.print(f"[bold blue]Uploading image: {image_path}[/bold blue]")
            with console.status("[bold blue]Uploading image...[/bold blue]"):
                upload_result = client.upload_init_image(image_path)
            
            image_id = upload_result.get("id")
            is_init_image = True
            console.print(f"[bold green]Image uploaded successfully with ID: {image_id}[/bold green]")
        
        # Create the motion generation
        console.print(f"[bold blue]Creating video from image with motion strength: {motion_strength}[/bold blue]")
        response = client.create_motion_generation(image_id, motion_strength, is_init_image)
        
        generation_id = response.get("sdGenerationJob", {}).get("generationId")
        if not generation_id:
            console.print("[bold red]Failed to start video generation. No generation ID returned.[/bold red]")
            return
        
        console.print(f"Video generation started with ID: [bold]{generation_id}[/bold]")
        
        # Wait for the generation to complete
        generation = client.wait_for_motion_generation(generation_id, timeout)
        
        # Get the generated video
        video_url = generation.get("videoUrl")
        if not video_url:
            console.print("[bold yellow]No video URL returned in the response.[/bold yellow]")
            return
        
        console.print(f"[bold green]Video generated successfully![/bold green]")
        console.print(f"Video URL: [link={video_url}]{video_url}[/link]")
        
        # Download the video
        console.print("[bold blue]Downloading video...[/bold blue]")
        response = requests.get(video_url)
        response.raise_for_status()
        
        # Save the video
        output_file = output_path / f"{generation_id}.mp4"
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        console.print(f"[bold green]Video saved to: {output_file}[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Error generating video: {str(e)}[/bold red]")


@cli.command()
@click.argument("generation_id")
def status(generation_id):
    """Check the status of an image generation."""
    client = get_client()
    
    try:
        with console.status(f"[bold blue]Checking status of generation {generation_id}...[/bold blue]"):
            generation = client.get_generation(generation_id)
        
        status = generation.get("status", "UNKNOWN")
        console.print(f"Status: [bold]{status}[/bold]")
        
        if status == "COMPLETE":
            images = generation.get("generations", [])
            console.print(f"Generated {len(images)} image(s)")
            
            for i, image in enumerate(images):
                console.print(f"Image {i+1} URL: [link={image.get('url')}]{image.get('url')}[/link]")
                console.print(f"Image {i+1} ID: [bold]{image.get('id')}[/bold]")
    
    except Exception as e:
        console.print(f"[bold red]Error checking generation status: {str(e)}[/bold red]")


@cli.command()
@click.argument("generation_id")
def video_status(generation_id):
    """Check the status of a video generation."""
    client = get_client()
    
    try:
        with console.status(f"[bold blue]Checking status of video generation {generation_id}...[/bold blue]"):
            generation = client.get_motion_generation(generation_id)
        
        status = generation.get("status", "UNKNOWN")
        console.print(f"Status: [bold]{status}[/bold]")
        
        if status == "COMPLETE":
            video_url = generation.get("videoUrl")
            if video_url:
                console.print(f"Video URL: [link={video_url}]{video_url}[/link]")
            else:
                console.print("[bold yellow]No video URL found in the response.[/bold yellow]")
    
    except Exception as e:
        console.print(f"[bold red]Error checking video generation status: {str(e)}[/bold red]")


@cli.command()
@click.argument("image_id")
@click.option("--type", type=click.Choice(["upscale", "unzoom", "no_background"]), default="upscale",
              help="Type of variation to create")
@click.option("--is-variation", is_flag=True, help="Set to true if image_id is from a previous variation")
@click.option("--output-dir", default="./leonardo-output", help="Directory to save the result")
@click.option("--timeout", default=120, help="Timeout in seconds to wait for generation")
def variation(image_id, type, is_variation, output_dir, timeout):
    """Create a variation of an existing image (upscale, unzoom, remove background)."""
    client = get_client()
    
    # Create the output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    console.print(f"[bold blue]Creating {type} variation of image {image_id}...[/bold blue]")
    
    try:
        # Create the variation
        response = client.create_image_variation(image_id, type, is_variation)
        
        # Extract the variation ID (depends on the variation type)
        variation_id = None
        job_info = {}
        
        # Handle differences in API response format
        if type == "upscale":
            job_info = response.get("sdUpscaleJob", {})
        elif type == "unzoom":
            job_info = response.get("sdUnzoomJob", {})
        elif type == "no_background":
            job_info = response.get("noBackgroundJob", {})
        
        variation_id = job_info.get("id")
        
        if not variation_id:
            console.print("[bold red]Failed to start variation. No variation ID returned.[/bold red]")
            return
        
        console.print(f"Variation started with ID: [bold]{variation_id}[/bold]")
        
        # Wait for the variation to complete
        variation = client.wait_for_variation(variation_id, type, timeout)
        
        # Get the generated image URL
        image_url = variation.get("imageUrl") or variation.get("url")
        
        if not image_url:
            console.print("[bold yellow]No image URL found in the response.[/bold yellow]")
            return
        
        console.print(f"[bold green]Variation completed successfully![/bold green]")
        console.print(f"Image URL: [link={image_url}]{image_url}[/link]")
        
        # Download the image
        console.print("[bold blue]Downloading the result...[/bold blue]")
        response = requests.get(image_url)
        response.raise_for_status()
        
        # Save the image
        output_file = output_path / f"{variation_id}_{type}.png"
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        console.print(f"[bold green]Result saved to: {output_file}[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Error creating variation: {str(e)}[/bold red]")


@cli.command()
def usage():
    """Show API token usage for the current profile."""
    client = get_client()
    
    try:
        with console.status("[bold blue]Fetching usage information...[/bold blue]"):
            user_info = client.get_user_info()
        
        # Extract subscription data
        subscription = user_info.get("subscription", {})
        
        if not subscription:
            console.print("[bold yellow]No subscription information available.[/bold yellow]")
            return
        
        table = Table(title="API Token Usage")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        # Add subscription info
        table.add_row("Subscription Plan", subscription.get("plan", "N/A"))
        table.add_row("Tokens Remaining", str(subscription.get("tokensRemaining", "N/A")))
        table.add_row("Total Tokens", str(subscription.get("totalTokens", "N/A")))
        table.add_row("Tokens Used", str(subscription.get("tokensUsed", "N/A")))
        table.add_row("Next Renewal", subscription.get("nextRenewalDate", "N/A"))
        
        console.print(table)
        
        # Show usage chart if available
        if "tokensUsed" in subscription and "totalTokens" in subscription:
            tokens_used = subscription["tokensUsed"]
            total_tokens = subscription["totalTokens"]
            
            if total_tokens > 0:
                usage_percent = (tokens_used / total_tokens) * 100
                bar_width = 50
                filled_width = int((tokens_used / total_tokens) * bar_width)
                
                usage_bar = f"[{'#' * filled_width}{' ' * (bar_width - filled_width)}] {usage_percent:.1f}%"
                console.print("\n[bold]Token Usage:[/bold]")
                console.print(usage_bar)
    
    except Exception as e:
        console.print(f"[bold red]Error fetching usage information: {str(e)}[/bold red]")


@cli.command()
@click.option("--height", default=512, help="Image height")
@click.option("--width", default=512, help="Image width")
@click.option("--num", default=1, help="Number of images")
@click.option("--alchemy", is_flag=True, help="Enable Alchemy")
@click.option("--phoenix", is_flag=True, help="Use Phoenix model")
def estimate(height, width, num, alchemy, phoenix):
    """Estimate the cost of a generation without actually generating."""
    client = get_client()
    
    # Prepare parameters for price calculation
    params = {
        "imageHeight": height,
        "imageWidth": width,
        "numImages": num,
        "inferenceSteps": 30,  # Default
        "promptMagic": False,
        "alchemyMode": alchemy,
        "highResolution": False,  # Not exposed in options
        "isModelCustom": False,  # Assuming platform model
        "isSDXL": False,  # Not determining this yet
        "isPhoenix": phoenix
    }
    
    try:
        with console.status("[bold blue]Calculating cost...[/bold blue]"):
            pricing = client.calculate_pricing(params)
        
        cost = pricing.get("cost", 0)
        console.print(f"[bold green]Estimated cost: {cost} credits[/bold green]")
        
        # Show details
        table = Table(title="Cost Estimate Details")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Image Size", f"{width}x{height}")
        table.add_row("Number of Images", str(num))
        table.add_row("Alchemy Enabled", "Yes" if alchemy else "No")
        table.add_row("Phoenix Model", "Yes" if phoenix else "No")
        table.add_row("Total Cost", f"{cost} credits")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error calculating cost: {str(e)}[/bold red]")


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
            command = input("[leonardo-cli]> ")
            
            # Handle shell-specific commands
            if command.lower() in ("exit", "quit"):
                console.print("[bold green]Exiting shell. Goodbye![/bold green]")
                break
            elif command.lower() == "help":
                console.print("[bold cyan]Available Commands:[/bold cyan]")
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
            console.print("[bold yellow]Operation aborted.[/bold yellow]")
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")
