"""
Fill in the diff content into prompt template.
"""
import os
from config.supported_lang import supported_extension

# read prompt template from file
def read_prompt_template():
    with open("config/prompt_template.md", "r") as f:
        prompt_template = f.read()
    return prompt_template

# fill in the diff content into prompt template
def prompt_infill(title, diff_content, source_code, filename):
    max_length = 120000
    _, file_extension = os.path.splitext(filename)
    language = supported_extension.get(file_extension, 'text')  # Default to 'text' if not found
    
    
    prompt = read_prompt_template()
    prompt = prompt.replace("Embedded C", language)

    prompt = prompt.replace("**Summary**:", "**Summary**: " + title)
    prompt = prompt.replace("**Files Modified**:", "**Files Modified**: " + filename)
    
    # Truncate diff code to fit within 128k character.
    prompt_length = len(prompt) + len(diff_content)
    if prompt_length > max_length:
        diff_length = max_length - len(prompt)
        diff_content = diff_content[:diff_length]
    markdown_code_block = f"```diff\n{diff_content}\n```"
    prompt = prompt.replace("## Patch Diff", "## Patch Diff\n" + markdown_code_block)

    # Truncate source code to fit within 128k character.
    prompt_length = len(prompt) + len(source_code)
    if prompt_length > max_length:
        code_length = max_length - len(prompt)
        source_code = source_code[:code_length]

    markdown_code_block = f"```{language}\n{source_code}\n```"
    prompt = prompt.replace("## Source Code Context", "## Source Code Context\n" + markdown_code_block)

    return prompt