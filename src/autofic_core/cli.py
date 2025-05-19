import click

@click.command()
@click.option('--repo', help='GitHub repository URL')
def main(repo):
    click.echo(f"Analyzing repo: {repo}")

if __name__ == '__main__':
    main()