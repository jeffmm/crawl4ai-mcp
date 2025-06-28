import click

from .types import TransportType


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "html"]),
    default="stdio",
    help="Transport type",
)
def main(transport: TransportType) -> None:
    from .server import app

    if transport == "http":
        app.run(transport="streamable-http")
    else:
        app.run(transport="stdio")


if __name__ == "__main__":
    main()
