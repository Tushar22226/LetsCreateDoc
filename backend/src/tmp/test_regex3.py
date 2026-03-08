import re
import json

text = """
some text generate_diagram({"name": "rag-core-architecture", "content": "flowchart TD
    A-->B
    B-->C
"}) more text
"""

def extract_diagram(match):
    try:
        # strict=False allows unescaped newlines inside strings
        data = json.loads(match.group(1), strict=False)
        code = data.get('code', '') or data.get('content', '') or data.get('mermaid', '')
        if code:
            return f"\n```mermaid\n{code}\n```\n"
    except Exception as e:
        print("JSON error:", e)
        # fallback, try to extract everything between {"content": " and "} if it's super broken
        pass
    return match.group(0)

res = re.sub(r'generate_diagram\(\s*(\{.*?\})\s*\)', extract_diagram, text, flags=re.DOTALL)
print("Result:\n", res)
