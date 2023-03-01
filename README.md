# trackploy
Track and Deploy workflows and suites through git

**:warning:DISCLAIMER:warning:**:
This project is **BETA** and will be **Experimental** for the foreseeable future.
Interfaces and functionality are likely to change, and the project itself may be scrapped.
**DO NOT** use this software in any project/software that is operational.

## Overview
![](workflow.png)

## Installation
To install trackploy using pip (requires python, ecflow and pip):

    python -m pip install .

## Usage
To initialise the remote target git repository:
    
    usage: trackploy-init [-h] --target TARGET [--backup BACKUP] [--host HOST] [--user USER] [--force]

    Remote suite folder initialisation tool

    optional arguments:
    -h, --help       show this help message and exit
    --target TARGET  Target directory
    --backup BACKUP  Backup git repository
    --host HOST      Target host
    --user USER      Deploy user
    --force          Force push to remote

To stage and deploy a suite:
    
    usage: trackploy-deploy [-h] --stage STAGE --local LOCAL --target TARGET [--backup BACKUP] [--host HOST] [--user USER]
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
