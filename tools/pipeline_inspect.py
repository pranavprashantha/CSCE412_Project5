"""pipeline_inspect.py - read-only look at the CI/CD pipeline.

Used by the Deployer (pipeline config) and the Incident Manager (failed runs).
Nothing here changes AWS.

Usage:
    python3 tools/pipeline_inspect.py config
    python3 tools/pipeline_inspect.py last-failure
    python3 tools/pipeline_inspect.py known-good
"""
import json
import sys

from common import aws, settings


def pipeline_config():
    # the stages and actions of the pipeline, in order
    ok, out = aws("codepipeline", "get-pipeline", "--name", settings()["pipeline"])
    if not ok:
        return {"error": out}
    pipeline = json.loads(out)["pipeline"]
    stages = []
    for stage in pipeline["stages"]:
        for action in stage["actions"]:
            config = action.get("configuration", {})
            stages.append({
                "stage": stage["name"],
                "action": action["name"],
                "provider": action["actionTypeId"]["provider"],
                "inputs": [a["name"] for a in action.get("inputArtifacts", [])],
                "outputs": [a["name"] for a in action.get("outputArtifacts", [])],
                "branch": config.get("BranchName", ""),
                "env_vars": config.get("EnvironmentVariables", ""),
            })
    return {"pipeline": pipeline["name"], "stages": stages}


def build_log(build_id, lines=60):
    # the last lines of a CodeBuild log
    ok, out = aws("codebuild", "batch-get-builds", "--ids", build_id)
    if not ok:
        return [out]
    logs = json.loads(out)["builds"][0]["logs"]
    ok, out = aws("logs", "get-log-events", "--log-group-name", logs["groupName"],
                  "--log-stream-name", logs["streamName"], "--limit", str(lines))
    if not ok:
        return [out]
    return [event["message"].rstrip() for event in json.loads(out)["events"]]


def last_failure():
    # find the newest failed run, which action failed, and its log
    name = settings()["pipeline"]
    ok, out = aws("codepipeline", "list-pipeline-executions", "--pipeline-name", name, "--max-items", "10")
    if not ok:
        return {"error": out}
    failed_run = None
    for run in json.loads(out)["pipelineExecutionSummaries"]:
        if run["status"] == "Failed":
            failed_run = run
            break
    if failed_run is None:
        return {"found": False, "message": "no failed runs in the last 10"}

    commit = ""
    message = ""
    if failed_run.get("sourceRevisions"):
        commit = failed_run["sourceRevisions"][0].get("revisionId", "")
        message = failed_run["sourceRevisions"][0].get("revisionSummary", "")

    ok, out = aws("codepipeline", "list-action-executions", "--pipeline-name", name,
                  "--filter", "pipelineExecutionId=" + failed_run["pipelineExecutionId"])
    actions = json.loads(out)["actionExecutionDetails"] if ok else []
    failed_action = None
    for action in actions:
        if action["status"] == "Failed":
            failed_action = action
            break
    if failed_action is None:
        return {"found": True, "commit": commit, "error": "could not find the failed action"}

    build_id = failed_action.get("output", {}).get("executionResult", {}).get("externalExecutionId", "")
    return {
        "found": True,
        "execution_id": failed_run["pipelineExecutionId"],
        "commit": commit,
        "commit_message": message,
        "failed_stage": failed_action["stageName"],
        "summary": failed_action.get("output", {}).get("executionResult", {}).get("externalExecutionSummary", ""),
        "log_tail": build_log(build_id) if build_id else [],
    }


def known_good():
    # the last release that passed, and the saved releases
    bucket = settings()["release_bucket"]
    ok, out = aws("s3", "cp", "s3://" + bucket + "/known-good.txt", "-")
    good = out.strip() if ok else "none saved yet"
    ok, out = aws("s3", "ls", "s3://" + bucket + "/releases/")
    releases = []
    if ok:
        for line in out.splitlines():
            releases.append(line.replace("PRE", "").strip().strip("/"))
    return {"known_good": good, "saved_releases": releases}


if __name__ == "__main__":
    commands = {"config": pipeline_config, "last-failure": last_failure, "known-good": known_good}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        print("usage: python3 tools/pipeline_inspect.py config|last-failure|known-good")
        sys.exit(1)
    print(json.dumps(commands[sys.argv[1]](), indent=2))