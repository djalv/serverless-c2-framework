from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule


def print_banner():
    AETHERIS_ART = r"""
 ▄▄▄      ▓█████▄▄▄█████▓ ██░ ██ ▓█████  ██▀███   ██▓  ██████ 
▒████▄    ▓█   ▀▓  ██▒ ▓▒▓██░ ██▒▓█   ▀ ▓██ ▒ ██▒▓██▒▒██    ▒ 
▒██  ▀█▄  ▒███  ▒ ▓██░ ▒░▒██▀▀██░▒███   ▓██ ░▄█ ▒▒██▒░ ▓██▄   
░██▄▄▄▄██ ▒▓█  ▄░ ▓██▓ ░ ░▓█ ░██ ▒▓█  ▄ ▒██▀▀█▄  ░██░  ▒   ██▒
 ▓█   ▓██▒░▒████▒ ▒██▒ ░ ░▓█▒░██▓░▒████▒░██▓ ▒██▒░██░▒██████▒▒
 ▒▒   ▓▒█░░░ ▒░ ░ ▒ ░░    ▒ ░░▒░▒░░ ▒░ ░░ ▒▓ ░▒▓░░▓  ▒ ▒▓▒ ▒ ░
  ▒   ▒▒ ░ ░ ░  ░   ░     ▒ ░▒░ ░ ░ ░  ░  ░▒ ░ ▒░ ▒ ░░ ░▒  ░ ░
  ░   ▒      ░    ░       ░  ░░ ░   ░     ░░   ░  ▒ ░░  ░  ░  
      ░  ░   ░  ░         ░  ░  ░   ░  ░   ░      ░        ░  
                                                              
""" # noqa W291
    blue_chars = ["▓", "█", "▄", "▀"]
    white_chars = ["▒", "░"]

    colored_art = ""
    for char in AETHERIS_ART:
        if char in blue_chars:
            colored_art += f"[bold bright_blue]{char}[/bold bright_blue]"
        elif char in white_chars:
            colored_art += f"[white]{char}[/white]"
        else:
            colored_art += char

    console = Console()
    console.print(colored_art, justify="center")
    console.print(Rule(style="dim cyan"))
    console.print("[white]C2 Serverless Framework[/white]", justify="center")
    console.print(Rule(style="dim cyan"))
    print()


def print_agents_table(agents_list: list):
    if not agents_list:
        print("[ERROR] No agents found.")
        return

    console = Console()
    table = Table(title="Agents", show_header=True, header_style="bold cyan")

    table.add_column("Agent ID", style="dim", width=36)
    table.add_column("Last Seen", justify="left")
    table.add_column("Hostname", justify="left")
    table.add_column("OS Name", justify="left")
    table.add_column("Source IP", justify="left")

    for agent in agents_list:
        agent_id = agent.get("agentId", "N/A")
        last_seen = agent.get("lastSeen", "N/A")
        hostname = agent.get("hostname", "N/A")
        os_name = agent.get("os_name", "N/A")
        source_ip = agent.get("sourceIp", "N/A")

        table.add_row(agent_id, last_seen, hostname, os_name, source_ip)

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
