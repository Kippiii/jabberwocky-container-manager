# Jabberwocky Container Manager

This project is used for managing the containers related to the Jabberwocky Container Manager project.

## How to Use

```sh
poetry install # Only do on first time

poetry shell
poetry run python run.py
```

To run the local server independently 

```sh
poetry run python server.py
```

## Building
```sh
poetry run python build.py
```

The installer for your platform will be stored at `./build/dist/installer.exe`.

Or use the compiled binary files directly with

```sh
./build/dist/jab/jab
./build/dist/server/server
```

There is no support for cross-compiling at this time.

## After installation
```sh
jab help # View the help page
```
