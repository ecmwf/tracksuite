<p align="center">
  <picture>
    <img src="tracksuite.png" height="360">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/ecmwf/codex/raw/refs/heads/main/ESEE">
    <img src="https://github.com/ecmwf/codex/raw/refs/heads/main/ESEE/production_chain_badge.svg" alt="ECMWF Software EnginE">
  </a>
  <a href="https://github.com/ecmwf/codex/raw/refs/heads/main/Project Maturity">
    <img src="https://github.com/ecmwf/codex/raw/refs/heads/main/Project Maturity/incubating_badge.svg" alt="Maturity Level">
  </a>
  <a href="https://opensource.org/licenses/apache-2-0">
    <img src="https://img.shields.io/badge/Licence-Apache 2.0-blue.svg" alt="Licence">
  </a>
  <a href="https://github.com/ecmwf/tracksuite/releases">
    <img src="https://img.shields.io/github/v/release/ecmwf/tracksuite?color=purple&label=Release" alt="Latest Release">
  </a>
</p>

<p align="center">
  <!-- <a href="#quick-start">Quick Start</a>
  • -->
  <a href="#installation">Installation</a>
  •
  <a href="#documentation">Documentation</a>
  •
  <a href="#Overview">Overview</a>
</p>

> \[!IMPORTANT\]
> This software is **Incubating** and subject to ECMWF's guidelines on [Software Maturity](https://github.com/ecmwf/codex/raw/refs/heads/main/Project%20Maturity).

**Tracksuite** offers command-line tools and a Python API to allow users to track and deploy ecFlow suites through git.

## Installation
To install tracksuite using pip (requires python, ecFlow (optional) and pip):

    python -m pip install .

## Documentation
**To initialise the remote target git repository:**
    
    usage: tracksuite-init [-h] --target TARGET [--backup BACKUP] [--host HOST] [--user USER] [--force]

    Remote suite folder initialisation tool

    optional arguments:
    -h, --help       show this help message and exit
    --target TARGET  Target directory
    --backup BACKUP  Backup git repository
    --host HOST      Target host
    --user USER      Deploy user
    --force          Force push to remote

**To stage and deploy a suite:**
    
    usage: tracksuite-deploy [-h] --stage STAGE --local LOCAL --target TARGET [--backup BACKUP] [--host HOST] [--user USER]
                        [--push] [--message MESSAGE]

    Suite deployment tool

    optional arguments:
    -h, --help         show this help message and exit
    --stage STAGE      Staged suite
    --local LOCAL      Path to local git repository (will be created if doesn't exist)
    --target TARGET    Path to target git repository on host
    --backup BACKUP    URL to backup git repository
    --host HOST        Target host
    --user USER        Deploy user
    --push             Push staged suite to target
    --message MESSAGE  Git message

**To revert the suite to a previous state:**

    usage: tracksuite-revert [-h] [--host HOST] [--user USER] [--message MESSAGE] [--backup BACKUP] [--no_prompt] target n_state

    Revert a git repository to a previous state.

    positional arguments:
    target             Path to target git repository on host
    n_state            Number of states to revert back

    options:
    -h, --help         show this help message and exit
    --host HOST        Target host
    --user USER        Deploy user
    --message MESSAGE  Git message
    --backup BACKUP    URL to backup git repository
    --no_prompt        No prompt, --force will go through without user input

**To update the suite definition in the target git repository from the suite running on the ecFlow server (requires ecFlow):**

    usage: tracksuite-update-defs [-h] [--definition DEFINITION] --target TARGET --local LOCAL --backup BACKUP [--host HOST] [--user USER] [--port PORT] name

    Update suite definition on target from ecflow server

    positional arguments:
    name                  Ecflow suite name

    options:
    -h, --help            show this help message and exit
    --definition DEFINITION
                            Name of the definition file to update
    --target TARGET       Path to target git repository on host
    --local LOCAL         Path to local git repository. DEFAULT: $TMP
    --backup BACKUP       URL to backup git repository
    --host HOST           Target host
    --user USER           Deploy user
    --port PORT           Ecflow port

**To replace an ecFlow suite on an ecFlow server while preserving some attributes from the already deployed suite:**

    usage: tracksuite-replace [-h] --def-file DEF_FILE [--host HOST] [--port PORT] [--enable-ssl] [--node NODE] [--sync-variables] [--skip-status] [--skip-attributes] [--skip-repeat] name

    Replace suite on server and keep some attributes from the old one

    positional arguments:
    name                 Ecflow suite name

    options:
    -h, --help           show this help message and exit
    --def-file DEF_FILE  Name of the definition file to update
    --host HOST          Target host
    --port PORT          Ecflow port
    --enable-ssl         Enable SSL connection
    --node NODE          Path to the node to replace
    --sync-variables     Synchronise variables
    --skip-status        Don't synchronise status
    --skip-attributes    Don't synchronise attributes
    --skip-repeat        Don't synchronise repeat

## Overview
![](workflow.png)