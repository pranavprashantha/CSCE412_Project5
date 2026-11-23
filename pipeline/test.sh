#!/bin/bash
# Stage 2: Test
# Stamps the release with its commit, then runs the tests.
# If a test fails, this exits with an error and the pipeline stops before deploy.
set -e

python3 tests/make_version.py
python3 tests/run_tests.py
