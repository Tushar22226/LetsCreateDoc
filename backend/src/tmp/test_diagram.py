import asyncio
import os
import sys

# Add the project root to sys.path so we can import src modules
sys.path.append(os.path.abspath('/home/tushar/LetsCreateDoc/backend'))

from src.externals.diagram.generator import diagram_generator

async def main():
    # Example Mermaid Flowchart
    mermaid_code = """
    flowchart LR
        A[Start] --> B{Decision}
        B -->|Yes| C[Process]
        B -->|No| D[End]
        C --> D
    """
    
    print("Testing DiagramGenerator...")
    print(f"Mermaid Code:\n{mermaid_code}")
    
    try:
        # Generate the image bytes
        image_bytes = await diagram_generator.generate_image(mermaid_code.strip())
        
        if image_bytes:
            output_path = "/home/tushar/LetsCreateDoc/backend/src/tmp/test_output.png"
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            print(f"✅ Success! Image saved to {output_path}")
        else:
            print("❌ Failed: generate_image returned None or empty bytes.")
            
    except Exception as e:
        print(f"❌ Error during generation: {e}")

if __name__ == "__main__":
    asyncio.run(main())
