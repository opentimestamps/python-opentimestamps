# python-opentimestamps

Python3 library for creating and verifying OpenTimestamps proofs.

## Installation

From the PyPi repository:

    pip3 install opentimestamps

## Structure

Similar to the author's `python-bitcoinlib`, the codebase is split between the
consensus-critical `opentimestamps.core.*` modules, and the
non-consensus-critical `opentimestamps.*` modules. The distinction between the
two is whether or not changes to that code are likely to lead to permanent
incompatibilities between versions that could lead to timestamp validation
returning inconsistent results between versions.

## Unit tests

    python3 -m unittest discover -v

Additionally Travis is supported.

## SSL Root Certificates

On some MacOS setups SSL certificates may be missing. The following commands
could be of use to resolve this error (the below example assumes a user is
running Python "3.7", and is using Certifi package):

```
cd /Applications/Python\ 3.7
Install\ Certificates.command
```

