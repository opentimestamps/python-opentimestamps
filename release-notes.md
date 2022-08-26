# python-opentimestamps release notes

## v0.4.2

* Latest python-bitcoinlib marked as compatible; no other changes.

## v0.4.1

* Latest python-bitcoinlib marked as compatible; no other changes.


## v0.4.0

* Breaking change: Timestamp equality comparison now also checks attestations,
  not just operations.
* Fixed issues with timestamp less than/greater than comparisons, (e.g. `ts1 < ts2`)
* Fixed `str_tree()` crash


## v0.3.0

* New calendar server! Thanks to Vincent Cloutier from Catallaxy.
* URL handling in calendar code now handles tailing slashes.
* New attestation: `LitecoinBlockHeaderAttestation`.


## v0.2.1

Fixed `make_timestamp_from_block()` w/ blocks containing segwit transactions.


## v0.2.0.1

Actually get that right...


## v0.2.0

`python-bitcoinlib` version required bumped to 0.9.0 for segwit compatibility.


## v0.1.0

Initial release.
