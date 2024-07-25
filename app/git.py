# -*- coding: utf-8 -*-
import json
from os import abort
from threading import Thread
from flask import Blueprint, request, jsonify
from config.config import WEBHOOK_VERIFY_TOKEN
from service.chat_review import review_pr_code
from utils.LogHandler import log

git = Blueprint('git', __name__)

storage_file_path = 'commit_storage.json'
commit_storage = {}
try:
    with open(storage_file_path, 'r') as file:
        commit_storage = json.load(file)
except (FileNotFoundError, json.JSONDecodeError):
    commit_storage = {}


def review_pr_code_async(project_name, pr_id):
    # Wraps the original function to be used in a thread
    def target():
        review_pr_code(project_name, pr_id)
    
    # Start the review in a separate thread
    thread = Thread(target=target)
    thread.start()

@git.route('/api')
def question():
    return 'hello world'

@git.route('/webhook_github', methods=['GET', 'POST'])
def webhook_github():
    """
    receive pushes from GitHub
    """
    log.info('got GitHub webhook')
    print("heelo")

    if request.method == 'POST':
        """
        Main logic of the webhook, getting the GitHub push information
        """
        github_message = request.data.decode('utf-8')
        github_message = json.loads(github_message)

        # Get the project type
        valid_PR = github_message["pull_request"]

        if valid_PR:
            # Verification passed, get commit information
            # Get project ID
            project_name = valid_PR.get("head")["repo"]["full_name"]
            # Get PR ID
            pr_id = valid_PR.get("number")
            # Get last commit
            last_commit = valid_PR.get("head")["sha"]
            
            pr_url = f"PR: https://github.com/{project_name}/pull/{pr_id}"
            # log.info(f"PR: https://github.com/{project_name}/pull/{pr_id} , Last Commit: {last_commit}")
            # Generate a unique key for each project_name and pr_id combination
            key = f"{project_name}_{pr_id}"
            # Check if there is an existing last_commit stored
            if key not in commit_storage or commit_storage[key] != last_commit:
                # Update the last_commit in storage
                commit_storage[key] = last_commit
                with open(storage_file_path, 'w') as file:
                    json.dump(commit_storage, file, indent=4)
                # Trigger the process
                log.info(f"PR: {pr_url} Start ChatGPT code patch review")
                review_pr_code_async(project_name, pr_id)
            else:
                log.info(f"PR: {pr_url} No new commit, no comment")

            return jsonify({'status': 'success'}), 200
        else:
            log.error("Project is not a push or Merge Request")
            return jsonify({'status': 'bad token'}), 401
    else:
        abort(400)