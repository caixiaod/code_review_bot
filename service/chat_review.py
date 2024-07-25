# -*- coding: utf-8 -*-
import openai
import requests
from requests.auth import HTTPBasicAuth
from openai import OpenAIError
from retrying import retry
import json
import re
import os
from datetime import datetime
from config.config import (
    github_token,
    openai_model_name,
    chatbot_server_url,
    chatbot_user,
    chatbot_password,
)
from config.supported_lang import supported_extension
from utils.LogHandler import log
from service.prompt_infill import prompt_infill
from base64 import b64decode

github_headers = {
    'Accept': 'application/vnd.github.v3+json',
    'Authorization': f'token {github_token}'
}

def get_current_time_string():
    # Generate the current time string in the desired format
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return current_time

def save2file(prompt_content, review_note, filename):
    os.makedirs('logs/prompts', exist_ok=True)
    
    review_note_filename = f'logs/prompts/{filename}_review_note.md'
    with open(review_note_filename, 'w', encoding='utf-8') as file:
        file.write(review_note)
    log.info(f'review_note is saved to {review_note_filename}')
    
    prompt_filename = f'logs/prompts/{filename}_prompt.md'
    with open(prompt_filename, 'w', encoding='utf-8') as file:
        file.write(prompt_content)
    log.info(f'prompt_content is saved to {prompt_filename}')
def check_file_type(file_path):
    """
    Checks if the file type is supported based on its extension.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file type is supported, False otherwise.
    """
    _, file_extension = os.path.splitext(file_path)
    return file_extension in supported_extension

def find_line_number(diff_text):
    """
    Finds the first added and removed line numbers in a diff text.

    Args:
        diff_text (str): The diff text.

    Returns:
        tuple: A tuple containing the first added line number and the first removed line number.
    """
    diff_lines = diff_text.splitlines()
    first_added_line = first_removed_line = None
    current_line_number = 0

    for line in diff_lines:
        if line.startswith('@@'):
            match = re.search(r'\+(\d+)', line)
            if match:
                current_line_number = int(match.group(1))
        elif line.startswith('+') and not line.startswith('+++'):
            if first_added_line is None:
                first_added_line = current_line_number
            current_line_number += 1
        elif line.startswith('-') and not line.startswith('---'):
            if first_removed_line is None:
                first_removed_line = current_line_number
        elif not line.startswith('-'):
            current_line_number += 1

        if first_added_line is not None and first_removed_line is not None:
            break

    return first_added_line, first_removed_line

@retry(stop_max_attempt_number=3, wait_fixed=5000)
def post_pr_comments(project_name, pr_id, review_note, diff_content):
    new_line_number, old_line_number = find_line_number(diff_content['diff'])
    data = {
        'body': review_note,
        'commit_id': diff_content['sha'],
        'path': diff_content['new_path'],
        "line":new_line_number,
        "side":"RIGHT"
    }
    # log.info(data)
    url = f'https://api.github.com/repos/{project_name}/pulls/{pr_id}/comments'
    response = requests.post(url, headers=github_headers, json=data)

    if response.status_code == 201:
        log.info('Comment posted successfully')
    else:
        log.error(f'Failed to post comment: {response.status_code}, {response.json()}')

def wait_and_retry(exception):
    return isinstance(exception, OpenAIError)

@retry(retry_on_exception=wait_and_retry, stop_max_attempt_number=3, wait_fixed=60000)
def generate_review_note(title, source_code, change):
    """
    Generates a review note using ChatGPT.

    Args:
        title (str): The title of the change.
        source_code (str): The source code.
        change (dict): The change information.

    Returns:
        str: The generated review note.
    """
    diff_content = change['diff']
    filename_new = change['new_path']
    is_removed_file = change['deleted_file']
    if is_removed_file:
        source_code = ""

    prompt_content = prompt_infill(title, diff_content, source_code, filename_new)
    # log.info(f"prompt content\n{prompt_content}")

    response = requests.post(
        chatbot_server_url,
        auth=HTTPBasicAuth(chatbot_user, chatbot_password),
        json={
            "query": prompt_content,
            "stream": False,
            "model_name": openai_model_name,
            "temperature": 0.7
        })
    if response.status_code == 200:
        j = json.loads(response.text[6:], strict=False)
        review_note = j['text']
        log.info(f'Review is complete for: {filename_new}')
    else:
        review_note = ""
        log.error(f"Review in incomplete for {filename_new}")

    return prompt_content, review_note

@retry(stop_max_attempt_number=3, wait_fixed=5000)
def review_pr_code(project_name, pr_id):
    """
    Reviews the code of a GitHub pull request.

    Args:
        project_name (str): The full name of the project.
        pr_id (int): The pull request ID.

    Returns:
        None
    """
    # Step 1: Get the pull request details
    pr_url = f'https://api.github.com/repos/{project_name}/pulls/{pr_id}'
    pr_response = requests.get(pr_url, headers=github_headers)
    pr_data = pr_response.json()

    # Step 2: List the files changed in the pull request
    # log.info(f"PR Data is: {pr_data}")
    files_url = pr_data['_links']['self']['href'] + '/files'
    files_response = requests.get(files_url, headers=github_headers)
    files_data = files_response.json()

    # Step 3: Fetch the content of each changed file from the source branch
    for file_info in files_data:
        file_path = file_info['filename']
        raw_url = file_info['raw_url']
        
        # You can also use the content URL
        content_url = f"https://api.github.com/repos/{project_name}/contents/{file_path}?ref={pr_data['head']['ref']}"
        content_response = requests.get(content_url, headers=github_headers)
        content_data = content_response.json()
        
        # The file content is base64 encoded, so decode it
        source_code = b64decode(content_data['content']).decode('utf-8')
        
        title = pr_data['title']
        diff_content = {
            "new_path": file_path,
            "diff": file_info['patch'],
            "deleted_file": file_info['status'] == 'removed',
            "sha": pr_data['head']['sha']
        }
        # log.info(diff_content['diff'])
        prompt_content, review_note = generate_review_note(title, source_code, diff_content)
        current_time_str = get_current_time_string()
        url_encoded_path = file_path.replace("/", "%2F").replace(".", "%2E")
        md_filename = f"{current_time_str}_{project_name}_{pr_id}_{url_encoded_path}"
        save2file(prompt_content, review_note, md_filename)
        # log.info(f'Review result for {file_path}: {review_note}')
        if review_note:
            post_pr_comments(project_name, pr_id, review_note, diff_content)


def find_line_within_code(source_code, search_string):
    """
    Finds the line number containing the search string in the source code.

    Args:
        source_code (str): The source code.
        search_string (str): The string to search for.

    Returns:
        int: The line number where the string was found, or None if not found.
    """
    lines = source_code.split('\n')
    for i, line in enumerate(lines, start=1):
        if search_string in line:
            return i
    return None

if __name__ == '__main__':
    project_id = 787
    project_commit_id = ['ac98654c27a669bf88ce6d261d371a259c19dfcc']
    log.info(f"Project ID: {project_id}, commit ID: {project_commit_id}, starting ChatGPT code review")