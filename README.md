# CSCE 412 Project 5: Multi-Agent Website Deployment

Live site: https://csce412prra2413.me

## Overview

This project hosts a static website (Fieldline Run Club) on AWS. It also includes a set of AI agents that edit, deploy and check the site.

**AWS setup**
- **S3** stores the site files. The bucket is private.
- **CloudFront** serves the site over HTTPS. It is the only thing allowed to read the bucket (Origin Access Control).
- **ACM** provides the SSL certificate.
- **Route 53** points the domain at CloudFront.
- **Namecheap** is the registrar. It uses the Route 53 nameservers.

**Agent setup**
`orchestrator.py` passes messages between four agents. Each agent uses Gemini to make decisions and can only call the tools it is allowed to use. Every message, decision and tool call is written to a log in `logs/`.

## Agents

| Agent | What it does | Tools |
|---|---|---|
| Planner | Breaks a goal into tasks | none |
| Developer | Edits the website files | list/read/write files in `website/` |
| Deployer | Uploads the site and applies fixes | `deploy.sh` (dry run and deploy), `apply_fix.py` |
| Security/Validator | Checks the live site and finds what's wrong | `verify.py`, `aws_inspect.py` |

**Needs a human `yes` before running**
- Any fix to AWS (bucket policy or CloudFront settings)
- Any deploy that would delete files from S3

## Requirements

- Python 3.10 or newer
- AWS CLI v2
- A Gemini API key

## Install

```bash
git clone https://github.com/pranavprashantha/CSCE412_Project5.git
cd CSCE412_Project5
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

1. Copy the example env file and fill in your key:

```bash
cp .env.example .env
```

```
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-3.5-flash-lite
```

2. Set up an AWS CLI profile named `project5` with an IAM user's access keys:

```bash
aws configure --profile project5
```

Use region `us-east-1`.

3. Check `config/settings.json`. It holds the domain, bucket name, CloudFront distribution ID and AWS profile name.

`.env` and `logs/` are in `.gitignore`, so keys never get committed.

## Running

Check the live site. If something is broken, the agents try to fix it:

```bash
python3 orchestrator.py --verify-only
```

Give the agents a goal:

```bash
python3 orchestrator.py --goal "Add a December trail run to the events page"
```

Run only the checks, with no agents:

```bash
python3 tools/verify.py
```

## Reproducing a Workflow

**Normal run**
1. Run the `--goal` command above.
2. The Planner makes the tasks. The Developer edits `website/events.html`.
3. The Deployer does a dry run, then deploys and clears the CloudFront cache.
4. The Validator runs the 7 checks and reports healthy.

**Failure and recovery**
1. Break the site by deleting the bucket policy:
   ```bash
   aws s3api delete-bucket-policy --bucket csce412-prra2413-site --profile project5
   ```
2. Clear the cache so the error shows up:
   ```bash
   aws cloudfront create-invalidation --distribution-id E2XE8SGMTOFJIB --paths "/*" --profile project5
   ```
3. Run `python3 orchestrator.py --verify-only`.
4. The Validator sees failed checks and suggests `restore_bucket_policy`.
5. Type `yes` to approve. The Deployer restores the policy, and the Validator re-checks until the site is healthy.

Logs from my own runs are in `evidence/`.
