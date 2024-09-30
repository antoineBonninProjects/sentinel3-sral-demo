# sentinel3-sral-demo

### Project overview

This project aims at demonstrating how to download and store Sentinel3 EUMETSAT products to a partitionned Zarr collection. The data is fetched via [EUDMAC](https://anaconda.org/eumetsat/eumdac) library and this code is highly inspired by EUMETSAT [learn-sral](https://gitlab.eumetsat.int/eumetlab/oceans/ocean-training/sensors/learn-sral) repo.

Data is downloaded from EUMETSAT collection *ID(EO:EUM:DAT:0415): SRAL Level 2 Altimetry Global - Sentinel-3*.

This collection contains files (products) of Sentinel-3A and 3B of Level2 processed altimetry Data. Each product contains 3 datasets: reduced_measurement.nc (1Hz), standard_measurement.nc (20hz) and enhanced_measurement.nc (20Hz + additional data) NetCDF datasets.

Because I distribute code on a single computer for now, I only process _reduced_measurement.nc_ datasets of each product.

The dataset represents Level2 data derived from along track SRAL altimeter:

* Sea surface height: _ssha_01_ku_ and _ssha_01_plrm_ku_
* Wind speed: _wind_speed_alt_01_ku_ and _wind_speed_alt_01_plrm_ku_
* Significant wave height: _swh_ocean_01_ku_ and _swh_ocean_01_plrm_ku_
* Geophysical corrections: _iono_cor_alt_01_ku_ / _iono_cor_alt_filtered_01_ku_ / ...
* and many other data

Because it is along track measurements, the only dimension is time: _time_01_ (1Hz).
_lon_01_ and _lat_01_ coordinates are related to time, as the satellites moves along its orbit.

### Objectives

I focused on producing a simple code, where I try to implement generic python project good practices:

| Quality Focus Area     | Lib or Tool      | Fail_Under                |
|------------------------|------------------|---------------------------|
| Test Driven Development | pre-commit hooks | All hooks must pass        |
| Coverage               | pytest-cov       | 100% coverage              |
| Unit Tests             | pytest           | All tests OK               |
| Linter                 | pylint           | 100% score (default rules) |
| Formatter              | black            | Non-compliant formatting (default rules)  |

This is primarly a way for me to discover new technos:

* zarr
* zcollections
* dask
* xarray

Finally it allows me to have a practical overview of spatial altimetry datasets, and to understand what data can be derived from these spatial altimeters.

**Note**: in its current state, it is far from production ready:

* not packaged or Dockerized
* script is not really a job: no checkpointing
* no CICD
* no monitoring
* no clustering / no distributed storage

## Python dependencies

This project relies on several key libraries to provide functionality for accessing and manipulating data. Below is a summary of the primary dependencies:

| Library      | Description                                                                                                                                          | Documentation Link                                              |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| EUDMAC       | Provides simple access to EUMETSAT data from a variety of satellite missions.                                                                     | [EUDMAC](https://anaconda.org/eumetsat/eumdac)                |
| Xarray       | A comprehensive tool for working with labeled multi-dimensional data in Python.                                                                   | [Xarray](https://docs.xarray.dev/en/stable/)                  |
| Dask         | A Python library for parallel and distributed computing. It integrates well with Xarray and zcollections.                                          | [Dask](https://docs.dask.org/en/stable/)                      |
| Zarr         | A file storage format for chunked, compressed, N-dimensional arrays based on an open-source specification.                                         | [Zarr](https://zarr.readthedocs.io/en/stable/)                |
| Zcollections  | A Python library in the Pangeo ecosystem for manipulating data partitioned into collections of Zarr groups. Primarily used for writing partitioned data and querying easily with filters. | [Zcollections](https://zcollection.readthedocs.io/en/latest/api.html) |

## License

This code is licensed under an MIT license. See file LICENSE.txt for details on the usage and distribution terms.

## Authors

Antoine Bonnin

## Prerequisites

### Optionnal tools

**[RUNME](https://runme.dev/)**

Nice tool to render and execute shell commands from markdown in VSCode. Install the [VSCode extension](https://docs.runme.dev/getting-started/vscode).

Here is the readme without the VSCode extension:

<img src="./ressources/img/without_runme.png" alt="without runme" style="width:80%"/>

The VSCode extension allows you to execute shell code from your .md file:

<img src="./ressources/img/with_runme.png" alt="with runme" style="width:80%"/>

### Required tools

**python3.12**

You can use [pyenv](https://github.com/pyenv/pyenv) to manage your python versions by project.

```sh {"id":"01J8P8CJ70DD7FYZ7B2PTEH0H1"}
# Install python3.12-dev
pyenv install 3.12-dev
```

```sh {"id":"01J8P90EV8JAN2XHSNB3YKSQPK"}
# Set it as default python interpreter for the repo
pyenv local 3.12-dev
```

**[Conda](https://docs.anaconda.com/anaconda/install/index.html)**

We need conda to install some dependencies that are only available via conda channels. You can install [Miniconda](https://docs.anaconda.com/miniconda/) if you do not plan to use all anaconda functionnalities.

We use [libmamba](https://www.anaconda.com/blog/a-faster-conda-for-a-growing-community) solver to speed up dependencies solving.

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

**EUMETSAT credentials file**

First you need to create an account on [EUMETSAT eoportal](https://eoportal.eumetsat.int/cas/login)

Then, get your credentials from [your Profile](https://api.eumetsat.int/api-key/)

This is required to have an easy access to Sentinel3 data.

Then save your credentials to `~/.eumdac/credentials.ini`

```sh {"id":"01J8T3GWKJ78NSME8D352G5094"}
# Create your credentials file - Replace with your own credentials :)
mkdir -p ~/.eumdac
cat <<EOF > ~/.eumdac/credentials.ini
[myprofile]
consumer_key=my_key
consumer_secret=my_secret
EOF
```

**Environment variables**

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

- loads environment variables declared in .envrc files when you enter `cd` the directory containing the .envrc (or its sub directories)
- unloads environment variables when you `cd` out of this folder

## Usage

### Execution

```sh {"id":"01J9200BMAX0X0ANYCCTW7AVC3"}
# In the conda environment, with dependencies installed
# And all prerequisites followed
python -m pipelines.load_sen3_sral_data_to_zarr
```

### Quality

Quality is ensured by pre-commit hooks (see file *pre-commit-config.yaml*). But each quality tool can also be run on demand.

```sh {"id":"01J9207TSCB7YRF3P2QB6G8FRE"}
# manual Pytests with coverage
python -m pytest tests --cov=. --cov-report=term-missing
```

```sh {"id":"01J9208TSEMJQ1269V8GY60YN1"}
# Linter
pylint .
```

```sh {"id":"01J920BK7X9AHJC7A36D5JWP1Z"}
# Formatting
black .
```

#### Code structure

The python code is splitted in:

* **pipelines**: package to store tasks. For now there is only one task.
* **src**: custom code for our project. Splitted in packages, by logical function.
* **utils**: various generic tools. Typically code that would be part of libraries that we install via our conda channel or via git submodules.

## TODO

* pass arguments to the script: date range for files fetching
* set constants via env variables instead of in code
* package the code
* build a docker image of this project, even if it not really a job in its current state
* setup a local kubernetes cluster (minikube) and spawn:
   * a minimal dask cluster: 1 master / 1 executor
   * a minimal distributed file system (NFS, OpenEBS, or Cephi): 1 node on local setup to store the zarr collection
