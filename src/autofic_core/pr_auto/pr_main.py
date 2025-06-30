import os
from .create_yml import AboutYml
from .env_encrypt import EnvEncrypy
from .pr_procedure import PRProcedure

class BranchPRAutomation:
    def __init__(self, repo_url: str, save_dir: str):
        self.result = {
            "post_init": False,
            "mv_workdir": False,
            "check_branch": False,
            "discordwebhook": False,
            "slackwebhook": False,
            "create_yml": False,
            "push_yml": False,
            "change_files": False,
            "get_main_branch": False,
            "generate_pr": False,
            "create_upstream_pr": False,
            "error_msg": None,
        }
        self.branch_num = 1
        self.base_branch = 'main'
        self.branch_name = "UNKNOWN"
        self.repo_name = "UNKOWN"
        self.upstream_owner = "UNKOWN"
        self.save_dir = save_dir + '/repo'
        self.repo_url = repo_url.rstrip('/').replace('.git', '')
        self.secret_discord = os.getenv('DISCORD_WEBHOOK_URL')
        self.secret_slack = os.getenv('SLACK_WEBHOOK_URL')
        self.token = os.getenv('GITHUB_TOKEN')
        self.user_name = os.getenv('USER_NAME')
        self.slack_webhook = os.environ.get('SLACK_WEBHOOK_URL')
        self.discord_webhook = os.environ.get('DISCORD_WEBHOOK_URL')

    def run(self):
        pr_procedure = PRProcedure(
            self.base_branch, self.repo_name,
            self.upstream_owner, self.save_dir, self.repo_url,
            self.token, self.user_name
        )

        pr_procedure.post_init()
        self.repo_name = pr_procedure.repo_name
        self.upstream_owner = pr_procedure.upstream_owner
        self.result["post_init"] = True

        pr_procedure.mv_workdir()
        self.result["mv_workdir"] = True

        pr_procedure.check_branch_exists()
        self.branch_name = pr_procedure.branch_name
        self.result["check_branch"] = True

        EnvEncrypy(self.user_name, self.repo_name, self.token).webhook_secret_notifier('DISCORD_WEBHOOK_URL', self.secret_discord)
        self.result["discordwebhook"] = True

        EnvEncrypy(self.user_name, self.repo_name, self.token).webhook_secret_notifier('SLACK_WEBHOOK_URL', self.secret_slack)
        self.result["slackwebhook"] = True

        AboutYml().create_pr_yml()
        self.result["create_yml"] = True

        AboutYml().push_pr_yml(self.user_name, self.repo_name, self.token, self.branch_name)
        self.result["push_yml"] = True

        pr_procedure.change_files()
        self.result["change_files"] = True

        pr_procedure.current_main_branch()
        self.result["get_main_branch"] = True

        pr_procedure.generate_pr()
        self.result["generate_pr"] = True

        pr_procedure.create_pr_to_upstream()
        self.result["create_upstream_pr"] = True

        return self.result