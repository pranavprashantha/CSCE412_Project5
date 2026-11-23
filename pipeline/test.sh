#!/bin/bash
set -e

python3 tests/make_version.py
python3 tests/run_tests.py
