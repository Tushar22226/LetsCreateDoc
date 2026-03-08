import re

text1 = "some text | Task | Manual Research | Time | |---|---|---| | Case law | 4 hrs | 85% | more text"
# The table is all in one line. A pipe table should have newlines before and after, and after each row.
# But distinguishing rows is hard if they are just pipe-separated. 
# Usually, a row ends before the next pipe-started segment? Wait, in user's example:
# | Task | Manual Research | RAG-assisted | Time Savings | |——|—————–|————–|————-| | Case law research | 4-6 hours | 15-30 minutes | 85-92% |
# Notice the ` | | ` pattern. The space between the pipes means it's a new row.

text2 = "some text generate_diagram({ \"description\": \"Internal process\", \"type\": \"flowchart\", \"code\": \"flowchart LR...\" }) more text"
# We want to match generate_diagram({...}) and remove it, or convert it.
# Actually, if the AI is leaking `generate_diagram({...})`, we might want to extract the code and actually render it!
match = re.search(r'generate_diagram\(\s*(\{.*?\})\s*\)', text2, re.DOTALL)
if match:
    import json
    try:
        data = json.loads(match.group(1))
        print("Diagram code found:", data.get('code'))
    except:
        print("Failed to parse JSON")

