#!/bin/bash
# Start Dramatiq workers for breaking-law platform
# Requires: Redis running, Python venv activated

dramatiq breaking_law.documents.worker_parse &
dramatiq breaking_law.documents.worker_export &
dramatiq breaking_law.timekeeping.worker_deadline &
dramatiq breaking_law.retention.worker &
wait
