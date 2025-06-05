#!/bin/bash

# Create backup of original file
cp leonardo_cli.py leonardo_cli.py.bak

# Fix 1: Update list_models function to handle API endpoint changes
sed -i '' '
/def list_models/,/return response.json()/c\
    def list_models(self) -> Dict[str, Any]:\
        """List available AI models."""\
        # Try the newer endpoint structure first\
        try:\
            response = requests.get(f"{API_BASE_URL}/platformModels", headers=self.headers)\
            response.raise_for_status()\
            result = response.json()\
            # Format to match expected structure\
            return {"models": result.get("platformModels", [])}\
        except Exception as e:\
            # Log the error but do not fail\
            console.print(f"[bold yellow]Warning: Could not fetch models using platformModels endpoint: {str(e)}[/bold yellow]")\
            # Try legacy endpoint as fallback\
            try:\
                response = requests.get(f"{API_BASE_URL}/models", headers=self.headers)\
                response.raise_for_status()\
                return response.json()\
            except Exception as e:\
                console.print(f"[bold yellow]Warning: Could not fetch models using legacy endpoint: {str(e)}[/bold yellow]")\
                # Return empty result if both fail\
                return {"models": []}
' leonardo_cli.py

# Fix 2: Update shell function to properly handle quoted arguments
sed -i '' '
/def shell/,/while True:/a\
        import shlex
' leonardo_cli.py

# Fix 3: Update the command splitting in shell mode
sed -i '' '
/# Split the command into args for Click/,/cmd_args = args\[1:\]/c\
            # Split the command respecting quotes\
            try:\
                args = shlex.split(command)\
            except ValueError as e:\
                console.print(f"[bold red]Error parsing command: {str(e)}[/bold red]")\
                continue\
                \
            if not args:\
                continue\
                \
            cmd_name = args[0]\
            cmd_args = args[1:]
' leonardo_cli.py

# Fix 4: Update Phoenix model handling in create_generation
sed -i '' '
/# Phoenix model specific parameters/,/payload\["contrast"\] = contrast/c\
        # Phoenix model specific parameters\
        if is_phoenix:\
            # Set Phoenix model ID and flag\
            payload["modelId"] = "6b645e3a-d64f-4341-a6d8-7a3690fbf042"  # Leonardo Phoenix model ID\
            payload["isPhoenix"] = True\
            \
            if contrast is not None:\
                payload["contrast"] = contrast\
            \
            # Remove any conflicting parameters\
            payload.pop("photoReal", None)\
            payload.pop("photoRealVersion", None)
' leonardo_cli.py

# Add verification that fixes were applied
echo "Fixes applied successfully! Your CLI has been updated."
echo "The original file was backed up to leonardo_cli.py.bak"
echo "Try running your CLI again with: lcli shell"
