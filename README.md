# sentinel3-sral-demo

This code aims at demonstrating how to make basic manipulations over Sentinel3 satellite Altimeter data (SRAL).

It uses [EUDMAC](https://anaconda.org/eumetsat/eumdac) library to fetch Sentinel3 data.

This code is highly inspired by EUMETSAT [learn-sral](https://gitlab.eumetsat.int/eumetlab/oceans/ocean-training/sensors/learn-sral) repo.

## License

This code is licensed under an MIT license. See file LICENSE.txt for details on the usage and distribution terms.

## Authors

Antoine Bonnin

## Prerequisites

### Optionnal tools

**[RUNME](https://runme.dev/)**

Nice tool to render and execute shell commands from markdown in VSCode. Install the [VSCode extension](https://docs.runme.dev/getting-started/vscode).

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
# (Optionnal) - setup precommit hooks (black, pylint)
pre-commit install
```

### Configuration requirements

**EUMETSAT credentials file**

First you need to create an account on [EUMETSAT eoportal](https://eoportal.eumetsat.int/cas/login)

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
