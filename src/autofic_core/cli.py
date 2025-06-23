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

load_dotenv()        

@click.command()
@click.option('--repo', help='GitHub repository URL')
@click.option('--save-dir', default=os.getenv("DOWNLOAD_SAVE_DIR"), help="저장할 디렉토리 경로")
@click.option('--sast', is_flag=True, help='SAST 분석 수행 여부')
@click.option('--rule', default=os.getenv("SEMGREP_RULE"), help='Semgrep 규칙')
@click.option('--semgrep-result', default=os.getenv("SEMGREP_RESULT_PATH"), help="Semgrep 원본 결과 경로")

def main(repo, save_dir, sast, rule, semgrep_result):
    run_cli(repo, save_dir, sast, rule, semgrep_result)

def run_cli(repo, save_dir, sast, rule, semgrep_result):
    
    """ GitHub 저장소 fork 및 클론 """
    
    handler = GitHubRepoHandler(repo_url=repo)

    if handler.needs_fork:
        click.secho(f"\n저장소에 대한 Fork를 시도합니다...\n", fg="cyan")
        handler.fork()
        time.sleep(0.05)
        click.secho(f"\n[ SUCCESS ] 저장소를 성공적으로 Fork 했습니다!\n", fg="green")
    
    clone_path = handler.clone_repo(save_dir=save_dir, use_forked=handler.needs_fork)
    click.secho(f"\n[ SUCCESS ] 저장소를 {clone_path}에 클론했습니다!\n", fg="green")

    """ Semgrep 분석  """

    if sast:
        click.echo("\nSemgrep 분석 시작\n")
        with create_progress() as progress:
            task = progress.add_task("[cyan]Semgrep 분석 진행 중...", total=100)
            for _ in range(100):
                progress.update(task, advance=1)
                time.sleep(0.05)  
            semgrep_runner = SemgrepRunner(repo_path=save_dir, rule=rule)
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

        SemgrepPreprocessor.save_json_file(json.loads(semgrep_result_obj.stdout), semgrep_result)
        click.secho(f"\n[ SUCCESS ] Semgrep 분석 완료! 결과가 '{semgrep_result}'에 저장되었습니다.\n", fg="green")

        processed = SemgrepPreprocessor.preprocess(semgrep_result)

        ''' processed 활용해서 이후 개발 '''
        vulnerable_snippets = [s for s in processed if s.message.strip()]
        prompts = PromptGenerator().generate_prompts(vulnerable_snippets)

        '''LLM 호출 및 응답 저장 및 diff 생성 및 저장'''
        llm = LLMRunner()
        click.echo("\nGPT 응답 생성 및 저장 시작\n")
        
        with create_progress() as progress:
            task = progress.add_task("[magenta]LLM 응답 중...", total=len(vulnerable_snippets))
            for p in prompts:
                response = llm.run(p.prompt)
                save_md_response(response, p.snippet)
                progress.update(task, advance=1)
                time.sleep(0.05)
            progress.update(task, completed=100)

        click.secho(f"\n[ SUCCESS ] GPT 응답이 .md 파일로 저장 완료되었습니다!\n", fg="green")
        
        """ LLM 응답 파싱 및 diff 생성 """
        llm_response_dir = Path("artifacts/llm")
        md_files = sorted(llm_response_dir.glob("response_*.md"))

        parsed_blocks = []
        for path in md_files:
            parsed_blocks.extend(LLMResponseParser.load_and_parse(path))
        
        diff_generator = DiffGenerator()
        results = diff_generator.generate_from_blocks(parsed_blocks)

        click.echo()
        for r in results:
            if r.success:
                click.secho(f"[DIFF SUCCESS] {r.filename} → 저장 완료", fg="green")
            else:
                click.secho(f"[DIFF FAIL] {r.filename} → {r.error}", fg="red")

if __name__ == '__main__':
    main()