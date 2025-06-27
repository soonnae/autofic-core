import click
import json
import time
import os
from pyfiglet import Figlet
from rich.console import Console
from dotenv import load_dotenv
from pathlib import Path
from autofic_core.utils.progress_utils import create_progress
from autofic_core.download.github_repo_handler import GitHubRepoHandler
from autofic_core.sast.semgrep_runner import SemgrepRunner
from autofic_core.sast.semgrep_preprocessor import SemgrepPreprocessor
from autofic_core.sast.semgrep_merger import merge_snippets_by_location
from autofic_core.llm.prompt_generator import PromptGenerator
from autofic_core.llm.llm_runner import LLMRunner, save_md_response
from autofic_core.llm.response_parser import LLMResponseParser
from autofic_core.patch.diff_generator import DiffGenerator

load_dotenv()    

console = Console()

f = Figlet(font="slant")
ascii_art = f.renderText("AutoFiC")

console.print(f"[magenta]{ascii_art}[/magenta]")

def print_divider(title) :
    console.print(f"\n[bold magenta]{'-'*20} [ {title} ] {'-'*20}[/bold magenta]\n")

def print_summary(
    repo_url: str,
    detected_issues_count: int,
    output_dir: str,
    #pr_status: str,
    response_files: list   
):

    print_divider("AutoFiC 작업 요약")

    console.print(f"✔️ [bold]분석 대상 저장소:[/bold] {repo_url}")
    console.print(f"✔️ [bold]취약점이 탐지된 파일:[/bold] {detected_issues_count} 개")
    if response_files:
        first_file = Path(response_files[0]).name
        last_file = Path(response_files[-1]).name
        console.print(f"✔️ [bold]저장된 응답 파일:[/bold] {first_file} ~ {last_file}")
    else:
        console.print(f"✔️ [bold]저장된 응답 파일:[/bold] 없음")

    #console.print(f"✔️ [bold]PR 여부:[/bold] {pr_status}")

    console.print(f"\n[bold magenta]{'━'*64}[/bold magenta]\n")
    
@click.command()
@click.option('--repo', help='GitHub repository URL')
@click.option('--save-dir', default=os.getenv("DOWNLOAD_SAVE_DIR"), help="저장할 디렉토리 경로")
@click.option('--sast', is_flag=True, help='SAST 분석 수행 여부')
@click.option('--rule', default=os.getenv("SEMGREP_RULE"), help='Semgrep 규칙')

def main(repo, save_dir, sast, rule):
    run_cli(repo, save_dir, sast, rule)

def run_cli(repo, save_dir, sast, rule):

    save_dir = Path(save_dir).expanduser().resolve()
    """ GitHub 저장소 fork 및 클론 """
    
    print_divider("저장소 다운로드 단계")

    handler = GitHubRepoHandler(repo_url=repo)

    if handler.needs_fork:
        click.secho(f"\n저장소에 대한 Fork를 시도합니다...\n", fg="cyan")
        handler.fork()
        time.sleep(0.05)
        click.secho(f"\n[ SUCCESS ] 저장소를 성공적으로 Fork 했습니다!\n", fg="green")
    
    clone_path = handler.clone_repo(save_dir=str(save_dir), use_forked=handler.needs_fork)
    click.secho(f"\n[ SUCCESS ] 저장소를 {clone_path}에 클론했습니다!\n", fg="green")

    """ Semgrep 분석  """

    print_divider("SAST 분석 단계")

    if sast:
        click.echo("\nSemgrep 분석 시작\n")
        with create_progress() as progress:
            task = progress.add_task("[cyan]Semgrep 분석 진행 중...", total=100)
            for _ in range(100):
                progress.update(task, advance=1)
                time.sleep(0.05)  
            
            semgrep_runner = SemgrepRunner(repo_path=clone_path, rule=rule)
            semgrep_result_obj = semgrep_runner.run_semgrep()
            progress.update(task, completed=100)

        if semgrep_result_obj.returncode != 0:
            click.echo(f"\n[ ERROR ] Semgrep 실행 실패 (리턴 코드: {semgrep_result_obj.returncode})\n")
            try:
                err_json = json.loads(semgrep_result_obj.stdout or semgrep_result_obj.stderr)
                click.echo("[ Semgrep 에러 내용 ]")
                for err in err_json.get("errors", []):
                    click.echo(f"- {err.get('message')} (코드: {err.get('code')})")
            except json.JSONDecodeError:
                click.echo("에러 메시지 JSON 파싱 실패 : ")
                click.echo(semgrep_result_obj.stderr or semgrep_result_obj.stdout)
            return

        sast_dir = save_dir / "sast"
        sast_dir.mkdir(parents=True, exist_ok=True)
        
        semgrep_result_path = sast_dir / "before.json"
        
        SemgrepPreprocessor.save_json_file (
            json.loads(semgrep_result_obj.stdout),
            semgrep_result_path
        )
        
        click.secho(f"\n[ SUCCESS ] Semgrep 분석 완료! 결과가 '{semgrep_result_path}'에 저장되었습니다.\n", fg="green")

        processed = SemgrepPreprocessor.preprocess (
            input_json_path=semgrep_result_path,
            base_dir=clone_path
        )
        
        merged = merge_snippets_by_location(processed)
        
        '''프롬프트 호출'''
        prompts_generator = PromptGenerator()
        prompts = prompts_generator.generate_prompts(merged)
        
        '''LLM 호출 및 응답 저장'''

        print_divider("LLM 응답 생성 단계")

        llm = LLMRunner()
        llm_output_dir = save_dir / "llm"
        click.echo("\nGPT 응답 생성 및 저장 시작\n")

        with create_progress() as progress:
            task = progress.add_task("[magenta]LLM 응답 중...", total=len(prompts))
            for p in prompts:
                response = llm.run(p.prompt)
                save_md_response(response, p.snippet, output_dir=llm_output_dir)
                progress.update(task, advance=1)
                
                time.sleep(0.05)
            progress.update(task, completed=100)

        click.secho(f"\n[ SUCCESS ] GPT 응답이 .md 파일로 저장 완료되었습니다!\n", fg="green")

        response_files = sorted([f.name for f in llm_output_dir.glob("response_*.md")])

        print_summary(
        repo_url=repo,
        detected_issues_count=len(merged),
        output_dir=str(llm_output_dir),
        #pr_status="생성 완료",
        response_files=response_files
)
        
if __name__ == '__main__':
    main()