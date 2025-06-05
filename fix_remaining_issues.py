import os
import re

# Path to the CLI script
script_path = 'leonardo_cli.py'

# Read the file content
with open(script_path, 'r') as f:
    content = f.read()

# FIX 1: Update the list_models function to handle API endpoint changes
list_models_func = '''
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
'''

# Find and replace the list_models function
pattern_list_models = r'def list_models.*?return response\.json$$$$'
content = re.sub(pattern_list_models, list_models_func.strip(), content, flags=re.DOTALL)

# FIX 2: Fix the generate command to properly handle arguments
generate_command = '''
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
'''

# Find and replace the generate command function signature
pattern_generate = r'@cli\.command$$$$\n@click\.argument$$"prompt"$$.*?def generate$$.*?$$:'
content = re.sub(pattern_generate, generate_command, content, flags=re.DOTALL)

# FIX 3: Update the Phoenix model handling
phoenix_model_code = '''
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
        
        # Set Phoenix model ID (directly here, not in API payload)
        model_id = "6b645e3a-d64f-4341-a6d8-7a3690fbf042"  # Leonardo Phoenix model ID
        console.print(f"Using Phoenix model (ID: {model_id})")
'''

# Insert the updated Phoenix model handling
phoenix_pattern = r'# Phoenix model settings.*?valid_contrasts.*?\)'
content = re.sub(phoenix_pattern, phoenix_model_code.strip(), content, flags=re.DOTALL)

# FIX 4: Update the create_generation function's Phoenix handling
phoenix_api_code = '''
        # Phoenix model specific parameters
        if is_phoenix:
            # Set isPhoenix flag only (model_id is already set)
            payload["isPhoenix"] = True
            
            if contrast is not None:
                payload["contrast"] = contrast
            
            # Remove any conflicting parameters
            payload.pop("photoReal", None)
            payload.pop("photoRealVersion", None)
'''

# Replace the Phoenix-specific code in create_generation
phoenix_api_pattern = r'# Phoenix model specific parameters.*?payload\["contrast"\] = contrast'
content = re.sub(phoenix_api_pattern, phoenix_api_code.strip(), content, flags=re.DOTALL)

# Write back the updated content
with open(script_path, 'w') as f:
    f.write(content)

print("Fixed remaining issues in Leonardo CLI!")
print("1. Updated model listing to handle API endpoint changes")
print("2. Fixed the generate command to handle multi-word prompts")
print("3. Updated Phoenix model handling")
