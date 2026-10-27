# python-opentimestamps release notes

## v0.5.0

### Security Related Changes

* Redirects from remote calendars are now only followed to the same host, with
  http or https. Previously any redirect was followed, even to non-http
  protocols such as `file:`.
* URL whitelist handling fixed; previously the whitelist could be bypassed.
* Repeated ops after a fork are no longer silently ignored, and will now raise
  a `DeserializationError`.
* Variable int lengths are now bounded to 63 bits, and block heights are
  bounded to 32 bits. Otherwise `DeserializationError` was raised.

### Other Changes

* Python 3.11 or later is now required.
* Oversized responses from remote calendars now raise a specific error rather
  than being silently truncated.
* RIPEMD160 now works on recent Python versions that left it out.
* Using KECCAK256 as a file hash op now raises a proper error message.
* Removed incomplete `TimestampLog` feature.

## v0.4.5

* Fix broken upload on pypi

## v0.4.4

* Update requirements to mark python-bitcoinlib v0.12.x as compatible.

v0.12.x has breaking changes. But they don't affect us.

## v0.4.3

* Replaced pysha3 dependency with pycryptodomex. The former was not compatible
  with Python 3.11

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
