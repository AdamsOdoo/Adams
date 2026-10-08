#!/usr/bin/env python3
"""Claude Code PreToolUse guard installed by the odoo-harness.

On Odoo.sh a push to the production or a staging branch deploys it. The real protection is a GitHub
ruleset on those branches (`.odoo-harness/oh protect`), which applies to every agent and person. This
hook is a second line of defence in Claude Code. It blocks:
  - `git push` (also through `git subtree push`, `git send-pack`, aliases and wrappers such as
    `bash -c`, `env`, `sudo`) to a protected branch, including force, delete, wildcard, --all/--mirror
    and push.default=matching pushes, and pushes whose target it cannot read;
  - merges and approvals by the agent: `gh pr merge`, `gh pr review --approve`, `gh api`/`curl` calls
    to merge, ref, contents, ruleset or branch-protection endpoints, and the GitHub MCP merge,
    auto-merge and approving-review tools;
  - GitHub MCP writes to a protected branch, or without a branch (that means the default branch).
These rules cover the project's own repository: the repository of CLAUDE_PROJECT_DIR and the remotes it pushes
to. A push to another repository (a second checkout in the session, the harness repository), a last-resort
match in a command that runs in another repository and doesn't name the project's, and a GitHub MCP call on
another owner/repo are allowed. When the repository can't be resolved (no git repository, no remote, an unknown
remote name, a command git can't place), the rules apply: closed, not open.

For the odoo-reviewer and odoo-scout subagents (Claude Code sends their `agent_type`) and with --read-only, it allows
reading only: git inspection commands, `oh src|evidence|doctor`, `oh test --no-record`, and
read-only shell tools, with their writing or program-running options refused (sed w/e, sort -o,
uniq OUTPUT, tree -o, rg --pre, git grep -O, GIT_* variables, ...). It is an allowlist for honest
mistakes, not a sandbox; `oh evidence` before and after a review shows whether anything changed.

It reads the hook JSON on stdin and exits 2 with a reason to block; anything else is allowed.
"""
from __future__ import annotations

import json
import hashlib
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

DEFAULT_PROTECTED = {"main", "master", "production", "prod", "staging"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
PUSH_VALUE_OPTIONS = {"--repo", "-o", "--push-option", "--receive-pack", "--exec"}
MCP_BRANCH_WRITES = {"push_files", "create_or_update_file", "delete_file", "create_branch"}
MCP_ALWAYS_BLOCKED = {"merge_pull_request", "enable_pr_auto_merge"}
MCP_READ_PREFIXES = ("get_", "list_", "search_")
MCP_READ_TOOLS = {"pull_request_read", "issue_read"}
API_WRITES = re.compile(r"/pulls/\d+/merge\b|/merges\b|/git/refs\b|/contents/|/rulesets\b|"
                        r"/branches/[^/\s]+/(protection|rename)\b|/pulls/\d+/reviews\b")
GRAPHQL_WRITES = re.compile(r"\b(mergePullRequest|enablePullRequestAutoMerge|mergeBranch|updateRef|updateRefs|deleteRef|"
                            r"createRef|createCommitOnBranch|updateBranchProtectionRule|deleteBranchProtectionRule|"
                            r"addPullRequestReview|submitPullRequestReview)\b")
TEXT_TOOLS = {"echo", "printf", "grep", "egrep", "fgrep", "rg", "cat", "head", "tail", "less", "wc", "ls", "jq", "diff",
              "cd", "true"}
INTERPRETERS = {"python", "python3", "python2", "node", "nodejs", "perl", "ruby", "php", "awk", "gawk", "mawk", "lua"}
# Programs that hand their arguments to another program (so a quoted string may be code after all).
LAUNCHERS = {"env", "timeout", "sudo", "nohup", "nice", "xargs", "uv", "uvx", "pipx", "poetry", "exec", "eval", "command",
             "sh", "bash", "zsh", "dash", "oh", "odoo-bin"}
PROBE = "odoo-harness-read-only-probe"
READ_ONLY_AGENTS = {"odoo-reviewer", "odoo-scout"}

READ_ONLY_GIT = {"diff", "log", "show", "status", "rev-parse", "ls-files", "ls-tree", "blame", "grep", "merge-base",
                 "cat-file", "describe", "shortlog", "name-rev", "rev-list", "whatchanged", "show-ref",
                 "for-each-ref", "diff-tree", "range-diff", "branch", "remote"}
READ_ONLY_TOOLS = {"cat", "head", "tail", "grep", "egrep", "fgrep", "rg", "ls", "wc", "sort", "uniq", "cut", "diff",
                   "stat", "file", "tree", "echo", "printf", "pwd", "true", "false", "test", "[", "basename",
                   "dirname", "realpath", "readlink", "jq", "nl", "column", "tr", "cd", "comm", "md5sum",
                   "sha256sum", "date", "which", "sed", "find", "zcat"}
READ_ONLY_OH = {"src", "check", "evidence", "deps", "doctor"}
SAFE_VARIABLES = {"LC_ALL", "LANG", "LANGUAGE", "TZ", "COLUMNS", "LINES", "NO_COLOR", "TERM"}
BRANCH_LISTING = ("-a", "--all", "-r", "--remotes", "-l", "--list", "-v", "-vv", "--verbose", "--show-current",
                  "--contains", "--no-contains", "--merged", "--no-merged", "--points-at", "--sort", "--format",
                  "--color", "--no-color", "--column", "--no-column", "--abbrev", "--no-abbrev", "-i", "--ignore-case")
SED_PRINT = re.compile(r"^\s*(\d+|\$)?\s*(,\s*(\d+|\$))?\s*p\s*$")


def protected_branches(project_dir):
    try:
        config = json.loads((Path(project_dir) / ".odoo-harness" / "project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        config = {}
    if not isinstance(config, dict):
        config = {}
    names = set()
    if config.get("production_branch"):
        names.add(config["production_branch"])
        names.update(config.get("staging_branches") or [])
    names.update(config.get("protected_branches") or [])
    return names if config.get("production_branch") else names | DEFAULT_PROTECTED


def repo_url(url):
    """A remote URL in one comparable form (host/path, lower case): without scheme, credentials, `.git` or a
    trailing slash, so https://x-token@github.com/Owner/Repo.git and git@github.com:owner/repo are the same."""
    url = (url or "").strip()
    if not url:
        return None
    url = re.sub(r"^[a-z][a-z0-9+.-]*://", "", url, flags=re.I)
    url = re.sub(r"^[^/@]+@", "", url)
    if re.match(r"^[^/]+:", url):  # scp-like host:path
        url = url.replace(":", "/", 1)
    url = re.sub(r"(\.git)?/*$", "", url, flags=re.I)
    return url.lower().rstrip("/") or None


def project_scope(project_dir):
    """The project's own repository: its root and every remote URL it pushes to (comparable form), with the
    owner/repo slugs GitHub tools name it by. None when the project is not a git repository or has no remote:
    then nothing can be told apart and the rules apply everywhere."""
    root = ask_git(project_dir, "rev-parse", "--show-toplevel")
    if not root:
        return None
    urls = set()
    for name in ask_git(root, "remote").split():
        for url in (ask_git(root, "remote", "get-url", "--push", name), ask_git(root, "remote", "get-url", name)):
            if repo_url(url):
                urls.add(repo_url(url))
    if not urls:
        return None
    return {"root": os.path.realpath(root), "urls": urls, "slugs": {"/".join(u.rsplit("/", 2)[-2:]) for u in urls}}


def in_scope(url, scope):
    """Whether a push to `url` (comparable form, None when unresolved) concerns the project's repository."""
    return scope is None or url is None or url in scope["urls"]


def push_remote(args, where):
    """The repository `git push <args>` in `where` sends to, in comparable form; None when it can't be resolved."""
    positional, remote, i = [], None, 0
    while i < len(args):
        arg = args[i]
        if arg == "--repo" and i + 1 < len(args):
            remote, i = args[i + 1], i + 1
        elif arg.startswith("--repo="):
            remote = arg.split("=", 1)[1]
        elif arg in PUSH_VALUE_OPTIONS and i + 1 < len(args):
            i += 1
        elif not arg.startswith("-"):
            positional.append(arg)
        i += 1
    remote = positional[0] if positional else remote
    if not remote:
        upstream = ask_git(where, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        remote = ask_git(where, "config", "--get", "remote.pushDefault") or (
            upstream.split("/", 1)[0] if "/" in upstream else "origin")
    url = ask_git(where, "remote", "get-url", "--push", remote) or ask_git(where, "remote", "get-url", remote)
    if not url and ("/" in remote or ":" in remote):
        url = remote  # a URL or path given directly
    return repo_url(url) if url else None


def concerns_project(command, cwd, scope):
    """Whether a command the parser can't see into may act on the project's repository: it runs inside it (or
    where git can't say), or it names the project's path, a remote URL or an owner/repo of it."""
    top = ask_git(cwd, "rev-parse", "--show-toplevel")
    if not top or os.path.realpath(top) == scope["root"]:
        return True
    text = command.lower()
    return scope["root"].lower() in text or any(name in text for name in scope["urls"] | scope["slugs"])


def split_commands(command):
    """Split a shell command into simple commands (token lists) at ; & | && || and newlines."""
    lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    segments = [[]]
    for token in lexer:
        if token and set(token) <= set(";&|()"):
            segments.append([])
        else:
            segments[-1].append(token)
    return [s for s in segments if s]


def ask_git(cwd, *args):
    result = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def current_branches(cwd):
    """The current branch and its upstream branch: a bare `git push` may update either."""
    names = {ask_git(cwd, "rev-parse", "--abbrev-ref", "HEAD")}
    upstream = ask_git(cwd, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if upstream and "/" in upstream:
        names.add(upstream.split("/", 1)[1])
    return {n for n in names if n and n != "HEAD"}


def push_targets(args, cwd):
    """Return (destination branches, wide) for `git push <args>`; wide means it may update any branch."""
    positional, wide, i = [], False, 0
    while i < len(args):
        arg = args[i]
        if arg in ("--all", "--mirror", "--branches"):
            wide = True
        elif arg in PUSH_VALUE_OPTIONS and i + 1 < len(args):
            i += 1
        elif not arg.startswith("-"):
            positional.append(arg)
        i += 1
    refspecs = positional[1:]
    if not refspecs:
        remote = positional[0] if positional else "origin"
        configured = ask_git(cwd, "config", "--get-all", f"remote.{remote}.push").split()
        if configured:
            refspecs = configured
        elif ask_git(cwd, "config", "--get", "push.default") == "matching":
            return [], True
        else:
            return sorted(current_branches(cwd)), wide
    targets = []
    for spec in refspecs:
        if re.search(r"[$`*]", spec):
            return [], True  # computed or wildcard refspec: the target can't be checked
        spec = spec.lstrip("+")
        destination = spec.split(":", 1)[1] if ":" in spec else spec
        destination = re.sub(r"^refs/heads/", "", destination)
        if destination in ("HEAD", "@", ""):
            targets.extend(current_branches(cwd) or {destination})
        else:
            targets.append(destination)
    return targets, wide


def git_command(tokens, cwd, depth=0):
    """Return (subcommand, args, repo dir) for a git (or hub) command in `tokens`, resolving aliases."""
    for start, token in enumerate(tokens):
        if os.path.basename(token) in ("git", "hub"):
            break
    else:
        return None
    i, directory, aliases = start + 1, None, {}
    while i < len(tokens) and tokens[i].startswith("-"):
        option = tokens[i]
        if option in GIT_VALUE_OPTIONS and i + 1 < len(tokens):
            if option == "-C":
                directory = str(Path(directory or cwd, tokens[i + 1]))
            if option == "-c" and tokens[i + 1].startswith("alias."):
                key, _, value = tokens[i + 1][len("alias."):].partition("=")
                aliases[key] = value
            i += 2
        else:
            i += 1
    if i >= len(tokens):
        return None
    where = directory or cwd
    sub, args = tokens[i], tokens[i + 1:]
    alias = aliases.get(sub) or (ask_git(where, "config", "--get", f"alias.{sub}") if depth < 3 else "")
    if alias:
        if alias.startswith("!"):
            return ("!", [alias[1:] + " " + shlex.join(args)], where)
        return git_command(["git", *shlex.split(alias), *args], where, depth + 1)
    return sub, args, where


def http_method(tokens, method_flags, data_flags):
    method = None
    for i, token in enumerate(tokens):
        if token in method_flags and i + 1 < len(tokens):
            method = tokens[i + 1].upper()
        elif any(token == f or token.startswith(f + "=") for f in method_flags):
            method = token.split("=", 1)[1].upper()
        elif re.match(r"^-X[A-Za-z]+$", token):
            method = token[2:].upper()
    if method:
        return method
    return "POST" if any(t in data_flags or t.split("=", 1)[0] in data_flags for t in tokens) else "GET"


def check_segment(tokens, cwd, protected, depth=0, scope=None):
    names = [os.path.basename(t) for t in tokens]
    for i, name in enumerate(names):
        if name in SHELLS and i + 2 < len(tokens) and re.match(r"^-[a-z]*c[a-z]*$", tokens[i + 1]):
            return check_bash(tokens[i + 2], cwd, protected, depth + 1, scope)
        if name == "eval" and i + 1 < len(tokens):
            return check_bash(" ".join(tokens[i + 1:]), cwd, protected, depth + 1, scope)
    parsed = git_command(tokens, cwd)
    if parsed:
        sub, args, where = parsed
        if sub == "!":
            return check_bash(args[0], where, protected, depth + 1, scope)
        if sub == "subtree" and args[:1] == ["push"]:
            positional = [a for a in args[1:] if not a.startswith("-")]
            sub, args = "push", positional[-2:]
        if sub == "send-pack":
            sub, args = "push", [a for a in args if not a.startswith("-")]
        if sub == "push":
            if not in_scope(push_remote(args, where), scope):
                return None  # another repository: its branches are not the Odoo.sh deploy branches
            targets, wide = push_targets(args, where)
            if wide:
                return "this push may update the protected branches (--all/--mirror, wildcard, computed or " \
                       "push.default=matching); push one named feature branch"
            hit = sorted(t for t in targets if t in protected)
            if hit:
                return f"pushing to {', '.join(hit)} deploys on Odoo.sh"
        return None
    if "gh" in names:
        rest = tokens[names.index("gh") + 1:]
        if rest[:2] == ["pr", "merge"]:
            return "merging a pull request deploys on Odoo.sh; the user merges"
        if rest[:2] == ["pr", "review"] and any(t in ("--approve", "-a") for t in rest):
            return "the agent does not approve pull requests; a person reviews and approves"
        if rest[:1] == ["api"]:
            method = http_method(rest, {"-X", "--method"}, {"-f", "-F", "--field", "--raw-field", "--input"})
            if (method != "GET" and any(API_WRITES.search(t) for t in rest)) or any(GRAPHQL_WRITES.search(t) for t in rest):
                return "this GitHub API call merges, moves a branch, approves, writes files or changes protection"
    if names and names[0] in ("curl", "wget", "http", "https", "xh"):
        method = http_method(tokens, {"-X", "--request", "--method"},
                             {"-d", "--data", "--data-raw", "--data-binary", "--json", "-F", "--form", "-T",
                              "--upload-file", "--post-data", "--body-data"})
        github = any("api.github.com" in t or "/api/v3/" in t or "/api/graphql" in t for t in tokens)
        if github and ((method != "GET" and any(API_WRITES.search(t) for t in tokens))
                       or any(GRAPHQL_WRITES.search(t) for t in tokens)):
            return "this GitHub API call merges, moves a branch, approves, writes files or changes protection"
    return None


def check_bash(command, cwd, protected, depth=0, scope=None):
    if depth > 4:
        return "command nesting is too deep to check"
    try:
        segments = split_commands(command)
    except ValueError:
        if re.search(r"\b(push|merge)\b", command):
            return "could not parse this command; run a plain `git push origin <feature-branch>`"
        return None
    for tokens in segments:
        reason = check_segment(tokens, cwd, protected, depth, scope)
        if reason:
            return reason
    # Last resort for programs the parser can't see into (python -c, node -e, scripts): a command that
    # mentions both a push and a protected branch, and isn't just text tools, is not allowed. Quoted text and
    # heredoc bodies are skipped only when no token anywhere could run them: `sed -i 's/.../push to main/' notes.md`
    # writes prose, while `python3 -c "..."`, `env python3 -c "..."`, `oh shell -c "..."` or `timeout 9 node -e "..."`
    # may run git. A double-quoted `$(...)` or backtick runs in the shell itself and is always scanned.
    interpreted = runs_code(segments)
    scanned = command if interpreted else unquoted(command)
    words = set(re.findall(r"[A-Za-z0-9._/-]+", scanned))
    if ("push" in words and words & (protected | {f"refs/heads/{b}" for b in protected})
            and not any(git_command(t, cwd) for t in segments)
            and not all(os.path.basename(t[0]) in TEXT_TOOLS for t in segments)
            and (scope is None or concerns_project(command, cwd, scope))):
        return "this command mentions a push and a protected branch; use a plain `git push origin <feature-branch>`"
    return None


def runs_code(segments):
    """True when a token of the command is an interpreter or a program that starts one (in any position: launchers
    such as env, timeout or sudo put the interpreter second)."""
    for tokens in segments:
        for token in tokens:
            base = os.path.basename(token)
            if base in INTERPRETERS or base in LAUNCHERS or base.startswith(("python", "node")):
                return True
    return False


def unquoted(command):
    """The command without its quoted strings and heredoc bodies: what the shell itself would run. A double-quoted
    string holding a command substitution is kept, because the shell runs it."""
    text = re.sub(r"<<-?\s*'?\"?(\w+)'?\"?[^\n]*\n.*?^\1\s*$", " ", command, flags=re.S | re.M)  # heredocs
    text = re.sub(r"'[^']*'", " ", text)
    return re.sub(r'"(?:[^"\\]|\\.)*"', lambda m: m.group(0) if re.search(r"\$\(|`|\$\{", m.group(0)) else " ", text)


HANDOFF_LINES, HANDOFF_BYTES = 45, 4096  # as in oh (doctor reports the same limits)


def long_handoffs(cwd, dirty, unpushed):
    """Handoff files (.odoo-harness/HANDOFF.md, any handoff.md) changed in the working tree, in commits not on the
    remote yet or in the last commit, that are over the limits: a handoff that has grown into a status board."""
    names = {re.sub(r"^\S{1,2}\s+", "", line.strip()).split(" -> ")[-1].strip('"') for line in dirty}
    for rng in filter(None, [unpushed, "HEAD~1..HEAD"]):
        names.update(ask_git(cwd, "diff", "--name-only", rng).splitlines())
    top = ask_git(cwd, "rev-parse", "--show-toplevel") or cwd
    long = []
    for name in sorted(names):
        if Path(name).name.lower() != "handoff.md":
            continue
        try:
            data = (Path(top) / name).read_bytes()
        except OSError:
            continue  # deleted
        if len(data) > HANDOFF_BYTES or len(data.splitlines()) > HANDOFF_LINES:
            long.append(f"{name} ({len(data.splitlines())} lines, {len(data)} bytes)")
    return long


def stop_check(event):
    """Stop hook: a stop with unsaved work is held once per session and state of that work, so the agent commits or
    hands over (or says why it is leaving the tree as it is). The next stop with the same unsaved work goes
    through; new unsaved work is held once more."""
    if event.get("stop_hook_active"):
        return None
    cwd = event.get("cwd") or os.getcwd()
    if not ask_git(cwd, "rev-parse", "--is-inside-work-tree"):
        return None
    dirty = [l for l in ask_git(cwd, "status", "--porcelain", "--untracked-files=normal").splitlines() if l.strip()]
    branch = ask_git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    remote = ask_git(cwd, "rev-parse", "--abbrev-ref", "@{u}")
    if not remote and branch not in ("HEAD", "") and ask_git(cwd, "rev-parse", "--verify", "-q", "refs/remotes/origin/" + branch):
        remote = "origin/" + branch  # pushed before, without tracking
    ahead = ask_git(cwd, "rev-list", "--count", f"{remote}..HEAD") if remote else ""
    reasons = []
    long = long_handoffs(cwd, dirty, f"{remote}..HEAD" if remote else "")
    if long:
        reasons.append("handoff over 45 lines or 4096 bytes: " + ", ".join(long) + " (keep the active track and the "
                       "next action; finished work belongs in the status file and the feature notes)")
    if dirty:
        reasons.append(f"{len(dirty)} uncommitted change(s) (e.g. {dirty[0][3:]})")
    if remote and ahead not in ("", "0"):
        reasons.append(f"{ahead} commit(s) on {branch} not pushed to {remote}")
    elif not remote and branch not in ("HEAD", ""):
        reasons.append(f"branch {branch} has never been pushed")
    if not reasons:
        return None
    state = hashlib.sha256("\n".join([branch, ahead, *sorted(dirty), *long]).encode()).hexdigest()[:16]
    session = re.sub(r"[^A-Za-z0-9._-]", "_", str(event.get("session_id") or "session"))
    marker = Path(os.environ.get("OH_CACHE") or Path.home() / ".cache" / "odoo-harness") / "stops" / session
    try:
        if marker.is_file() and marker.read_text().strip() == state:
            return None  # held once already for this unsaved work
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(state)
    except OSError:
        pass
    return ("the session is stopping with unsaved work: " + "; ".join(reasons) + ". Hand over (odoo-dev §7): "
            "shorten the handoff if it is too long, commit the work with its evidence and the handoff and push the "
            "branch, or say in one line why it stays as it is, then stop again.")


def check_mcp(tool, tool_input, protected, scope=None):
    name = tool.rsplit("__", 1)[-1]
    owner, repo = tool_input.get("owner"), tool_input.get("repo")
    if scope and owner and repo and f"{owner}/{repo}".lower() not in scope["slugs"]:
        return None  # another repository: not the one Odoo.sh deploys
    if name in MCP_ALWAYS_BLOCKED:
        return "merging a pull request deploys on Odoo.sh; the user merges"
    if name == "pull_request_review_write" and str(tool_input.get("event", "")).upper() == "APPROVE":
        return "the agent does not approve pull requests; a person reviews and approves"
    if name in MCP_BRANCH_WRITES:
        branch = tool_input.get("branch")
        if not branch and name != "create_branch":
            return f"{name} without a branch writes to the default branch; name a feature branch"
        if branch in protected:
            return f"writing to {branch} deploys on Odoo.sh"
    return None


def short_flags(args, letters):
    """True when a short option cluster (such as -uo) contains one of `letters`."""
    return any(a.startswith("-") and not a.startswith("--") and set(a[1:]) & set(letters) for a in args)


def sed_problem(args):
    quiet, scripts, words, i = False, [], [], 0
    while i < len(args):
        arg = args[i]
        if arg in ("--quiet", "--silent"):
            quiet = True
        elif arg in ("-e", "--expression") or re.match(r"^-[nEsruz]*e$", arg):
            quiet = quiet or "n" in arg
            if i + 1 < len(args):
                scripts.append(args[i + 1])
            i += 1
        elif arg.startswith("--expression="):
            scripts.append(arg.split("=", 1)[1])
        elif re.match(r"^-[nEsruz]+$", arg) or arg in ("--regexp-extended", "--separate", "--posix", "--null-data"):
            quiet = quiet or "n" in arg
        elif arg.startswith("-"):
            return f"sed option {arg} is not allowed in read-only review"
        else:
            words.append(arg)
        i += 1
    if not scripts and words:
        scripts = [words[0]]
    if not quiet or not scripts or not all(SED_PRINT.match(part) for s in scripts for part in s.split(";") if part.strip()):
        return "only `sed -n '<first>,<last>p' <file>` is allowed in read-only review"
    return None


def tool_problem(name, args):
    """Why an otherwise read-only tool would write or run something with these arguments, or None."""
    if name == "sed":
        return sed_problem(args)
    if name == "sort" and (short_flags(args, "o") or any(a.startswith(("--output", "--compress-program")) for a in args)):
        return "sort -o/--output writes a file and --compress-program runs one"
    if name == "uniq":
        words, i = [], 0
        while i < len(args):
            if args[i] in ("-f", "-s", "-w"):
                i += 1
            elif not args[i].startswith("-") or args[i] == "-":
                words.append(args[i])
            i += 1
        if len(words) > 1:
            return "uniq writes its second file argument"
    if name == "tree" and (short_flags(args, "oR") or any(a.startswith("--output") for a in args)):
        return "tree -o and -R write files"
    if name == "file" and (short_flags(args, "C") or "--compile" in args):
        return "file -C writes a compiled magic file"
    if name == "date" and (short_flags(args, "s") or any(a.startswith("--set") for a in args)):
        return "date -s sets the clock"
    if name == "rg" and any(a.startswith(("--pre", "--hostname-bin")) for a in args):
        return "rg --pre and --hostname-bin run programs"
    if name == "find" and any(a in ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0",
                                    "-fprintf", "-fls") for a in args):
        return "find actions that run commands or write files are not allowed in read-only review"
    return None


def git_problem(args):
    if any(a in ("-c", "--config-env") or a.startswith(("--config-env=", "--exec-path=", "--output")) for a in args):
        return "git configuration overrides, --exec-path and --output are not allowed in read-only review"
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in ("-C", "--git-dir", "--work-tree", "--namespace") else 1
    sub, rest = (args[i], args[i + 1:]) if i < len(args) else ("", [])
    if sub not in READ_ONLY_GIT:
        return f"`git {sub}` is not a read-only git command"
    if sub == "grep" and any(a.startswith(("-O", "--open-files-in-pager")) for a in rest):
        return "git grep -O runs a program"
    if sub == "branch":
        options = [a for a in rest if a.startswith("-")]
        if any(a.split("=", 1)[0] not in BRANCH_LISTING for a in options) or (
                len(options) < len(rest) and not set(options) & {"-l", "--list", "--contains", "--no-contains",
                                                                 "--merged", "--no-merged", "--points-at"}):
            return "only listing branches is allowed in read-only review"
    if sub == "remote" and not (rest in ([], ["-v"], ["--verbose"]) or (rest[:1] in (["show"], ["get-url"])
                                                                         and len(rest) <= 3)):
        return "only reading remotes (git remote -v / show / get-url) is allowed in read-only review"
    return None


def read_only_bash(command):
    """None when every part of the command only reads; otherwise the reason to block."""
    if PROBE in command:
        return "read-only review mode is active (this probe is expected to be blocked)"
    if "$(" in command or "`" in command:
        return "command substitution is not allowed in read-only review"
    try:
        lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|()<>")
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return "could not parse the command"
    for i, token in enumerate(tokens):
        if set(token) <= set("<>&|;()") and ">" in token:
            target = tokens[i + 1] if i + 1 < len(tokens) else ""
            if not (target == "/dev/null" or (token == ">&" and target in ("1", "2"))):
                return "writing files is not allowed in read-only review"
    for tokens in split_commands(command):
        tokens = [t for t in tokens if t not in ("<",)]
        while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
            variable = tokens[0].split("=", 1)[0]
            if variable not in SAFE_VARIABLES:  # GIT_EXTERNAL_DIFF, GIT_PAGER, GIT_CONFIG_* ... run programs
                return f"setting {variable} is not allowed in read-only review"
            tokens = tokens[1:]
        while tokens and os.path.basename(tokens[0]) in ("timeout", "time"):  # wrappers: check what they run
            tokens = tokens[1:]
            while tokens and (tokens[0].startswith("-") or re.match(r"^\d+(\.\d+)?[smhd]?$", tokens[0])):
                tokens = tokens[1:]
        if tokens and os.path.basename(tokens[0]) in ("python", "python3") and tokens[1:2] and \
                tokens[1].endswith(".odoo-harness/oh"):
            tokens = tokens[1:]  # `python3 .odoo-harness/oh ...` is oh
        if not tokens or tokens[0].isdigit():
            continue
        name = os.path.basename(tokens[0])
        args = tokens[1:]
        if name == "git":
            problem = git_problem(args)
            if problem:
                return problem
            continue
        if name == "oh" or tokens[0].endswith(".odoo-harness/oh"):
            sub = args[0] if args else ""
            if sub in READ_ONLY_OH or sub in ("-h", "--help"):
                if sub == "evidence" and any(a.split("=")[0].startswith("--p") for a in args) \
                        and not any(a.startswith("--d") for a in args):
                    return "the reviewer does not prune evidence (`oh evidence --dry-run` lists what a prune would delete)"
                continue
            if sub == "test" and "--no-record" in args and "--keep" not in args:
                continue
            return "in read-only review use `oh src`, `oh check`, `oh evidence`, `oh deps`, `oh doctor` or `oh test ... --no-record`"
        if name not in READ_ONLY_TOOLS:
            return f"`{name}` is not on the read-only list"
        problem = tool_problem(name, args)
        if problem:
            return problem
    return None


def read_only(tool, tool_input):
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return "the reviewer does not change files"
    if tool == "Bash":
        return read_only_bash(tool_input.get("command", ""))
    if tool.startswith("mcp__"):
        name = tool.rsplit("__", 1)[-1]
        if not (name.startswith(MCP_READ_PREFIXES) or name in MCP_READ_TOOLS):
            return f"{name} is not a read-only tool"
    return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool, tool_input = event.get("tool_name", ""), event.get("tool_input") or {}
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
    if "--stop" in argv:
        reason = stop_check(dict(event, cwd=event.get("cwd") or project_dir))
        if reason:
            print(f"odoo-harness: {reason}", file=sys.stderr)
            return 2
        return 0
    # Hooks in a subagent's own definition don't run in `-p` sessions or untrusted folders; the settings
    # hook does, and Claude Code tells it which subagent is calling.
    if "--read-only" in argv or event.get("agent_type") in READ_ONLY_AGENTS:
        reason = read_only(tool, tool_input)
        if reason:
            print(f"Blocked by odoo-harness guard (read-only review): {reason}.", file=sys.stderr)
            return 2
    protected = protected_branches(project_dir)
    if tool == "Bash":
        reason = check_bash(tool_input.get("command", ""), event.get("cwd") or project_dir, protected,
                            scope=project_scope(project_dir))
    elif tool.startswith("mcp__") and "github" in tool.lower():
        reason = check_mcp(tool, tool_input, protected, project_scope(project_dir))
    else:
        reason = None
    if reason:
        print(f"Blocked by odoo-harness guard: {reason}. Push a feature branch and ask the user to merge "
              f"(protected: {', '.join(sorted(protected))}).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
