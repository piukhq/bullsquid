![project logo](docs/bullsquid.png)

# bullsquid

Portal API backend project.

# Prerequisites

Ensure Poetry 1.2+ is installed:

```
❯ poetry --version
Poetry (version 1.2.0)
```

Ensure `psql` is installed:

```
❯ psql --version
psql (PostgreSQL) 14.2
```

`psql` version does not matter as long as it's relatively recent.

## Setup

The bootstrap script will do most of the work setting up the project.

```
❯ scripts/bootstrap
```

The script will install dependencies and attempt to set up the database.
If you don't have a PostgreSQL instance running on the default port, then the
script will attempt to set one up for you with Docker. If you don't have Docker,
this stage will fail and you will need to either set up PostgreSQL manually or
install docker. Once you have done that, re-run the bootstrap script.

## Running the API server

```
❯ poetry run scripts/server
```

### Running tests

```
❯ poetry run scripts/test
```
