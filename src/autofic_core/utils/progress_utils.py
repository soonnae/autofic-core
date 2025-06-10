from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

def create_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=None, style="green", complete_style="green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        transient=False
    )