# Albert Launcher Firefox Extension
Opens *Firefox* bookmarks.

## Install
To install, copy or symlink this directory to `~/.local/share/albert/python/plugins/firefox/`.

## Config
Config is stored in `~/.config/albert/python.firefox/settings.json`.

Example config:

```json
{
  "profileName": "a1b2c3d4.default"
}
```

## Development Setup
To setup the project for development, run:

    $ cd firefox/
    $ pre-commit install --hook-type pre-commit --hook-type commit-msg

To lint and format files, run:

    $ pre-commit run --all-files
