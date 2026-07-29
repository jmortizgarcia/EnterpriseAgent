from dataclasses import dataclass, field


@dataclass
class AgentState:
    messages: list[dict] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    current_provider: str = "claude"
