import click
import json
import time
import os
from pathlib import Path
from rich.console import Console
from pyfiglet import Figlet
from dotenv import load_dotenv

from autofic_core.utils.progress_utils import create_progress
from autofic_core.download.github_repo_handler import GitHubRepoHandler
from autofic_core.sast.snippet import BaseSnippet 
from autofic_core.sast.semgrep.runner import SemgrepRunner
from autofic_core.sast.semgrep.preprocessor import SemgrepPreprocessor
from autofic_core.sast.codeql.runner import CodeQLRunner
from autofic_core.sast.codeql.preprocessor import CodeQLPreprocessor
from autofic_core.sast.snykcode.runner import SnykCodeRunner
from autofic_core.sast.snykcode.preprocessor import SnykCodePreprocessor
from autofic_core.sast.merger import merge_snippets_by_file
from autofic_core.llm.prompt_generator import PromptGenerator
from autofic_core.llm.llm_runner import LLMRunner, save_md_response
from autofic_core.llm.retry_prompt_generator import RetryPromptGenerator
from autofic_core.patch.diff_generator import DiffGenerator
from autofic_core.llm.response_parser import ResponseParser
from autofic_core.patch.apply_patch import PatchApplier
from autofic_core.pr_auto.create_yml import AboutYml
from autofic_core.pr_auto.env_encrypt import EnvEncrypy
from autofic_core.pr_auto.pr_procedure import PRProcedure
from autofic_core.log.log_writer import LogManager
from autofic_core.log.log_generator import LogGenerator

load_dotenv()
console = Console()

f = Figlet(font="slant")
ascii_art = f.renderText("AutoFiC")
console.print(f"[magenta]{ascii_art}[/magenta]")


def print_divider(title):
    console.print(f"\n[bold magenta]{'-'*20} [ {title} ] {'-'*20}[/bold magenta]\n")


def print_summary(repo_url: str, detected_issues_count: int, output_dir: str, response_files: list):
    print_divider("AutoFiC 작업 요약")
    console.print(f"✔️ [bold]분석 대상 저장소:[/bold] {repo_url}")
    console.print(f"✔️ [bold]취약점이 탐지된 파일:[/bold] {detected_issues_count} 개")

    if response_files:
        first_file = Path(response_files[0]).name
        last_file = Path(response_files[-1]).name
        console.print(f"✔️ [bold]저장된 응답 파일:[/bold] {first_file} ~ {last_file}")
    else:
        console.print(f"✔️ [bold]저장된 응답 파일:[/bold] 없음")
    console.print(f"\n[bold magenta]{'━'*64}[/bold magenta]\n")


def print_help_message():
    click.secho("\n\n [ AutoFiC CLI 사용 설명서 ]", fg="magenta", bold=True)
    click.echo("""

--explain       AutoFiC 사용 설명서 출력

--repo          분석할 GitHub 저장소 URL (필수)
--save-dir      분석 결과를 저장할 디렉토리 (기본: artifacts/downloaded_repo)

--sast          Semgrep 기반 정적 분석 실행, 사용할 SAST 도구 선택 (semgrep, codeql, eslint, snyk)

--llm           LLM을 통한 취약 코드 수정 및 응답 저장

\n※ 사용 예시:
    python -m autofic_core.cli --repo https://github.com/user/project --sast --llm

⚠️ 주의사항:
  - --llm 사용 시 --sast 옵션이 반드시 선행되어야 합니다.
    """)


class RepositoryManager:
    def __init__(self, repo_url: str, save_dir: Path):
        self.repo_url = repo_url
        self.save_dir = save_dir
        self.clone_path = None
        self.handler = GitHubRepoHandler(repo_url=self.repo_url)

    def clone(self):
        print_divider("저장소 다운로드 단계")

        if self.handler.needs_fork:
            console.print("\n저장소 Fork 시도 중...\n", style="cyan")
            self.handler.fork()
            time.sleep(1)
            console.print("\n[ SUCCESS ] Fork 완료\n", style="green")

        self.clone_path = Path(self.handler.clone_repo(save_dir=str(self.save_dir), use_forked=self.handler.needs_fork))
        console.print(f"\n[ SUCCESS ] 저장소 클론 완료: {self.clone_path}\n", style="green")


class SASTAnalyzer:
    def __init__(self, repo_path: Path, save_dir: Path, tool: str):
        self.repo_path = repo_path
        self.save_dir = save_dir
        self.tool = tool 
        self.result_path = None

    def run(self):
        print_divider("SAST 분석 단계")

        if self.tool == "semgrep":
            console.print("\nSemgrep 분석 시작\n")
            with create_progress() as progress:
                task = progress.add_task("[cyan]Semgrep 분석 진행 중...", total=100)
                for _ in range(100):
                    progress.update(task, advance=1)
                    time.sleep(0.01)

                semgrep_runner = SemgrepRunner(repo_path=str(self.repo_path), rule="p/javascript")
                semgrep_result_obj = semgrep_runner.run_semgrep()
                progress.update(task, completed=100)

            if semgrep_result_obj.returncode != 0:
                console.print(f"\n[ ERROR ] Semgrep 실행 실패 (리턴 코드: {semgrep_result_obj.returncode})\n", style="red")
                raise RuntimeError("Semgrep 실행 실패")

            sast_dir = self.save_dir / "sast"
            sast_dir.mkdir(parents=True, exist_ok=True)
            self.result_path = sast_dir / "before.json"

            SemgrepPreprocessor.save_json_file(
                json.loads(semgrep_result_obj.stdout),
                self.result_path
            )

            console.print(f"\n[ SUCCESS ] Semgrep 결과 저장 완료 (로그) →  {self.result_path}\n", style="green")

            snippets = SemgrepPreprocessor.preprocess(
                input_json_path=str(self.result_path),
                base_dir=str(self.repo_path)
            )
            merged_snippets = merge_snippets_by_file(snippets)

            merged_path = sast_dir / "merged_snippets.json"
            with open(merged_path, "w", encoding="utf-8") as f:
                json.dump([snippet.model_dump() for snippet in merged_snippets], f, indent=2, ensure_ascii=False)

            console.print(f"[ SUCCESS ] 병합된 스니펫 저장 완료 (로그) → {merged_path}\n", style="green")

            return merged_path

        elif self.tool == "codeql":
            console.print("\nCodeQL 분석 시작\n")
            with create_progress() as progress:
                task = progress.add_task("[cyan]CodeQL 분석 진행 중...", total=100)
                for _ in range(100):
                    progress.update(task, advance=1)
                    time.sleep(0.01)

                codeql_runner = CodeQLRunner(repo_path=str(self.repo_path))
                codeql_result_path = codeql_runner.run_codeql()
                progress.update(task, completed=100)

            sast_dir = self.save_dir / "sast"
            sast_dir.mkdir(parents=True, exist_ok=True)
            self.result_path = sast_dir / "before.json"

            with open(codeql_result_path, "r", encoding="utf-8") as f:
                sarif_data = json.load(f)

            CodeQLPreprocessor.save_json_file(sarif_data, self.result_path)

            console.print(f"\n[ SUCCESS ] CodeQL 결과 저장 완료 (로그) →  {self.result_path}\n", style="green")

            snippets = CodeQLPreprocessor.preprocess(
                input_json_path=str(self.result_path),
                base_dir=str(self.repo_path)
            )
            merged_snippets = merge_snippets_by_file(snippets)

            merged_path = sast_dir / "merged_snippets.json"
            with open(merged_path, "w", encoding="utf-8") as f:
                json.dump([snippet.model_dump() for snippet in merged_snippets], f, indent=2, ensure_ascii=False)

            console.print(f"[ SUCCESS ] 병합된 스니펫 저장 완료 (로그) → {merged_path}\n", style="green")

            return merged_path

        if self.tool == "snykcode":
            console.print("\nSnykCode 분석 시작\n")
            with create_progress() as progress:
                task = progress.add_task("[cyan]SnykCode 분석 진행 중...", total=100)
                for _ in range(100):
                    progress.update(task, advance=1)
                    time.sleep(0.01)

                snykcode_runner = SnykCodeRunner(repo_path=str(self.repo_path))
                snykcode_result_obj = snykcode_runner.run_snykcode()
                progress.update(task, completed=100)

            sast_dir = self.save_dir / "sast"
            sast_dir.mkdir(parents=True, exist_ok=True)
            self.result_path = sast_dir / "before.json"

            SnykCodePreprocessor.save_json_file(
                json.loads(snykcode_result_obj.stdout),
                self.result_path
            )

            console.print(f"\n[ SUCCESS ] SnykCode 결과 저장 완료 (로그) →  {self.result_path}\n", style="green")

            snippets = SnykCodePreprocessor.preprocess(
                input_json_path=str(self.result_path),
                base_dir=str(self.repo_path)
            )
            merged_snippets = merge_snippets_by_file(snippets)

            merged_path = sast_dir / "merged_snippets.json"
            with open(merged_path, "w", encoding="utf-8") as f:
                json.dump([snippet.model_dump() for snippet in merged_snippets], f, indent=2, ensure_ascii=False)

            console.print(f"[ SUCCESS ] 병합된 스니펫 저장 완료 (로그) → {merged_path}\n", style="green")

            return merged_path

    def save_snippets(self, merged_snippets_path: Path):
        with open(merged_snippets_path, "r", encoding="utf-8") as f:
            merged_snippets = json.load(f)

        snippets_dir = self.save_dir / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)

        for snippet_data in merged_snippets:
            if isinstance(snippet_data, dict):
                snippet_obj = BaseSnippet(**snippet_data)
            elif isinstance(snippet_data, BaseSnippet):
                snippet_obj = snippet_data
            else:
                raise TypeError(f"[ ERROR ] 알 수 없는 snippet 형식: {type(snippet_data)}")
            
            filename_base = snippet_obj.path.replace("\\", "_").replace("/", "_")
            filename = f"snippet_{filename_base}.json"
            path = snippets_dir / filename

            with open(path, "w", encoding="utf-8") as f_out:
                json.dump(snippet_obj.snippet, f_out, indent=2, ensure_ascii=False)

        console.print(f"[ SUCCESS ] 스니펫 저장 완료 (로그) → {snippets_dir}\n", style="green")


class LLMProcessor:
    def __init__(self, sast_result_path: Path, repo_path: Path, save_dir: Path, tool: str):
        self.sast_result_path = sast_result_path
        self.repo_path = repo_path
        self.save_dir = save_dir
        self.tool = tool
        self.llm_output_dir = save_dir / "llm"
        self.parsed_dir = save_dir / "parsed"

    def run(self):
        print_divider("LLM 응답 생성 단계")

        prompt_generator = PromptGenerator()
        merged_path = self.save_dir / "sast" / "merged_snippets.json"
        with open(merged_path, "r", encoding="utf-8") as f:
            merged_data = json.load(f)
        file_snippets = [BaseSnippet(**item) for item in merged_data]
        prompts = prompt_generator.generate_prompts(file_snippets)

        llm = LLMRunner()
        self.llm_output_dir.mkdir(parents=True, exist_ok=True)

        console.print("\nGPT 응답 생성 및 저장 시작\n")
        with create_progress() as progress:
            task = progress.add_task("[magenta]LLM 응답 중...", total=len(prompts))
            for p in prompts:
                response = llm.run(p.prompt)
                save_md_response(response, p, output_dir=self.llm_output_dir)
                progress.update(task, advance=1)
                time.sleep(0.01)
            progress.update(task, completed=100)

        console.print(f"\n[ SUCCESS ] LLM 응답 저장 완료 (로그) → {self.llm_output_dir}\n", style="green")
        return prompts, file_snippets

    def retry(self):
        print_divider("LLM 재실행 단계")
        console.print("[RETRY] 수정된 코드에 대해 GPT 재실행 중...\n")

        retry_output_dir = self.save_dir / "llm_retry"
        parsed_dir = self.save_dir / "parsed"  # 기존 응답
        retry_output_dir.mkdir(parents=True, exist_ok=True)

        diff_gen = DiffGenerator(repo_dir=self.repo_path, parsed_dir=parsed_dir, patch_dir=self.save_dir / "retry_diff")
        diff_gen.run()

        retry_prompts = RetryPromptGenerator().generate_prompts(diff_gen.load_diffs())

        llm = LLMRunner()
        for prompt in retry_prompts:
            response = llm.run(prompt.prompt)
            save_md_response(response, prompt.snippet, output_dir=retry_output_dir)

        console.print(f"\n[ SUCCESS ] 재검토 GPT 응답 저장 완료 → {retry_output_dir}\n", style="green")

    def extract_and_save_parsed_code(self):
        print_divider("LLM 응답 코드 추출 및 저장 단계")
        parser = ResponseParser(md_dir=self.llm_output_dir, diff_dir=self.parsed_dir)
        success = parser.extract_and_save_all()

        if success:
            console.print(f"\n[ SUCCESS ] 파싱된 코드 저장 완료 (로그) → {self.parsed_dir}\n", style="green")
        else:
            console.print(f"\n[ WARN ] 파싱된 코드가 없습니다.\n", style="yellow")


class PatchManager:
    def __init__(self, parsed_dir: Path, patch_dir: Path, repo_dir: Path):
        self.parsed_dir = parsed_dir
        self.patch_dir = patch_dir
        self.repo_dir = repo_dir

    def run(self):
        print_divider("Diff 생성 및 패치 적용 단계")

        from autofic_core.patch.diff_generator import DiffGenerator
        diff_generator = DiffGenerator(
            repo_dir=self.repo_dir,
            parsed_dir=self.parsed_dir,
            patch_dir=self.patch_dir,
        )
        diff_generator.run()
        console.print(f"\n[ SUCCESS ] Diff 생성 완료 → {self.patch_dir}\n", style="green")

        patch_applier = PatchApplier(
            patch_dir=self.patch_dir,
            repo_dir=self.repo_dir,
            parsed_dir=self.parsed_dir,  
        )
        success = patch_applier.apply_all()

        if success:
            console.print(f"\n[ SUCCESS ] 모든 패치 적용 완료 → {self.repo_dir}\n", style="green")
        else:
            console.print(f"\n[ WARN ] 일부 패치 적용 실패 발생 → {self.repo_dir}\n", style="yellow")


class AutoFiCPipeline:
    def __init__(self, repo_url: str, save_dir: Path, sast: bool, sast_tool: str, llm: bool, llm_retry: bool):
        self.repo_url = repo_url
        self.save_dir = save_dir.expanduser().resolve()
        self.sast = sast
        self.llm = llm
        self.sast_tool = sast_tool
        self.llm_retry = llm_retry

        self.repo_manager = RepositoryManager(self.repo_url, self.save_dir)
        self.sast_analyzer = None
        self.llm_processor = None

    def run(self):
        self.repo_manager.clone()

        sast_result_path = None
        if self.sast:
            self.sast_analyzer = SASTAnalyzer(
            self.repo_manager.clone_path,
            self.save_dir,
            tool=self.sast_tool,
            )
            sast_result_path = self.sast_analyzer.run()
            self.sast_analyzer.save_snippets(sast_result_path)

        if self.llm:
            if not sast_result_path:
                raise RuntimeError("LLM 실행 시 SAST 결과 필요")

            self.llm_processor = LLMProcessor(sast_result_path, self.repo_manager.clone_path, self.save_dir, self.sast_tool)
            prompts, file_snippets = self.llm_processor.run()
            self.llm_processor.extract_and_save_parsed_code()

            prompt_generator = PromptGenerator()
            unique_file_paths = prompt_generator.get_unique_file_paths(file_snippets)

            llm_output_dir = self.llm_processor.llm_output_dir
            response_files = sorted([f.name for f in llm_output_dir.glob("response_*.md")])

            print_summary(
                repo_url=self.repo_url,
                detected_issues_count=len(unique_file_paths),
                output_dir=str(llm_output_dir),
                response_files=response_files
            )
            
        if self.llm_retry:
            if not self.llm_processor:
                raise RuntimeError("LLM 재실행은 --llm 실행 후만 수행됩니다.")
            self.llm_processor.retry()

SAST_TOOL_CHOICES = ['semgrep', 'codeql', 'eslint', 'snykcode']
@click.command()
@click.option('--explain', is_flag=True, help="AutoFiC 사용 설명서 출력")
@click.option('--repo', required=False, help="분석할 GitHub 저장소 URL (필수)")
@click.option('--save-dir', default="artifacts/downloaded_repo", help="분석 결과 저장 디렉토리")
@click.option(
    '--sast',
    type=click.Choice(SAST_TOOL_CHOICES, case_sensitive=False),
    required=False,
    help='사용할 SAST 도구 선택 (semgrep, codeql, eslint, snykcode 중 하나)'
)
@click.option('--llm', is_flag=True, help="LLM을 통한 취약 코드 수정 및 응답 저장")
@click.option('--llm-retry', is_flag=True, help="LLM 재실행을 통한 최종 확인 및 수정")
@click.option('--patch', is_flag=True, help="diff 생성 및 git apply로 패치")
@click.option('--pr', is_flag=True, help="PR 자동 생성까지 수행")


def main(explain, repo, save_dir, sast, llm, llm_retry, patch, pr):
    log_manager = LogManager()
    log_gen = LogGenerator()
    
    if explain:
        print_help_message()
        return

    if not repo:
        click.echo(" --repo는 필수입니다!", err=True)
        return

    if llm and llm_retry:
        click.secho("[ ERROR ] --llm-retry 옵션은 --llm 옵션이 자동으로 함께 실행됩니다!", fg="red")
        return

    if not sast and (llm or llm_retry):
        click.secho("[ ERROR ] --llm 또는 --llm-retry 옵션은 --sast 없이 단독 사용 불가!", fg="red")
        return

    try:
        llm_flag = llm or llm_retry
        pipeline = AutoFiCPipeline(repo, Path(save_dir), sast, llm=llm_flag, llm_retry=llm_retry, sast_tool=sast.lower())
        pipeline.run()

        if patch:
            parsed_dir = Path(save_dir) / "parsed"
            patch_dir = Path(save_dir) / "patch"
            repo_dir = pipeline.repo_manager.clone_path

            patch_manager = PatchManager(parsed_dir, patch_dir, repo_dir)
            patch_manager.run()

        if pr:
            # PR 자동화
            branch_num = 1
            base_branch = 'main'
            branch_name = "UNKNOWN"
            repo_name = "UNKOWN"
            upstream_owner = "UNKOWN"
            save_dir = Path(save_dir).joinpath('repo')
            repo_url = repo.rstrip('/').replace('.git', '')
            secret_discord = os.getenv('DISCORD_WEBHOOK_URL')
            secret_slack = os.getenv('SLACK_WEBHOOK_URL')
            token = os.getenv('GITHUB_TOKEN')
            user_name = os.getenv('USER_NAME')
            slack_webhook = os.environ.get('SLACK_WEBHOOK_URL')
            discord_webhook = os.environ.get('DISCORD_WEBHOOK_URL')

            # Define PRProcedure class
            json_path = str(save_dir.parent / "sast" / "before.json") 
            tool = sast.lower()
            pr_procedure = PRProcedure(
                base_branch, repo_name, upstream_owner, 
                save_dir, repo_url, token, user_name, json_path, tool
            )
            # Chapter 1
            pr_procedure.post_init()
            repo_name = pr_procedure.repo_name
            upstream_owner = pr_procedure.upstream_owner
            # Chaper 2
            pr_procedure.mv_workdir()
            # Chapter 3
            pr_procedure.check_branch_exists()
            branch_name = pr_procedure.branch_name
            # Chapter 4
            EnvEncrypy(user_name, repo_name, token).webhook_secret_notifier('DISCORD_WEBHOOK_URL', secret_discord)
            EnvEncrypy(user_name, repo_name, token).webhook_secret_notifier('SLACK_WEBHOOK_URL', secret_slack)
            # Chapter 5
            AboutYml().create_pr_yml()
            AboutYml().push_pr_yml(user_name, repo_name, token, branch_name)
            # Chapter 6
            pr_procedure.change_files()
            # Chapter 7
            pr_procedure.current_main_branch()
            # Chapter 8,9
            pr_procedure.generate_pr()
            pr_procedure.create_pr()
            # for pr_log
            pr_log_data = log_gen.generate_pr_log(user_name=user_name, repo_url=repo_url, approved=False)
            log_manager.add_pr_log(pr_log_data)
            
            # for repo_log
            repo_data = log_gen.generate_repo_log(save_dir=save_dir.parent, name=repo_name, owner=upstream_owner, repo_url=repo_url,
            sastTool=tool, rerun=llm_retry)
            log_manager.add_repo_status(repo_data)

    except Exception as e:
        console.print(f"[ ERROR ] {e}", style="red")
    
if __name__ == "__main__":
    main()