"""Push the backend to a Hugging Face Space (Docker SDK) and set its secrets.

Only the files the image needs are uploaded (Dockerfile, requirements.txt,
backend/), plus deploy/hf_space_README.md as the Space's README — HF reads the
Space config (sdk: docker, app_port) from that file's YAML header.

Usage (reads HF_TOKEN and the app secrets from .env):
    python deploy/deploy_hf.py <username>/<space-name> [--origins https://my-app.vercel.app]
"""
import argparse
import os
from pathlib import Path

from dotenv import dotenv_values
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
SECRETS = ['GROQ_API_KEY', 'SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE_ANON_KEY']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('space_id', help='e.g. aditya/ats-resume-api')
    parser.add_argument('--origins', help='Comma-separated frontend origins allowed by CORS')
    args = parser.parse_args()

    env = {**dotenv_values(ROOT / '.env'), **os.environ}
    api = HfApi(token=env.get('HF_TOKEN'))

    api.create_repo(args.space_id, repo_type='space', space_sdk='docker', exist_ok=True)

    for key in SECRETS:
        if env.get(key):
            api.add_space_secret(args.space_id, key, env[key])
    if args.origins:
        api.add_space_variable(args.space_id, 'ALLOWED_ORIGINS', args.origins)

    api.upload_folder(
        repo_id=args.space_id, repo_type='space', folder_path=ROOT,
        allow_patterns=['Dockerfile', 'requirements.txt', 'backend/**/*.py', 'backend/**/*.sql'],
        ignore_patterns=['**/__pycache__/**'],
        commit_message='Deploy backend',
    )
    api.upload_file(
        repo_id=args.space_id, repo_type='space',
        path_or_fileobj=ROOT / 'deploy' / 'hf_space_README.md', path_in_repo='README.md',
        commit_message='Space config',
    )
    # Space subdomain = "<owner>-<name>", lowercased, with "_" and "." turned into "-"
    host = args.space_id.replace('/', '-').replace('_', '-').replace('.', '-').lower()
    print(f'Deployed. Build logs: https://huggingface.co/spaces/{args.space_id}')
    print(f'API URL:            https://{host}.hf.space')


if __name__ == '__main__':
    main()
