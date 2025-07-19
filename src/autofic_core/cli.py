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
    print_divider("AutoFiC Summary")
    console.print(f"✔️ [bold]Target Repository:[/bold] {repo_url}")
    console.print(f"✔️ [bold]Files with detected vulnerabilities:[/bold] {detected_issues_count} 개")

    if response_files:
        first_file = Path(response_files[0]).name
        last_file = Path(response_files[-1]).name
        console.print(f"✔️ [bold]Saved response files:[/bold] {first_file} ~ {last_file}")
    else:
        console.print(f"✔️ [bold]Saved response files:[/bold] None")
    console.print(f"\n[bold magenta]{'━'*64}[/bold magenta]\n")


def print_help_message():
    click.secho("\n\n [ AutoFiC CLI Usage Guide ]", fg="magenta", bold=True)
    click.echo("""

--explain       Display AutoFiC usage guide

--repo          GitHub repository URL to analyze (required)
--save-dir      Directory to save analysis results (default: artifacts/downloaded_repo)

--sast          Run SAST analysis using selected tool (semgrep, codeql, snyk)

--llm           Run LLM to fix vulnerable code and save response
--llm-retry     Re-run LLM to verify and finalize code

\n※ Example usage:
    python -m autofic_core.cli --repo https://github.com/user/project --sast --llm

⚠️ Note:
  - The --sast option must be run before using --llm or --llm-retry
    """)


class RepositoryManager:
    def __init__(self, repo_url: str, save_dir: Path):
        self.repo_url = repo_url
        self.save_dir = save_dir
        self.clone_path = None
        self.handler = GitHubRepoHandler(repo_url=self.repo_url)

    def clone(self):
        print_divider("Repository Cloning Stage")

        if self.handler.needs_fork:
            console.print("\nAttempting to fork the repository...\n", style="cyan")
            self.handler.fork()
            time.sleep(1)
            console.print("\n[ SUCCESS ] Fork completed\n", style="green")

        self.clone_path = Path(self.handler.clone_repo(save_dir=str(self.save_dir), use_forked=self.handler.needs_fork))
        console.print(f"\n[ SUCCESS ] Repository cloned successfully: {self.clone_path}\n", style="green")


class SASTAnalyzer:
    def __init__(self, repo_path: Path, save_dir: Path, tool: str):
        self.repo_path = repo_path
        self.save_dir = save_dir
        self.tool = tool 
        self.result_path = None

    def run(self):
        print_divider("SAST Analysis Stage")

        if self.tool == "semgrep":
            console.print("\nStarting Semgrep analysis\n")
            with create_progress() as progress:
                task = progress.add_task("[cyan]Running Semgrep...", total=100)
                for _ in range(100):
                    progress.update(task, advance=1)
                    time.sleep(0.01)

                semgrep_runner = SemgrepRunner(repo_path=str(self.repo_path), rule="p/javascript")
                semgrep_result_obj = semgrep_runner.run_semgrep()
                progress.update(task, completed=100)

            if semgrep_result_obj.returncode != 0:
                console.print(f"\n[ ERROR ] Semgrep failed (return code: {semgrep_result_obj.returncode})\n", style="red")
                raise RuntimeError("Semgrep execution failed")

            sast_dir = self.save_dir / "sast"
            sast_dir.mkdir(parents=True, exist_ok=True)
            self.result_path = sast_dir / "before.json"

            SemgrepPreprocessor.save_json_file(
                json.loads(semgrep_result_obj.stdout),
                self.result_path
            )

            console.print(f"\n[ SUCCESS ] Semgrep results saved →  {self.result_path}\n", style="green")

            snippets = SemgrepPreprocessor.preprocess(
                input_json_path=str(self.result_path),
                base_dir=str(self.repo_path)
            )
            merged_snippets = merge_snippets_by_file(snippets)

            merged_path = sast_dir / "merged_snippets.json"
            with open(merged_path, "w", encoding="utf-8") as f:
                json.dump([snippet.model_dump() for snippet in merged_snippets], f, indent=2, ensure_ascii=False)

            console.print(f"[ SUCCESS ] Merged snippets saved → {merged_path}\n", style="green")

            return merged_path

        elif self.tool == "codeql":
            console.print("\nStarting CodeQL analysis\n")
            with create_progress() as progress:
                task = progress.add_task("[cyan]Running CodeQL...", total=100)
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

            console.print(f"\n[ SUCCESS ] CodeQL results saved →  {self.result_path}\n", style="green")

            snippets = CodeQLPreprocessor.preprocess(
                input_json_path=str(self.result_path),
                base_dir=str(self.repo_path)
            )
            merged_snippets = merge_snippets_by_file(snippets)

            merged_path = sast_dir / "merged_snippets.json"
            with open(merged_path, "w", encoding="utf-8") as f:
                json.dump([snippet.model_dump() for snippet in merged_snippets], f, indent=2, ensure_ascii=False)

            console.print(f"[ SUCCESS ] Merged snippets saved → {merged_path}\n", style="green")

            return merged_path

        if self.tool == "snykcode":
            console.print("\nStarting SnykCode analysis\n")
            with create_progress() as progress:
                task = progress.add_task("[cyan]Running SnykCode...", total=100)
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

            console.print(f"\n[ SUCCESS ] SnykCode results saved →  {self.result_path}\n", style="green")

            snippets = SnykCodePreprocessor.preprocess(
                input_json_path=str(self.result_path),
                base_dir=str(self.repo_path)
            )
            merged_snippets = merge_snippets_by_file(snippets)

            merged_path = sast_dir / "merged_snippets.json"
            with open(merged_path, "w", encoding="utf-8") as f:
                json.dump([snippet.model_dump() for snippet in merged_snippets], f, indent=2, ensure_ascii=False)

            console.print(f"[ SUCCESS ] Merged snippets successfully saved → {merged_path}\n", style="green")

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
                raise TypeError(f"[ ERROR ] Unknown snippet type: {type(snippet_data)}")
            
            filename_base = snippet_obj.path.replace("\\", "_").replace("/", "_")
            filename = f"snippet_{filename_base}.json"
            path = snippets_dir / filename

            with open(path, "w", encoding="utf-8") as f_out:
                json.dump(snippet_obj.snippet, f_out, indent=2, ensure_ascii=False)

        console.print(f"[ SUCCESS ] Snippets saved → {snippets_dir}\n", style="green")


class LLMProcessor:
    def __init__(self, sast_result_path: Path, repo_path: Path, save_dir: Path, tool: str):
        self.sast_result_path = sast_result_path
        self.repo_path = repo_path
        self.save_dir = save_dir
        self.tool = tool
        self.llm_output_dir = save_dir / "llm"
        self.parsed_dir = save_dir / "parsed"
        self.patch_dir = save_dir / "patch"  

    def run(self):
        print_divider("LLM Response Generation Stage")

        prompt_generator = PromptGenerator()
        merged_path = self.save_dir / "sast" / "merged_snippets.json"
        with open(merged_path, "r", encoding="utf-8") as f:
            merged_data = json.load(f)
        file_snippets = [BaseSnippet(**item) for item in merged_data]
        prompts = prompt_generator.generate_prompts(file_snippets)

        llm = LLMRunner()
        self.llm_output_dir.mkdir(parents=True, exist_ok=True)

        console.print("\nStarting GPT response generation\n")
        with create_progress() as progress:
            task = progress.add_task("[magenta]Generating LLM responses...", total=len(prompts))
            for p in prompts:
                response = llm.run(p.prompt)
                save_md_response(response, p, output_dir=self.llm_output_dir)
                progress.update(task, advance=1)
                time.sleep(0.01)
            progress.update(task, completed=100)

        console.print(f"\n[ SUCCESS ] LLM responses saved → {self.llm_output_dir}\n", style="green")
        return prompts, file_snippets
    
    def retry(self):
        print_divider("LLM Retry Stage")

        retry_prompt_generator = RetryPromptGenerator(parsed_dir=self.parsed_dir)
        retry_prompts = retry_prompt_generator.generate_prompts()

        console.print("[RETRY] Regenerating GPT responses for modified files...\n")

        llm = LLMRunner() 
        retry_output_dir = self.save_dir / "retry_llm"
        retry_output_dir.mkdir(parents=True, exist_ok=True)

        console.print("\nStarting GPT retry response generation\n")
        with create_progress() as progress:
            task = progress.add_task("[magenta]Retrying LLM responses...", total=len(retry_prompts))
            for prompt in retry_prompts:
                response = llm.run(prompt.prompt)
                save_md_response(response, prompt, output_dir=retry_output_dir)
                progress.update(task, advance=1)
                time.sleep(0.01)
            progress.update(task, completed=100)

        console.print(f"\n[ SUCCESS ] Retry LLM responses saved → {retry_output_dir}\n", style="green")

        return retry_prompts, retry_output_dir
    
    def extract_and_save_parsed_code(self):
        print_divider("LLM Response Parsing Stage")
        parser = ResponseParser(md_dir=self.llm_output_dir, diff_dir=self.parsed_dir)
        success = parser.extract_and_save_all()

        if success:
            console.print(f"\n[ SUCCESS ] Parsed code saved→ {self.parsed_dir}\n", style="green")
        else:
            console.print(f"\n[ WARN ] No parsable content found in LLM responses.\n", style="yellow")

class PatchManager:
    def __init__(self, parsed_dir: Path, patch_dir: Path, repo_dir: Path):
        self.parsed_dir = parsed_dir
        self.patch_dir = patch_dir
        self.repo_dir = repo_dir

    def run(self):
        print_divider("Diff Generation and Patch Application Stage")

        from autofic_core.patch.diff_generator import DiffGenerator
        diff_generator = DiffGenerator(
            repo_dir=self.repo_dir,
            parsed_dir=self.parsed_dir,
            patch_dir=self.patch_dir,
        )
        diff_generator.run()
        time.sleep(0.1)
        console.print(f"\n[ SUCCESS ] Diff files generated → {self.patch_dir}\n", style="green")

        patch_applier = PatchApplier(
            patch_dir=self.patch_dir,
            repo_dir=self.repo_dir,
            parsed_dir=self.parsed_dir,  
        )
        success = patch_applier.apply_all()

        if success:
            console.print(f"\n[ SUCCESS ] All patches successfully applied → {self.repo_dir}\n", style="green")
        else:
            console.print(f"\n[ WARN ] Some patches failed to apply → {self.repo_dir}\n", style="yellow")


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
                raise RuntimeError("SAST results are required before running LLM.")

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
                raise RuntimeError("LLM retry can only be executed after the initial LLM run.")            

            patch_manager = PatchManager(self.llm_processor.parsed_dir, self.llm_processor.patch_dir, self.repo_manager.clone_path)
            patch_manager.run()
            
            retry_prompts, retry_output_dir = self.llm_processor.retry()
            self.llm_processor.parsed_dir = self.save_dir / "retry_parsed"
            self.llm_processor.llm_output_dir = retry_output_dir
            self.llm_processor.extract_and_save_parsed_code()

            prompt_generator = RetryPromptGenerator(parsed_dir=self.llm_processor.parsed_dir)
            unique_file_paths = prompt_generator.get_unique_file_paths(retry_prompts)
            
            llm_output_dir = self.llm_processor.llm_output_dir
            response_files = sorted([f.name for f in llm_output_dir.glob("response_*.md")])
            
            print_summary(
                repo_url=self.repo_url,
                detected_issues_count=len(unique_file_paths),
                output_dir=str(retry_output_dir),
                response_files=response_files
            )

SAST_TOOL_CHOICES = ['semgrep', 'codeql', 'snykcode']
@click.command()
@click.option('--explain', is_flag=True, help="Print AutoFiC usage guide.")
@click.option('--repo', required=False, help="Target GitHub repository URL to analyze (required).")
@click.option('--save-dir', default="artifacts/downloaded_repo", help="Directory to save analysis results.")
@click.option(
    '--sast',
    type=click.Choice(SAST_TOOL_CHOICES, case_sensitive=False),
    required=False,
    help='Select SAST tool to use (choose one of: semgrep, codeql, snykcode).'
)
@click.option('--llm', is_flag=True, help="Run LLM to fix vulnerable code and save responses.")
@click.option('--llm-retry', is_flag=True, help="Re-run LLM for final verification and fixes.")
@click.option('--patch', is_flag=True, help="Generate diffs and apply patches using git.")
@click.option('--pr', is_flag=True, help="Automatically create a pull request.")


def main(explain, repo, save_dir, sast, llm, llm_retry, patch, pr):
    log_manager = LogManager()
    log_gen = LogGenerator()
    
    if explain:
        print_help_message()
        return

    if not repo:
        click.echo(" --repo is required!", err=True)
        return

    if llm and llm_retry:
        click.secho("[ ERROR ]  The --llm-retry option includes --llm automatically. Do not specify both!", fg="red")
        return

    if not sast and (llm or llm_retry):
        click.secho("[ ERROR ] The --llm or --llm-retry options cannot be used without --sast!", fg="red")
        return

    try:
        llm_flag = llm or llm_retry
        pipeline = AutoFiCPipeline(repo, Path(save_dir), sast, llm=llm_flag, llm_retry=llm_retry, sast_tool=sast.lower())
        pipeline.run()
        repo_dir = pipeline.repo_manager.clone_path

        if patch:
            parsed_dir = Path(save_dir) / "retry_parsed" if llm_retry else Path(save_dir) / "parsed"
            retry_patch_dir = Path(save_dir) / "retry_patch"
            patch_dir = retry_patch_dir if llm_retry else Path(save_dir) / "patch"

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
            pr_number = pr_procedure.generate_pr()
            pr_procedure.create_pr()

            # for log
            repo_data = log_gen.generate_repo_log(save_dir=save_dir.parent, name=repo_name, owner=upstream_owner,
            repo_url=repo_url, sastTool=tool, rerun=llm_retry)
            pr_log_data = log_gen.generate_pr_log(owner=upstream_owner, repo=repo_name, user_name=user_name, repo_url=repo_url, repo_hash=repo_data["repo_hash"], pr_number=pr_number)
            log_manager.add_pr_log(pr_log_data)
            log_manager.add_repo_status(repo_data)

    except Exception as e:
        console.print(f"[ ERROR ] {e}", style="red")
    
if __name__ == "__main__":
    main()