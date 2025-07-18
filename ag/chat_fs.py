from pathlib import Path
import subprocess, time

CHAT_DIR     = Path.home() / ".ag" / "chats"
CURRENT_FILE = Path.home() / ".ag" / "current"
INSN_DIR     = Path.home() / ".ag" / "insn"
INSN_CURRENT = Path.home() / ".ag" / "insn" / "current"
DEFAULT_INSTRUCTIONS = ("")

def ensure_insn_dir() -> None:
    INSN_DIR.mkdir(parents=True, exist_ok=True)

def list_insns() -> list[str]:
    ensure_insn_dir()
    return sorted(p.stem for p in INSN_DIR.iterdir() if p.suffix == ".md")

def read_insn(name: str) -> str:
    path = INSN_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt '{name}' not found")
    return path.read_text(encoding="utf-8")

def new_insn(name: str, src_file: str | None = None) -> None:
    ensure_insn_dir()
    path = INSN_DIR / f"{name}.md"
    if path.exists():
        raise FileExistsError(f"Prompt '{name}' already exists")
    if src_file:
        text = Path(src_file).read_text(encoding="utf-8")
    else:
        text = ""
    path.write_text(text, encoding="utf-8")

def delete_insn(name: str) -> None:
    path = INSN_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt '{name}' not found")
    path.unlink()

def set_default_insn(name: str) -> None:
    ensure_insn_dir()
    if name not in list_insns():
        raise FileNotFoundError(f"Prompt '{name}' not found")
    INSN_CURRENT.write_text(name, encoding="utf-8")

def get_default_insn() -> str | None:
    try:
        return INSN_CURRENT.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None

def ensure_git_repo() -> None:
    """init git repo"""
    git_dir = CHAT_DIR / ".git"
    if not git_dir.exists():
        subprocess.run(
            ["git", "init", str(CHAT_DIR)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

def git_commit(session: str) -> None:
    """
    git add ... && git commit

    <session>: Q&A @ YYYY-MM-DD HH:MM:SS
    """
    ensure_git_repo()
    subprocess.run(
        ["git", "-C", str(CHAT_DIR), "add", "."],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    msg = f"{session}: Q&A @ {ts}"
    subprocess.run(
        ["git", "-C", str(CHAT_DIR), "commit", "-m", msg],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def list_chats() -> list[str]:
    """list sessions (without .md), alphabetic order"""
    ensure_chat_dir()
    return sorted(f.stem for f in CHAT_DIR.iterdir() if f.suffix == ".md")

def get_default_chat() -> str | None:
    """read ~/.ag/current"""
    try:
        return CURRENT_FILE.read_text().strip()
    except FileNotFoundError:
        return None

def set_default_chat(name: str) -> None:
    """set default chat"""
    ensure_chat_dir()
    if name not in list_chats():
        raise FileNotFoundError(f"Chat '{name}' doesn't exist")
    CURRENT_FILE.write_text(name, encoding="utf-8")

def show_chat(name: str) -> str:
    """
    print chat to stdout
    """
    path = chat_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Chat '{name}' doesn't exist")
    return path.read_text(encoding="utf-8")

def ensure_chat_dir() -> None:
    """make sure chat dir exists"""
    CHAT_DIR.mkdir(parents=True, exist_ok=True)

def chat_path(name: str) -> Path:
    """return the path of markdown file"""
    ensure_chat_dir()
    return CHAT_DIR / f"{name}.md"

def new_chat(name: str, insn: str | None = None) -> None:
    """
    create new chat and write in template
    name: session name
    insn: instruction
    """
    path = chat_path(name)
    if path.exists():
        raise FileExistsError(f"Chat '{name}' already exists")
    inst = insn.strip() if insn else DEFAULT_INSTRUCTIONS
    content = (
        f"# Chat: {name}\n\n"
        "## Instructions:\n"
        f"{inst}\n\n"
        "## Conversation\n\n"
    )
    path.write_text(content, encoding="utf-8")

def rename_chat(old: str, new: str) -> None:
    """rename chat"""
    old_path = chat_path(old)
    new_path = chat_path(new)
    if not old_path.exists():
        raise FileNotFoundError(f"Chat '{old}' doesn't exist")
    if new_path.exists():
        raise FileExistsError(f"Chat '{new}' already exists")
    old_path.rename(new_path)

def delete_chat(name: str) -> None:
    """delete chat"""
    path = chat_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Chat '{name}' doesn't exist")
    path.unlink()

def read_chat(name: str) -> str:
    """read the entire chat (to send to the model)"""
    path = chat_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Chat '{name}' doesn't exist")
    return path.read_text(encoding="utf-8")

def append_reply(name: str, reply: str) -> None:
    """
    append AI's reply to the file
    """
    path: Path = chat_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Chat '{name}' doesn't exist")

    with path.open("a", encoding="utf-8") as file:
        file.write("\n### Assistant\n")
        file.write("```reply\n")
        file.write(reply.strip() + "\n")
        file.write("```\n")

def append_user_and_reply(name: str, question: str, reply: str) -> None:
    """
    append user's question and AI's reply to the file
    """
    path = chat_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Chat '{name}' doesn't exist")
    with path.open("a", encoding="utf-8") as file:
        file.write("\n### User\n")
        file.write(question.strip() + "\n\n")
        file.write("\n### Assistant\n")
        file.write("```reply\n")
        file.write(reply.strip() + "\n")
        file.write("```\n")
