# Claude Code on Amazon Bedrock — Team Setup Guide

One-command setup scripts for macOS and Windows that handle everything:
1. Create an AWS profile via **isengardcli**
2. Set all Bedrock environment variables persistently
3. Install Claude Code if needed
4. Launch Claude Code

---

## Prerequisites

| Requirement | macOS | Windows |
|---|---|---|
| Node.js 18+ | `brew install node` | [nodejs.org](https://nodejs.org/) |
| AWS CLI | `brew install awscli` | [aws.amazon.com/cli](https://aws.amazon.com/cli/) |
| ada **or** isengardcli | See below | See below |
| Bedrock model access | Enabled in your AWS account (see below) | Same |

### Credential Tool: ada vs isengardcli

The scripts auto-detect which tool is available on your machine:

- **ada** (preferred) — the current credential tool. Install with `toolbox install ada`
- **isengardcli** (legacy fallback) — for older machines that already have it. No longer available for new installs via toolbox.

If both are present, the scripts use `ada`. If neither is found, the script exits with install instructions.

### Enable Bedrock Model Access (one-time per account)

1. Go to **AWS Console → Amazon Bedrock → Model catalog**
2. Find the Anthropic Claude models
3. Complete the use case form (access is granted immediately)

### IAM Permissions

Attach the policy in [`iam-policy.json`](./iam-policy.json) to the IAM role used by your team. Required actions:

- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`
- `bedrock:ListInferenceProfiles`
- `bedrock:GetInferenceProfile`

---

## macOS Setup

```bash
chmod +x setup-macos.sh
./setup-macos.sh
```

The script will:
- Detect whether **ada** or **isengardcli** is available
- Prompt for your **AWS account ID**
- Create an AWS profile called `claude-bedrock`
- Append env vars to `~/.bashrc` and `~/.zshrc`
- Install Claude Code globally via npm (requires sudo)
- Launch Claude Code

**Shell support:** Both bash and zsh are configured automatically.

---

## Windows Setup

Open **PowerShell** (as Administrator for the npm install) and run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\setup-windows.ps1
```

The script will:
- Detect whether **ada** or **isengardcli** is available
- Prompt for your **AWS account ID**
- Create an AWS profile called `claude-bedrock`
- Set persistent **user-level** environment variables (survive reboots)
- Add env vars to your **PowerShell profile** for new sessions
- Install Claude Code globally via npm
- Launch Claude Code

---

## What Gets Configured

Both scripts set these environment variables:

| Variable | Value |
|---|---|
| `CLAUDE_CODE_USE_BEDROCK` | `1` |
| `AWS_PROFILE` | `claude-bedrock` |
| `AWS_REGION` | `us-east-1` |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `us.anthropic.claude-sonnet-4-6` |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | `us.anthropic.claude-opus-4-7` |

---

## After Setup

Once the script finishes, Claude Code launches automatically. Run `/status` inside Claude Code to confirm the provider shows **Amazon Bedrock**.

To launch Claude Code in future sessions, just run:

```bash
claude
```

The environment variables persist across terminal sessions.

---

## Credential Refresh

Credentials are temporary. When they expire, refresh them:

**ada:**
```bash
ada credentials update --account <your-account-id> --profile claude-bedrock --role <your-role> --once
```
> Common roles: `Admin`, `ReadOnly`, or a custom role assigned by your team admin.
> Omit `--once` to keep credentials auto-refreshing in the background.

**isengardcli (legacy):**
```bash
isengardcli credentials <your-account-id>
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `isengardcli` / `ada` not found | `toolbox install ada` (new machines) or `toolbox install isengardcli` (legacy) |
| Region errors | Verify model availability: `aws bedrock list-inference-profiles --region us-east-1` |
| npm permission denied (macOS) | Run with `sudo`: `sudo npm install -g @anthropic-ai/claude-code` |
| npm permission denied (Windows) | Run PowerShell as Administrator |
| Credentials expired | `ada credentials update --account <account-id> --profile claude-bedrock --role <your-role> --once` or `isengardcli credentials <account-id>` |
| Profile already exists | The script will ask if you want to overwrite it |
| MCP servers failing to authenticate | Midway-dependent MCPs (outlook, slack, sentral) don't work in Claude Code — they can't run `mwinit` interactively. Use those in Kiro only. `builder-mcp` and `aws-docs` work fine. |

---

## Files

| File | Description |
|---|---|
| `setup-macos.sh` | Team setup script for macOS (bash/zsh) |
| `setup-windows.ps1` | Team setup script for Windows (PowerShell) |
| `iam-policy.json` | IAM policy with required Bedrock permissions |

---

## References

- [Official Anthropic docs — Claude Code on Bedrock](https://docs.anthropic.com/en/docs/claude-code/amazon-bedrock)
- [Bedrock IAM documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html)
- [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
