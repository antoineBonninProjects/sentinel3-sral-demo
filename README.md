# Sentinel3-SRAL-Demo

### Project Overview

This project demonstrates how to download and store Sentinel-3 EUMETSAT products into a partitioned Zarr collection. Data is fetched via the [EUMDAC](https://anaconda.org/eumetsat/eumdac) library, and the code is heavily inspired by the EUMETSAT [learn-sral](https://gitlab.eumetsat.int/eumetlab/oceans/ocean-training/sensors/learn-sral) repository.

By default, data is downloaded from the EUMETSAT collection **ID(EO:EUM:DAT:0415): SRAL Level 2 Altimetry Global - Sentinel-3**, but this can be changed.

This collection contains files (products) from Sentinel-3A and 3B with Level 2 processed altimetry data. Each product includes three datasets:

- `reduced_measurement.nc` (1Hz)
- `standard_measurement.nc` (20Hz)
- `enhanced_measurement.nc` (20Hz + additional data)

For now, I only process the `reduced_measurement.nc` datasets from each product as I distribute code on a single computer.

The dataset represents Level 2 data derived from along-track SRAL altimeter measurements, which include:

- Sea Surface Height: `ssha_01_ku` and `ssha_01_plrm_ku`
- Wind Speed: `wind_speed_alt_01_ku` and `wind_speed_alt_01_plrm_ku`
- Significant Wave Height: `swh_ocean_01_ku` and `swh_ocean_01_plrm_ku`
- Geophysical Corrections: `iono_cor_alt_01_ku`, `iono_cor_alt_filtered_01_ku`, etc.
- And many other data points.

As these measurements are along-track, the only dimension is time: `time_01` (1Hz). The `lon_01` and `lat_01` coordinates are related to time as the satellite moves along its orbit.

### Objectives

The focus is on producing simple code that implements good practices for generic Python projects:

| Quality Focus Area     | Library or Tool      | Fail Under                |
|------------------------|----------------------|---------------------------|
| Test Driven Development | Pre-commit Hooks     | All hooks must pass       |
| Coverage               | pytest-cov           | 100% coverage             |
| Unit Tests             | pytest               | All tests OK              |
| Linter                 | pylint               | 100% score (default rules)|
| Formatter              | black                | Non-compliant formatting   |
| Static type checks     | mypy                 | NEVER FAILS : Not configured in pre-commit hooks   |

This project primarily serves as a means for me to discover new technologies, including:

- Zarr
- Zcollections
- Dask
- Xarray

Ultimately, it provides a practical overview of spatial altimetry datasets and helps me understand the data that can be derived from these spatial altimeters.

**Note**: In its current state, this project is far from production-ready:

- Not packaged or Dockerized
- Script is not structured as a job: no checkpointing to download only new files
- No CI/CD
- No monitoring
- No clustering or distributed storage
- No regression tests
- pytests are a bit limitted:
   - lack of edge case testing
   - lack of call parameters tests on methods and functions
   - but 100% code covering

## License

This code is licensed under the MIT License. See the `LICENSE.txt` file for details on usage and distribution terms.

## Authors

Antoine Bonnin

## Python Dependencies

This project relies on several key libraries for accessing and manipulating data. Below is a summary of the primary dependencies:

| Library      | Description                                                                                                                      | Documentation Link                                              |
|--------------|----------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| EUDMAC       | Provides simple access to EUMETSAT data from various satellite missions.                                                        | [EUDMAC](https://anaconda.org/eumetsat/eumdac)                |
| Xarray       | A comprehensive tool for working with labeled multi-dimensional data in Python.                                                | [Xarray](https://docs.xarray.dev/en/stable/)                  |
| Dask         | A Python library for parallel and distributed computing, which integrates well with Xarray and Zcollections.                    | [Dask](https://docs.dask.org/en/stable/)                      |
| Zarr         | A file storage format for chunked, compressed N-dimensional arrays based on an open-source specification.                        | [Zarr](https://zarr.readthedocs.io/en/stable/)                |
| Zcollections  | A Python library in the Pangeo ecosystem for manipulating data partitioned into collections of Zarr groups. Primarily used for writing partitioned data and querying with filters. | [Zcollections](https://zcollection.readthedocs.io/en/latest/api.html) |

## Prerequisites

### Optional Tools

**[RUNME](https://runme.dev/)**

A nice tool to render and execute shell commands from markdown in VSCode. You can install the [VSCode extension](https://docs.runme.dev/getting-started/vscode).

Here is the README without the VSCode extension:

![Without Runme](./ressources/img/without_runme.png)

The VSCode extension allows you to execute shell code directly from your markdown file:

![With Runme](./ressources/img/with_runme.png)

### Required Tools

**Python 3.12**

You can use [pyenv](https://github.com/pyenv/pyenv) to manage your Python versions by project.

```sh {"id":"01J8P8CJ70DD7FYZ7B2PTEH0H1"}
# Install python3.12-dev
pyenv install 3.12-dev
```

```sh {"id":"01J8P90EV8JAN2XHSNB3YKSQPK"}
# Set it as default python interpreter for the repo
pyenv local 3.12-dev
```

**[Conda](https://docs.anaconda.com/anaconda/install/index.html)**

Conda is needed to install some dependencies available only through conda channels. You can install [Miniconda](https://docs.anaconda.com/miniconda/) if you do not plan to use all of Anaconda's functionalities.

We use [libmamba](https://www.anaconda.com/blog/a-faster-conda-for-a-growing-community) solver to speed up dependency resolution.

```sh {"id":"01J8PCGEAAC83CN6JDQ7M79Q39"}
# Install libmamba solver
conda update -n base conda
conda install -n base conda-libmamba-solver
conda config --set solver libmamba
```

```sh {"id":"01J8PCRR9NS7NW97TNFKC2Q423"}
# Install project dependencies and setup 3.12 virtualenv
conda env create -f environment.yml --solver=libmamba
```

```sh {"id":"01J8PD7W29RA6FTWQFQ6ACNYRY"}
# Or update dependencies
conda env update --file environment.yml
```

```sh {"id":"01J8PCK4MF4GPRB83ECRK84VY3"}
# Use the project's virtualenv
conda activate sentinel3-sral-demo
```

```sh {"id":"01J8P9NSFP1JWKZXHZ0CDQD3H3"}
# (Optionnal) - setup precommit hooks (black, pylint, pytests)
pre-commit install
```

### Configuration requirements

#### EUMETSAT credentials file

First, create an account on [EUMETSAT eoportal](https://eoportal.eumetsat.int/cas/login)

Next, retrieve your credentials from [your Profile](https://api.eumetsat.int/api-key/). This is necessary for easy access to Sentinel-3 data.

Then, save your credentials to ~/.eumdac/credentials.ini:

```sh {"id":"01J8T3GWKJ78NSME8D352G5094"}
# Create your credentials file - Replace with your own credentials :)
mkdir -p ~/.eumdac
cat <<EOF > ~/.eumdac/credentials.ini
[myprofile]
consumer_key=my_key
consumer_secret=my_secret
EOF
```

#### Environment variables

| Variable Name           | Utility                                                   | Default Value                   |
|-------------------------|-----------------------------------------------------------|---------------------------------|
| `LOG_LEVEL`             | Defines the logging level for the task and its modules.   | `INFO`                          |
| `COLLECTION_ID`         | EUMDAC ID of the data collection being processed.          | `EO:EUM:DAT:0415`               |
| `DOWNLOAD_DIR`          | Directory where downloaded EUMDAC products are stored.     | `/tmp/products`                 |
| `MEASUREMENTS_FILENAME` | Filename for the reduced measurement data inside the EUMDAC products ZIP.                 | `reduced_measurement.nc`        |
| `ZARR_BASE_PATH`        | Path where the Zarr collection will be saved.              | `/tmp/sen3_sral`                |
| `INDEX_DIMENSION`       | Dimension to index the data for partitioning in Zarr.      | `time_01`                       |

```sh {"id":"01J91SMJW9PYFP2SAGYD38CPK2"}
# .envrc is not to be commited - in .gitignore
cp .envrc.tpl .envrc

# Edit variables in .envrc as you like
```

```sh {"id":"01J91SPEZF3S06DKMG6JFJN97C"}
# Load environment variables to your shell
source .envrc
```

Use **[direnv](https://direnv.net/)**:

- Loads environment variables declared in .envrc files when you cd into the directory containing the .envrc (or its subdirectories).
- Unloads environment variables when you cd out of that folder.

```sh {"id":"01J94H1KMMN5EGRVHW1DD5JBDJ"}
sudo apt install direnv

# Do not forget to configure the hook to your .bashrc
eval "$(direnv hook bash)" >> ~/.bashrc
source ~/.bashrc
direnv allow # In the folder containing .envrc, asked after each modification of .envrc

# or in zsh
eval "$(direnv hook zsh)" >> ~/.zshrc
source ~/.zshrc
direnv allow # In the folder containing .envrc, asked after each modification of .envrc

```

## Usage

### Execution

```sh {"id":"01J9200BMAX0X0ANYCCTW7AVC3"}
# In the conda environment, with dependencies installed
# And all prerequisites followed
python -m tasks.persist_sen3_sral_data_to_zarr
```

### Quality

Quality is ensured by pre-commit hooks (see the pre-commit-config.yaml file). However, each quality tool can also be run on demand:

```sh {"id":"01J9207TSCB7YRF3P2QB6G8FRE"}
# manual Pytests with coverage
python -m pytest tests --cov=. --cov-report=term-missing
```

```sh {"id":"01J9208TSEMJQ1269V8GY60YN1"}
# Linter
python -m pylint .
```

```sh {"id":"01J920BK7X9AHJC7A36D5JWP1Z"}
# Formatting
black .
```

```sh {"id":"01J928Y2ZZ4KYGTHW8MDDZSDVD"}
# Static type checks - not set as a pre-commit hooks
# 'PEP 484 prohibits implicit Optional' is annoying -> leads to very verbose code
python -m mymy .
```

### Code structure

The Python code is organized into:

- pipelines: A package to store tasks. Currently, it contains only one task.
- src: Custom code for our project, organized into packages by logical function.
- utils: Various generic tools, typically code that would be part of libraries installed via our conda channel or through git submodules.

## TODO

- Pass arguments to the script: date range for file fetching
- Package the code
- Build a Docker image of this project, even if it is not structured as a job in its current state
- Set up a local Kubernetes cluster (Minikube) and deploy:
   - A minimal Dask cluster: 1 master / 1 executor
   - A minimal distributed file system (NFS, OpenEBS, or Ceph): 1 node on local setup to store the Zarr collection