import re
import json

text = """
some text generate_diagram({"name": "rag-core-architecture", "content": "flowchart TD
    A-->B
    B-->C
"}) more text

and diagram generate_diagram({   "description": "Internal process of the Generative Synthesis Engine",   "type": "flowchart",   "code": "flowchart LR\n    subgraph C [Generative Synthesis Engine]" })
"""

def extract_diagram(match):
    try:
        # If the LLM output actual unescaped newlines inside the string, strict=False helps parse it.
        # But if it output `\n` literal characters, they are just parsed as `\n`.
        # However, another issue is if the JSON uses other keys.
        json_str = match.group(1)
        
        # Sometimes it's completely malformed and strict=False isn't enough.
        # Let's try to just do a regex extraction if json.loads fails.
        try:
            data = json.loads(json_str, strict=False)
            code = data.get('code', '') or data.get('content', '') or data.get('mermaid', '')
            if code:
                return f"\n```mermaid\n{code}\n```\n"
        except Exception as e:
            print("JSON fallback needed:", e)
            
            # Fallback: regex search for anything inside "code": "..." or "content": "..."
            # This is tricky because the value might have escaped quotes.
            # But usually it's the last key-value pair and goes till the end.
            code_match = re.search(r'"(?:code|content|mermaid)"\s*:\s*"(.*?)"\s*\}', json_str, re.DOTALL)
            if code_match:
                code = code_match.group(1)
                # Unescape some common things if needed
                code = code.replace('\\n', '\n').replace('\\"', '"')
                return f"\n```mermaid\n{code}\n```\n"
                
    except Exception as e:
        pass
    return match.group(0)

res = re.sub(r'generate_diagram\(\s*(\{.*?\})\s*\)', extract_diagram, text, flags=re.DOTALL)
print("Result:\n", res)
