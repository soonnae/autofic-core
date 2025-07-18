import click

EXPLAIN_OPTION = click.option(
    '--explain',
    is_flag = True,
    help = 'Display usage guide for AutoFiC'
)

REPO_OPTION = click.option(
    '--repo',
    required=False,
    help = 'GitHub repository URL to analyze'
)

SAVE_DIR_OPTION = click.option(
    '--save-dir',
    default = "artifacts/downloaded_repo",
    help = 'Directory path to save analysis results'
)

SAST_TOOL_CHOICES = ['semgrep', 'codeql', 'eslint', 'snykcode']
SAST_TOOL_OPTION = click.option(
    '--sast',
    type=click.Choice(SAST_TOOL_CHOICES, case_sensitive=False),
    default='semgrep',
    show_default=True,
    help='Choose the SAST tool to use'
)

LLM_OPTION = click.option(
    '--llm',
    is_flag = True,
    help = 'Run LLM to generate responses and modify code'
)

LLM_RETRY_OPTION = click.option(
    '--llm-retry',
    is_flag=True,
    default=False,
    help='Re-run the LLM on modified code for final verification'
)

PR_OPTION = click.option(
    '--pr',
    is_flag = True,
    help = 'Automatically create a PR after patching the code'
)

def explain_option(func) :
    func = EXPLAIN_OPTION(func)
    return func

def common_options(func):
    for option in reversed([REPO_OPTION, SAVE_DIR_OPTION, EXPLAIN_OPTION]):
        func = option(func)
    return func

def sast_options(func):
    for option in reversed([SAST_TOOL_OPTION]):
        func = option(func)
    return func

def llm_option(func):
    func = LLM_OPTION(func)
    return func

def llm_retry_option(func):
    func = LLM_RETRY_OPTION(func)
    return func

def pr_option(func):
    func = PR_OPTION(func)
    return func