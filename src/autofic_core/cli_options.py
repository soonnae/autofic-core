import click

EXPLAIN_OPTION = click.option(
    '--explain',
    is_flag = True,
    help = 'AutoFiC 사용 설명서'
)

REPO_OPTION = click.option(
    '--repo',
    required=False,
    help = 'GitHub repository URL'
)

SAVE_DIR_OPTION = click.option(
    '--save-dir',
    default = "artifacts/downloaded_repo",
    help = '저장할 디렉토리 경로'
)

SAST_OPTION = click.option(
    '--sast',
    is_flag = True,
    help = 'SAST 분석 수행 여부'
)

RULE_OPTION = click.option(
    '--rule',
    default = "p/default",
    show_default=True,
    help='SAST 시 사용할 Semgrep 룰'
)

LLM_OPTION = click.option(
    '--llm',
    is_flag = True,
    help = 'LLM 응답 생성 및 코드 수정 수행 여부'
)

LLM_RETRY_OPTION = click.option(
    '--llm-retry',
    is_flag=True,
    default=False,
    help='수정된 코드에 대해 LLM 재실행을 수행합니다.'
)

PR_OPTION = click.option(
    '--pr',
    is_flag = True,
    help = '코드 수정 후 자동 PR 생성 여부'
)

def explain_option(func) :
    func = EXPLAIN_OPTION(func)
    return func

def common_options(func):
    for option in reversed([REPO_OPTION, SAVE_DIR_OPTION, EXPLAIN_OPTION]):
        func = option(func)
    return func

def sast_options(func):
    for option in reversed([SAST_OPTION, RULE_OPTION]):
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