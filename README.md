# Jabberwocky Container Manager

Used for managing containers used with the [Jabberwocky project](https://github.com/Kippiii/Jabberwocky).

Here are some premade containers created for some Florida Tech classes [here](https://drive.google.com/drive/folders/1xRxzqJvm2w27yZCNgnlD7_iKxYhAQ6qB?usp=sharing)

## How to Build the Executable Files and Installer From Source

```sh
poetry install # Only do on first time

poetry shell
python build.py
```

Once the build has completed, the results will be stored in `build/dist`.

The installer file for the host platform will be stored at `build/dist/installer-[platform]-[architecture]`

There is no support for cross-compiling at this time.

## How to Run the Tool (For Developers)

```sh
poetry install # Only do first time

poetry shell
python download_prerequisites.py # Only do first time
python run.py
```
