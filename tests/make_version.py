# make_version.py
# Writes website/version.json with the commit hash so we know which release is live.

import json
import os
import subprocess

commit = os.environ.get("CODEBUILD_RESOLVED_SOURCE_VERSION")
if not commit:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()

json.dump({"release": commit}, open("website/version.json", "w"))
print("version.json ->", commit)
