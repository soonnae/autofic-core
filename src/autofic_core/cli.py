import click
import json
import time
import os
from dotenv import load_dotenv
from pathlib import Path
from autofic_core.utils.progress_utils import create_progress
from autofic_core.download.github_repo_handler import GitHubRepoHandler
from autofic_core.sast.semgrep_runner import SemgrepRunner
from autofic_core.sast.semgrep_preprocessor import SemgrepPreprocessor 
from autofic_core.llm.prompt_generator import PromptGenerator
from autofic_core.llm.llm_runner import LLMRunner, save_md_response
from autofic_core.llm.response_parser import LLMResponseParser
from autofic_core.patch.diff_generator import DiffGenerator
from autofic_core.cli_options import (explain_option, common_options, sast_options, llm_option, pr_option)

load_dotenv()        

@click.command()
@explain_option
@common_options
@sast_options
@llm_option
@pr_option
@click.pass_context

def main(ctx, repo, save_dir, explain, sast, rule, llm, pr):
    if explain:
        print_help_message()
        ctx.exit(0)

    if not repo:
        click.echo(" --repo는 필수입니다!", err=True)
        ctx.exit(1)
    
    if llm and not sast:
        click.secho("[ERROR] --llm 옵션은 --sast 없이 단독으로 사용할 수 없습니다!", fg="red")
        raise click.Abort()
    
    if pr and not llm:
        click.secho("[ERROR] --pr 옵션은 --llm 수행 이후에만 사용할 수 있습니다!", fg="red")
        raise click.Abort()
    
    run_cli(repo, save_dir, sast, rule, llm, pr)

def print_help_message():
    click.secho("\n\n [ AutoFiC CLI 사용법 안내 ]", fg="magenta", bold=True)
    click.echo("""

--explain       AutoFiC 사용 설명서 출력

--repo          분석할 GitHub 저장소 URL (필수)
--save-dir      분석 결과를 저장할 디렉토리 (기본: artifacts/downloaded_repo)

--sast          Semgrep 기반 정적 분석 실행
--rule          SAST 수행 시 사용할 Semgrep 룰셋 경로 또는 preset (기본: p/default)

--llm           LLM을 통한 취약 코드 수정 및 응답 저장
--pr            수정된 코드를 기반으로 자동 PR 생성


\n※ 사용 예시:
    python -m autofic_core.cli --repo https://github.com/user/project --sast --llm --pr\n


⚠️ 주의사항:
  - --llm 사용 시 --sast 옵션이 반드시 선행되어야 합니다.
  - --pr 사용 시 --llm 옵션이 반드시 선행되어야 합니다.
    """)

def run_sast(clone_path, save_dir, rule):
    click.echo("\nSemgrep 분석 시작\n")
    with create_progress() as progress:
        task = progress.add_task("[cyan]Semgrep 분석 진행 중...", total=100)
        for _ in range(100):
            progress.update(task, advance=1)
            time.sleep(0.01)
        
        semgrep_runner = SemgrepRunner(repo_path=clone_path, rule=rule)
        semgrep_result_obj = semgrep_runner.run_semgrep()
        progress.update(task, completed=100)

    if semgrep_result_obj.returncode != 0:
        click.echo(f"\n[ ERROR ] Semgrep 실행 실패 (리턴 코드: {semgrep_result_obj.returncode})\n")
        return None
    
    sast_dir = save_dir / "sast"
    sast_dir.mkdir(parents=True, exist_ok=True)
    semgrep_result_path = sast_dir / "before.json"
    
    SemgrepPreprocessor.save_json_file(
        json.loads(semgrep_result_obj.stdout),
        semgrep_result_path
    )

    click.secho(f"\n[ SUCCESS ] Semgrep 결과가 {semgrep_result_path}에 저장됨\n", fg="green")

    return semgrep_result_path


def run_llm(semgrep_result_path, clone_path, save_dir):
    prompts = PromptGenerator().from_semgrep_file(
        semgrep_result_path,
        base_dir=clone_path
    )
    llm_output_dir = save_dir / "llm"
    llm = LLMRunner()

    click.echo("\nGPT 응답 생성 및 저장 시작\n")
    with create_progress() as progress:
        task = progress.add_task("[magenta]LLM 응답 중...", total=len(prompts))
        for p in prompts:
            response = llm.run(p.prompt)
            save_md_response(response, p.snippet, output_dir=llm_output_dir)
            progress.update(task, advance=1)
            time.sleep(0.01)
        progress.update(task, completed=100)

    click.secho(f"\n[ SUCCESS ] LLM 응답 저장 완료! {llm_output_dir}\n", fg="green")
    return llm_output_dir


def clone_repository(repo, save_dir):
    handler = GitHubRepoHandler(repo_url=repo)

    if handler.needs_fork:
        click.secho(f"\n저장소 Fork 시도 중...\n", fg="cyan")
        handler.fork()
        time.sleep(1)
        click.secho(f"\n[ SUCCESS ] Fork 완료\n", fg="green")
    
    clone_path = handler.clone_repo(save_dir=str(save_dir), use_forked=handler.needs_fork)
    click.secho(f"\n[ SUCCESS ] 저장소 클론 완료: {clone_path}\n", fg="green")
    return clone_path  

def run_cli(repo, save_dir, sast, rule, llm, pr):
    save_dir = Path(save_dir).expanduser().resolve()
    clone_path = clone_repository(repo, save_dir)

    semgrep_result_path = None

    if sast:
        semgrep_result_path = run_sast(clone_path, save_dir, rule)

    if llm:
        if not semgrep_result_path:
            sast_path = save_dir / "sast/before.json"
            if not sast_path.exists():
                click.echo("[ERROR] SAST 결과가 없습니다. --sast 옵션을 추가하거나 기존 분석 결과를 확인하세요.", err=True)
                return
            semgrep_result_path = sast_path

        run_llm(semgrep_result_path, clone_path, save_dir)

    if pr:
        from autofic_core.patch.pr_auto import BranchPRAutomation
        BranchPRAutomation(repo, save_dir).run()


if __name__ == '__main__':
    main()