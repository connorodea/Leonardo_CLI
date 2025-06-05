import re

# Path to the file
file_path = 'leonardo_cli.py'

# Read the file
with open(file_path, 'r') as f:
    content = f.read()

# 1. Fix the extra parenthesis in the Phoenix model ID line
content = re.sub(r'console\.print$$f"Using Phoenix model \(ID: \{model_id\}$$"\)\)', 
                 r'console.print(f"Using Phoenix model (ID: {model_id}")', 
                 content)

# 2. Fix duplicated Phoenix model handling code
phoenix_code = '''        # Phoenix model specific parameters
        if is_phoenix:
            # Set isPhoenix flag only (model_id is already set)
            payload["isPhoenix"] = True
            
            if contrast is not None:
                payload["contrast"] = contrast
            
            # Remove any conflicting parameters
            payload.pop("photoReal", None)
            payload.pop("photoRealVersion", None)'''

# Replace the entire Phoenix model section with the clean version
content = re.sub(r'# Phoenix model specific parameters.*?payload\.pop$$"photoRealVersion", None$$((\s+# Remove.*?\))*)',
                 phoenix_code,
                 content,
                 flags=re.DOTALL)

# 3. Fix the list_models function's nested exception blocks
list_models_func = '''    def list_models(self) -> Dict[str, Any]:
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
                return {"models": []}'''

content = re.sub(r'def list_models.*?return {"models": \[\]}',
                list_models_func,
                content,
                flags=re.DOTALL)

# 4. Fix newline issues in the shell function's input function
content = re.sub(r'command = input$$"(\s*)\[leonardo-cli\]> "$$',
                 r'command = input("[leonardo-cli]> ")',
                 content)

# 5. Fix newline issues in the shell function's console.print calls
content = re.sub(r'console\.print$$"(\s*)\[bold cyan\]Available Commands:\[/bold cyan\]"$$',
                 r'console.print("[bold cyan]Available Commands:[/bold cyan]")',
                 content)

content = re.sub(r'console\.print$$"(\s*)\[bold yellow\]Operation aborted\.\[/bold yellow\]"$$',
                 r'console.print("[bold yellow]Operation aborted.[/bold yellow]")',
                 content)

# Save the fixed content
with open(file_path, 'w') as f:
    f.write(content)

print("Fixed syntax errors and removed duplicate code!")
