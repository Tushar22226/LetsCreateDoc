import re
import json

text = """
some text generate_diagram({"name": "rag-core-architecture", "content": "flowchart TD\n    A-->B\n    B-->C\n"}) more text
"""

def extract_diagram(match):
    try:
        data = json.loads(match.group(1))
        # Support various keys that the LLM might hallucinate
        code = data.get('code', '') or data.get('content', '') or data.get('mermaid', '')
        if code:
            return f"\n```mermaid\n{code}\n```\n"
    except Exception as e:
        print("JSON error:", e)
        pass
    return match.group(0)

res = re.sub(r'generate_diagram\(\s*(\{.*?\})\s*\)', extract_diagram, text, flags=re.DOTALL)
print(res)
