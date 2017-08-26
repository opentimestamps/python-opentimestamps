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
