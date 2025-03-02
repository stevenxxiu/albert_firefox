# Albert Launcher Firefox Extension
Opens *Firefox* bookmarks.

## Install
To install, copy or symlink this directory to `~/.local/share/albert/python/plugins/firefox/`.

## Config
Config is stored in `~/.config/albert/python.firefox/settings.json`.

Config is optional. Without config, we look for a profile in order of:

- The last used default profile.
- The dev profile.

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
    $ mkdir stubs/
    $ ln --symbolic ~/.local/share/albert/python/plugins/albert.pyi stubs/

To lint and format files, run:

    $ pre-commit run --all-files
