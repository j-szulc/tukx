import logging
import sys
import uuid
import os
import shlex
import shutil
import pathlib
import jinja2

import click

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

__templates = {
    "permanent": "permanent.service.j2",
    "inline-file": "inline-file.sh.j2",
}


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )


def get_cmd_list(command, shell=False):
    command = [line.strip() for line in command.splitlines() if line.strip()]
    if not command:
        return []
    if shell:
        return ["sh", "-c", " ; ".join(command)]
    if len(command) != 1:
        raise click.ClickException("Only one command can be specified when shell is disabled.")
    return shlex.split(command[0])


def fix_exec_path(cmd_list):
    if not cmd_list:
        return []
    if shutil.which(cmd_list[0]) is None:
        raise click.ClickException("Command '{}' not found in PATH".format(cmd_list[0]))
    cmd_list[0] = shutil.which(cmd_list[0])
    return cmd_list


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
    return __jinja2_env.get_template(__templates["inline-file"]).render(dst_path=dst_path, src_content=src_content, EOF=EOF, sudo=sudo)

@click.command()
@click.option("--verbose", is_flag=True, help="Enables verbose mode.")
@click.option("--description", default=None)
@click.option("--unit", default=None, help="Name of the service (Default: random)")
@click.option("--user", help="Run service as user (Default: current user)")
@click.option("--group", help="Run service as group (Default: current user's group)")
@click.option("--restart", default="no", show_default=True, help="Restart policy")
@click.option("--working-directory", default=None, help="Working directory (Default: current directory)")
@click.option("--environment", "-E", default=[], multiple=True, help="Environment variables", metavar="NAME=VALUE")
@click.option("--system-wide/--user-wide", default=True, show_default=True, help="Install service system-wide or user-wide")
@click.option("--shell", is_flag=True,  help="Run the command in a shell.")
@click.option("--install/--dont-install", default=True, show_default=True, help="Install the service")
@click.argument("command", nargs=-1)
def main(verbose, description, unit, user, group, restart, working_directory, environment, system_wide, shell, install, command):
    """
    tukx - Run commands as systemd services

    COMMAND - Command to run as a service.
              If not specified, the command will be read from stdin.
              Press Ctrl+D to finish input.
    """
    print(str(pathlib.Path(__file__).parent / "templates"))
    unit="tukx-{}".format(uuid.uuid4()) if unit is None else unit
    if verbose:
        setup_logging(logging.DEBUG)
    working_directory = working_directory if working_directory is not None else "."
    working_directory = os.path.abspath(working_directory)
    if not os.path.isdir(working_directory):
        raise click.ClickException("Working directory '{}' does not exist".format(working_directory))
    if user is None:
        user = os.getlogin()
    if group is None:
        group = user
    environment = fix_envlist(environment)
    if not command:
        print("Enter command to run as a service. Press Ctrl+D to finish input.", file=sys.stderr)
        command = sys.stdin.read()
    if isinstance(command, tuple):
        command = " ".join(command)
    command = shlex.join(fix_exec_path(get_cmd_list(command, shell)))
    if not command:
        raise click.ClickException("No command specified")

    kwargs = {
        "description": description,
        "unit": unit,
        "user": user,
        "group": group,
        "working_directory": working_directory,
        "environment": environment,
        "command": command,
        "restart": restart,
        "install": install,
    }
    service = __jinja2_env.get_template(__templates["permanent"]).render(**kwargs)
    target_folder = "/etc/systemd/system" if system_wide else "/etc/systemd/user"
    target_path = os.path.join(target_folder, "{}.service".format(unit))

    cmd = inline_file(service, target_path, sudo=True)
    print(cmd)
    return service







if __name__ == '__main__':
    main()
