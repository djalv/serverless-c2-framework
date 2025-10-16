from rich.console import Console
from rich.table import Table
from rich.panel import Panel


def print_agents_table(agents_list: list):
    if not agents_list:
        print("[ERROR] No agents found.")
        return

    console = Console()
    table = Table(title="Agents", show_header=True, header_style="bold cyan")

    table.add_column("Agent ID", style="dim", width=36)
    table.add_column("Last Seen", justify="left")
    table.add_column("Hostname", justify="left")
    table.add_column("Source IP", justify="left")

    for agent in agents_list:
        agent_id = agent.get("agentId", "N/A")
        last_seen = agent.get("lastSeen", "N/A")
        hostname = agent.get("hostname", "N/A")
        source_ip = agent.get("sourceIp", "N/A")

        table.add_row(agent_id, last_seen, hostname, source_ip)

    console.print(table)


def print_task_result(result_content: str, agent_id: str):
    console = Console()

    result_panel = Panel.fit(
        result_content,
        title=f"Agent's Result {agent_id}",
        border_style="green",
        padding=(1, 2),
    )

    console.print(result_panel)
