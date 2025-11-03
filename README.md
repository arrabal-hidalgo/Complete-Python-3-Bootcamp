# Segittur Commons

## Installation with Docker (Recommended)

### Dependencies

Segittur Commons project development environment is dockerized, so you need to install `docker` and `docker compose` if you want run the project throught containers. To know how to open project throught DevContainer see [DevContainer section](#open-in-devcontainer).

### Install

1.- Copy `.env.template` into `.devcontainer` as `.env` and set the variable properly according to environment.
```bash
cp .env.template .devcontainer/.env
```
2.- Go to `.devcontainer`.
```bash
cd .devcontainer
```
3.- Build the images.
```bash
docker compose build
```
4.- Run the whole project.
```bash
docker compose up -d
```

### Open in devContainer

To open the project in **devContainer**, please execute the following steps:

1. Add `.env` file into the `.devcontainer` folder.
2. Click in the lower left corner blue button **(><)** and then click in *Reopen in Container*.

## Build project as PyPI package

https://gitlab.sngular.com/help/user/packages/workflows/build_packages.md#create-a-pypi-package

0. Change version to development version in `pyproject.toml`.
For example, if **version=1.0.0** and **dev_version=3**:
```
[project]
name = "segittur-commons"
version = "1.0.0-rc3"
```

1. Install the package *build* library:
```bash
pip install build
```

2. Build the package:
```bash
python -m build
```

3. The output should be visible in a newly-created dist folder:
```bash
ls dist/*-1.0.0rc3*
```
```bash
segittur_commons-1.0.0rc3-py3-none-any.whl segittur_commons-1.0.0rc3.tar.gz
```

## Publish PyPI package to the package registry

https://gitlab.sngular.com/help/user/packages/pypi_repository/index.md

1. Create a [**personal access token**](https://gitlab.sngular.com/-/user_settings/personal_access_tokens) in GitLab with the scope set to **api**.

2. Make a copy of the `.pypirc_template` and rename it as `.pypirc`. Then fill the *password* with your *personal access token*.

3. Install the package *twine* library:
```bash
pip install twine
```

4. Upload your package with twine:
```bash
python3 -m twine upload --repository gitlab --config-file .pypirc dist/*-1.0.0rc3*
```
When a package is published successfully, a message like this is displayed:
```bash
Uploading distributions to https://gitlab.sngular.com/api/v4/projects/7537/packages/pypi
Uploading segittur_commons-<version>-py3-none-any.whl
100%|███████████████████████████████████████████████████████████████████████████████████████████| 4.58k/4.58k [00:00<00:00, 10.9kB/s]
Uploading segittur_commons-<version>.tar.gz
100%|███████████████████████████████████████████████████████████████████████████████████████████| 4.24k/4.24k [00:00<00:00, 11.0kB/s]
```
The package is published to the package registry, and is shown on the [**Packages and registries**](https://gitlab.sngular.com/SngularData/asistentes/segittur/segittur-commons/-/packages) page.