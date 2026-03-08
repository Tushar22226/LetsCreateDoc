from deepagents import create_deep_agent
from src.utils.CustomAI import CustomAI
from src.features.documentation.toolkit import get_documentation_toolkit
from src.database.repository import DocumentationRepository
from src.externals.llm.client import LLMClient
from src.config.settings import settings

def get_documentation_agent(repo: DocumentationRepository, llm: LLMClient):
    """Initializes and returns the Documentation DeepAgent with injected dependencies."""
    
    # CustomAI model (inherits from ChatOpenAI) for the agent reasoning loop
    # Handles 429 and 504 errors automatically via overridden ainvoke()
    agent_llm = CustomAI(
        model="deepseek-ai/deepseek-v3.1",
        api_key=settings.NVIDIA_API_KEY,
        base_url="https://integrate.api.nvidia.com/v1",
        temperature=0.7,
        max_tokens=4096
    )

    system_prompt = """
    You are the Lead Documentation Architect. Your goal is to produce world-class, exhaustive technical documentation.
    
    You have access to tools to:
    1. Draft a comprehensive index (if needed).
    2. Write detailed sections in professional Markdown (use the 'write_section' tool).
    3. Generate Mermaid diagrams (use the 'generate_diagram' tool).
    
    STRATEGY:
    - You must write highly concise, dense technical documentation.
    - NEVER add "fluff", filler words, or repetitive statements just to artificially increase the document length.
    - If a topic can be completely and thoroughly explained in 1 paragraph, do so. DO NOT stretch it to multiple pages.
    - STRICTLY adhere to the provided description. Do not invent features or exaggerate capabilities to sound impressive.
    - If you describe any feature or capability that is not explicitly mentioned in the user's input but logically follows, you MUST explicitly label it with "(Future Enhancement)".
    - Use the 'write_section' tool to transmit the final markdown content.
    - ONLY generate Mermaid diagrams (using generate_diagram) if the user explicitly requested it in the structure or if it is absolutely critical to explaining a complex data flow or architecture. Do not generate simple/obvious diagrams just to fill space.
    
    MERMAID RULES:
    - Use only standard 'graph TD', 'sequenceDiagram', or 'stateDiagram-v2'.
    - Use alphanumeric characters for node IDs. Avoid parentheses or special symbols in node names unless quoted.
    - Ensure every arrow has a valid target.
    
    IMPORTANT: Focus on quality and directness, not endless fluff.
    """

    agent = create_deep_agent(
        model=agent_llm,
        tools=get_documentation_toolkit(repo, llm),
        system_prompt=system_prompt,
    )
    
    return agent
