# Tukx
Run commands as systemd services.

## Installation

```
git clone git@github.com:j-szulc/tukx.git && \
cd tukx && \
pip install .
```

## Usage

```
$ tukx --help
Usage: tukx [OPTIONS] [COMMAND]...

  tukx - Run commands as systemd services. If not specified, the command will
  be read from stdin. Press Ctrl+D to finish input.

Options:
  --verbose                     Enables verbose mode.
  --remote                      Allows specifying paths, users, groups not
                                existent on this device.
  --remote-root                 Shortcut for --remote --working-directory
                                /root --user root --group root
  --description TEXT
  --unit TEXT                   Name of the service [default: random]
  --user TEXT                   Run service as user [default: current user]
  --group TEXT                  Run service as group [default: equal to
                                --user]
  --restart TEXT                Restart policy  [default: no]
  --working-directory TEXT      Working directory [default: current directory
                                or home if --remote]
  -E, --environment NAME=VALUE  Environment variables
  --system-wide / --user-wide   Install service system-wide or user-wide
                                [default: system-wide]
  --shell                       Run the command in a shell.
  --install / --dont-install    Install the service  [default: install]
  --enable                      Add a command to enable the service
  --now                         Add a command to start the service and view
                                status
  --help                        Show this message and exit.
```

## Examples

```
$ tukx --working-directory ~ -- echo hello world
sudo tee <<EOF /etc/systemd/system/tukx-c8114a94-3442-4e60-af2c-c081ec5e7c63.service >/dev/null

[Service]
Type=simple
ExecStart=/bin/echo hello world
User=root
Group=root
Restart=no
WorkingDirectory=/home/username

[Install]
WantedBy=multi-user.target

EOF
sudo systemctl enable --now tukx-c8114a94-3442-4e60-af2c-c081ec5e7c63
sudo systemctl status --lines=0 tukx-c8114a94-3442-4e60-af2c-c081ec5e7c63
journalctl -u tukx-c8114a94-3442-4e60-af2c-c081ec5e7c63 -f
```
```
$ tukx --shell --working-directory ~                                                                                               1 ✘  7s  
>>> Enter command to run as a service. Press Ctrl+D to finish input.
>>> echo hello
>>> echo world
sudo tee <<EOF /etc/systemd/system/tukx-84311689-623b-4ee1-9b7f-b56fa8ac9706.service >/dev/null

[Service]
Type=simple
ExecStart=/bin/sh -c 'echo hello ; echo world'
User=root
Group=root
Restart=no
WorkingDirectory=/home/username

[Install]
WantedBy=multi-user.target

EOF
```