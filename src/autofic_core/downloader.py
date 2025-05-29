import os
import requests
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
import time

def download_files(js_files, save_dir="downloaded_repo"):
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=None, style="green", complete_style="green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        transient=False

    ) as progress:
        task2 = progress.add_task("[cyan]파일 다운로드 중...", total=len(js_files))

        for file in js_files:
            progress.update(task2, advance=1)
            time.sleep(0.05)
            path = file["path"]
            url = file["download_url"]
            local_path = os.path.join(save_dir, path)

            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            if os.path.exists(local_path):
                results.append({"path": path, "status": "skipped"})
                continue

            try:
                response = requests.get(url)
                response.raise_for_status()

                with open(local_path, "wb") as f:
                    f.write(response.content)
                results.append({"path": path, "status": "success"})
            except Exception as e:
                results.append({"path": path, "status": "fail", "error": str(e)})

        progress.update(task2, completed=100)

    return results
