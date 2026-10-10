#!/usr/bin/env bash
# run_tests.sh — Run SURDAS test suite cleanly
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python3 -m pytest tests/ -v "$@"
