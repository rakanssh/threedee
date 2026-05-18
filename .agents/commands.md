# Commands

## Local Smoke Checks

```bash
python3 -m compileall threedee
python3 -m threedee.cli --help
python3 -m threedee.cli generate "stylized armored knight" --dry-run
python3 -m threedee.cli status
python3 -m threedee.cli list
```

Clean dry-run artifacts before committing:

```bash
rm -rf runs threedee/__pycache__
```

## Install Editable

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## OpenRouter

macOS/Linux:

```bash
export OPENROUTER_API_KEY="..."
```

PowerShell:

```powershell
$env:OPENROUTER_API_KEY = "..."
```

Generate only through the OpenRouter image stage:

```bash
threedee generate "stylized armored knight" --until image
```

## Benchmarking

```bash
threedee benchmark mesh hunyuan3d <job_id>
threedee benchmark rig riganything <job_id>
```
