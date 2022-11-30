# Jabberwocky Container Manager

Used for managing containers used with the Jabberwocky project.

## How to Build the Executable Files and Installer

```sh
poetry install # Only do on first time

poetry shell
python build.py
```

Once the build has completed, the results will be stored in `build/dist`.

The installer file for the host platform will be stored at `build/dist/installer-[platform]-[architecture]`

There is no support for cross-compiling at this time.

## How to Run the Tool

```sh
poetry install # Only do on first time

poetry shell
python run.py
```
