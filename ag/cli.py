import subprocess, tempfile, sys, os, shutil, time, locale
import click
from .chat_fs import (
    chat_path, get_default_chat, git_commit, list_chats, rename_chat, set_default_chat, append_reply,
    read_chat, append_user_and_reply, delete_chat, show_chat, new_chat, DEFAULT_INSTRUCTIONS
)
from .api_client import send_message, APIError

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """ag: agent for everything"""
    pass

@cli.command(name="re", help="repl mode")
@click.option("--stream", is_flag=True, help="stream")
def repl(stream: bool) -> None:
    """
    repl mode
    """
    encoding = locale.getpreferredencoding(False)

    click.secho("Entering REPL mode. Type /exit or Ctrl+D to quit.", fg="blue")

    messages: list[dict[str, str]] = []
    if DEFAULT_INSTRUCTIONS:
        messages.append({"role": "system", "content": DEFAULT_INSTRUCTIONS})

    history: list[tuple[str, str]] = []

    while True:
        click.echo(">>> ", nl=False)
        try:
            raw_bytes = sys.stdin.buffer.readline()
        except KeyboardInterrupt:
            click.echo()
            break

        if not raw_bytes:
            click.echo()
            break

        q = raw_bytes.decode(encoding, errors="ignore").rstrip("\n")
        if q.strip() in ("/exit", "/quit"):
            break

        messages.append({"role": "user", "content": q})
        click.secho("Processing...", fg="green")
        try:
            reply = send_message(messages, stream=stream)
        except APIError as e:
            click.secho(f"API Error: {e}", fg="red")
            messages.pop()
            continue

        if not stream:
            click.echo(reply)
        history.append((q, reply))
        messages.append({"role": "assistant", "content": reply})

    if not history:
        click.secho("No messages in this REPL session.", fg="yellow")
        return

    if not click.confirm("Save this REPL conversation as a new session?", default=False):
        click.secho("REPL session discarded.", fg="yellow")
        return

    while True:
        name = click.prompt("Enter session name", default=f"repl-{int(time.time())}")
        try:
            new_chat(name)
            break
        except FileExistsError:
            click.secho(f"Session '{name}' already exists.", fg="red")

    for q, reply in history:
        append_user_and_reply(name, q, reply)

    click.secho(f"REPL conversation saved to session '{name}'", fg="green")
    try:
        git_commit(name)
    except subprocess.CalledProcessError:
        click.secho("Git commit failed; please check your Git setup.", fg="yellow")

@cli.command(name="new")
@click.argument("name")
@click.option("-i", "--insn", help="system prompt")
def new(name, insn):
    """new conversation"""
    try:
        new_chat(name, insn)
        click.secho(f"New conversation created: '{name}'", fg="green")
        try:
            git_commit(name)
        except subprocess.CalledProcessError:
            click.secho("Git commit failed; please check your Git setup.", fg="yellow")
    except FileExistsError as e:
        click.secho(f"Error encounted: {e}", fg="red")
        sys.exit(1)

@cli.command(name="mv")
@click.argument("old_name")
@click.argument("new_name")
def rename(old_name, new_name):
    """rename"""
    try:
        rename_chat(old_name, new_name)
        click.secho(f"Conversation renamed: {old_name} → {new_name}", fg="green")
        try:
            git_commit(new_name)
        except subprocess.CalledProcessError:
            click.secho("Git commit failed; please check your Git setup.", fg="yellow")
    except (FileNotFoundError, FileExistsError) as e:
        click.secho(f"Error encounted: {e}", fg="red")
        sys.exit(1)

@cli.command(name="rm")
@click.argument("name")
def delete(name):
    """delete"""
    try:
        delete_chat(name)
        click.secho(f"Deleted conversation: '{name}'", fg="green")
        try:
            git_commit(name)
        except subprocess.CalledProcessError:
            click.secho("Git commit failed; please check your Git setup.", fg="yellow")
    except FileExistsError as e:
        click.secho(f"Error encounted: {e}", fg="red")
        sys.exit(1)

@cli.command()
@click.argument("name", required=False)
@click.option("--stdin"  , "use_stdin", is_flag = True, help="read from stdin, no history")
@click.option("--temp"   , "is_temp"  , is_flag = True, help="temp session")
@click.option("--save-as", "save_as"  , default = None, help="save the chat (temp session)")
@click.option("--stream" , "stream"   , is_flag = True, help="turn on stream")
def ask(name, use_stdin, is_temp, save_as, stream):
    """
    send question to llm

    pipe:
      echo "question" | ag ask --stdin [--temp] [--save-as NAME|--no-save]
    normal:
      ag ask [NAME] [--stream]
    """
    if use_stdin:
        prompt = sys.stdin.read().strip()
    else:
        if not name:
            default = get_default_chat()
            if default:
                click.secho("Using default session")
                name = default
            click.secho("Require a session name, default session or --stdin flag", fg="red", err=True)
            sys.exit(1)
        prompt = read_chat(name)

    temp_path : str | None = None
    if is_temp:
        temp_file = tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False)
        temp_file.write(f"#Temporary session\n\n{prompt}")
        temp_file.flush()
        temp_path = temp_file.name
        temp_file.close()

    click.secho("Processing...", fg="green")
    message = [{"role": "user", "content": prompt}]
    try:
        reply = send_message(message, stream=stream)
    except APIError as e:
        click.secho(f"Failed to fetch reply, {e}", fg="red")
        if temp_path is not None:
            os.unlink(temp_path)
        sys.exit(1)

    if not stream:
        click.echo(reply)

    if is_temp:
        assert temp_path is not None
        with open(temp_path, "a", encoding="utf-8") as f:
            f.write("\n### Assistant\n")
            f.write(reply + "\n")

            if save_as:
                new_chat(save_as)
                append_user_and_reply(save_as, prompt, reply)
                try:
                    git_commit(save_as)
                except subprocess.CalledProcessError:
                    click.secho("Git commit failed; please check your Git setup.", fg="yellow")
                click.secho(f"Saved to session '{save_as}'", fg="green")
                os.unlink(temp_path)
                return

            click.secho("Temporary conversation discarded", fg="yellow")
            os.unlink(temp_path)
            return
    else:
        if use_stdin:
            append_user_and_reply(name, prompt, reply)
        else:
            append_reply(name, reply)
        try:
            git_commit(name)
        except subprocess.CalledProcessError:
            click.secho("Git commit failed; please check your Git setup.", fg="yellow")

@cli.command()
@click.argument("name")
def edit(name):
    """edit conversation"""
    import os, subprocess
    path = chat_path(name)
    if not path.exists():
        click.secho(f"Chat '{name}' not found", fg="red")
        sys.exit(1)
    editor = os.getenv("EDITOR", "vi")
    subprocess.call([editor, str(path)])

@cli.command(name="ls")
def ag_list():
    """list all sessions, display '*' before default session"""
    chats = list_chats()
    default = get_default_chat()
    for name in chats:
        prefix = "* " if name == default else "  "
        click.echo(f"{prefix}{name}")

@cli.command(name="sw")
@click.argument("name", required=False)
def switch(name):
    """
    switch default session

      ag switch         # if you have fzf installed
      ag switch SESSION # directly set SESSION

    """
    if name:
        try:
            set_default_chat(name)
            click.secho(f"switched default chat to '{name}'", fg="green")
        except FileNotFoundError as e:
            click.secho(f"Error encounted: {e}", fg="red")
            sys.exit(1)
    else:
        chats = list_chats()
        if not chats:
            click.secho("No available sessions found", fg="red")
            sys.exit(1)
        fzf_path = shutil.which("fzf")
        if not fzf_path:
            click.secho("You need fzf to run this command", fg="red")
            sys.exit(1)

        try:
            proc = subprocess.run(
                [fzf_path, "--prompt=Select chat> "],
                input="\n".join(chats).encode(),
                stdout=subprocess.PIPE,
                check=True
            )
            choice = proc.stdout.decode().strip()
        except:
            click.secho("Switch cancelled", fg="yellow")
            sys.exit(1)

        try:
            set_default_chat(choice)
            click.secho(f"switched default chat to '{choice}'", fg="green")
        except FileNotFoundError as e:
            click.secho(f"Error encounted: {e}", fg="red")
            sys.exit(1)

@cli.command(name="cat")
@click.argument("name")
def show(name):
    """
    print session to stdout

    this is just for fast scripting
    equals to "cat ~/.ag/FILENAME"

    ag show NAME | less
    ag show NAME | grep ....
    """
    try:
        md = show_chat(name)
    except FileNotFoundError as e:
        click.secho(f"Error encounted: {e}", fg="red")
        sys.exit(1)
    click.echo(md)

if __name__ == "__main__":
    cli()
