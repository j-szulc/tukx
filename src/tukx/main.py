import logging
import sys
import uuid
import os
import shlex
import pathlib
import jinja2
import click

try:
    import pyperclip
    copy = pyperclip.copy
except ImportError:
    copy = lambda *_: None

from tukx import __version__

__author__ = "Jakub Szulc"
__copyright__ = "Jakub Szulc"
__license__ = "MIT"

_logger = logging.getLogger(__name__)

__jinja2_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(pathlib.Path(__file__).parent / "templates")),
    autoescape=jinja2.select_autoescape(),
    lstrip_blocks=True,
    trim_blocks=True
)

def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )

def parse_command_input(command_input, shell=False):
    command_input = [line for line in command_input.splitlines() if line.strip()]
    if not command_input:
        return ""
    if len(command_input) > 1 and not shell:
        raise click.ClickException("No-shell mode requires a single command")

    get_exec = lambda line: shlex.split(line)[0]
    command_input = [line.replace(get_exec(line),r"$(which "+get_exec(line)+")",1) for line in command_input]

    if not shell:
        return command_input[0]

    command_input = "\n".join(command_input)
    result = shlex.join(["/REPLACE/ME", "-c", command_input])
    return result.replace("/REPLACE/ME", r"$(which sh)")

def fix_envlist(envlist):
    for arg in envlist:
        # Note: that's a very rudimentary check, do not rely on it.
        if "=" not in arg:
            raise click.ClickException("Invalid environment variable: {}. Format: NAME=VALUE".format(arg))
        name, value = arg.split("=", 1)
        if not all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in name):
            raise click.ClickException("Invalid environment variable name: {}".format(name))
        if not value.isprintable():
            raise click.ClickException("Invalid environment variable value: {}".format(value))
        yield "{}={}".format(name, value)


def inline_file(src_content, dst_path, sudo=False):
    EOF = "EOF"
    if EOF in src_content:
        EOF = "EOF-{}".format(uuid.uuid4())
    if EOF in src_content:
        raise click.ClickException("EOF string found in source content")
    return __jinja2_env.get_template("inline-file.sh.j2").render(dst_path=dst_path, src_content=src_content,
                                                                        EOF=EOF, sudo=sudo)


@click.group()
def cli():
    pass

@cli.command("gen")
@click.option("--verbose", is_flag=True, help="Enables verbose mode.")
@click.option("--description", default=None)
@click.option("--unit", "-n", default=None, help="Name of the service [default: random]")
@click.option("--user", help="Run service as user [default: current user]")
@click.option("--group", help="Run service as group [default: equal to --user]")
@click.option("--restart", default="no", show_default=True, help="Restart policy")
@click.option("--working-directory", default=None,
              help="Working directory [default: home]")
@click.option("--environment", "-E", default=[], multiple=True, help="Environment variables", metavar="NAME=VALUE")
@click.option("--system-wide/--user-wide", default=True, show_default=True,
              help="Install service system-wide or user-wide")
@click.option("--shell/--no-shell", default=False, show_default=True, help="Run command in shell.")
@click.option("--install/--dont-install", default=True, show_default=True, help="Install the service")
@click.option("--replace", is_flag=True, help="Replace existing service, if exists.")
@click.option("--enable", is_flag=True, help="Add a command to enable the service")
@click.option("--now", is_flag=True, help="Add a command to start the service and view status")
def tukx_gen(verbose, description, unit, user, group, restart, working_directory, environment,
         system_wide, shell, install, replace, enable, now):
    """
    Generate a systemd service file.
    """
    if verbose:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.WARNING)

    if not system_wide and user:
        raise click.ClickException("If --user-wide specified then --user is unneccesary")
    if not system_wide and group:
        raise click.ClickException("If --user-wide specified then --group is unneccesary")
    if enable and not install:
        raise click.ClickException("--enable requires --install")
    if enable and not unit:
        raise click.ClickException("--enable requires unit name (set with --unit)")

    if system_wide and not user:
        user = os.getlogin()
    if system_wide and not group:
        group = user
    if not working_directory:
        working_directory = "~"
    elif working_directory.strip() == ".":
        working_directory = os.getcwd()
    working_directory = working_directory.replace("~", "%h")

    if not unit:
        unit = "tukx-temp-{}".format(uuid.uuid4())

    environment = fix_envlist(environment)

    command = parse_command_input(click.edit(), shell).replace("\n", "\\\n")
    if command is None:
        raise click.ClickException("No command specified")

    service = __jinja2_env.get_template("permanent.service.j2").render(
        description=description,
        unit=unit,
        user=user,
        group=group,
        working_directory=working_directory,
        environment=environment,
        command=command,
        restart=restart,
        install=install,
    )

    target_folder = "/etc/systemd/system" if system_wide else "/etc/systemd/user"
    target_path = os.path.join(target_folder, "{}.service".format(unit))
    service_command = inline_file(service, target_path, sudo=True)

    result = __jinja2_env.get_template("result.sh.j2").render(
        unit=unit,
        system_wide=system_wide,
        service_command=service_command,
        enable=enable,
        now=now,
        replace=replace,
    )

    copy(result)
    print(result)

    return service


@cli.command("del")
@click.argument("unit")
def tukx_del(unit):
    """
    Delete a systemd service file.
    """
    result = __jinja2_env.get_template("delete.sh.j2").render({
        "unit": unit,
        "os": os,
        "zip": zip
    })
    copy(result)
    print(result)
    return result


if __name__ == '__main__':
    cli()
