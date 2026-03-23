#!/usr/bin/env python3
"""
Translate Anthropic courses notebooks and READMEs to Czech.
Uses OpenAI GPT-4o for translation.
"""

import json
import os
import sys
import time
from pathlib import Path
from openai import OpenAI

# Get API key from Claude settings
SETTINGS_FILE = os.path.expanduser("~/.claude/settings.json")
with open(SETTINGS_FILE) as f:
    settings = json.load(f)
OPENAI_API_KEY = settings["env"]["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are a professional Czech translator specializing in technical documentation and educational content about AI and programming.

Your task is to translate English text to Czech while:
1. Keeping all code examples, variable names, function names, class names, and API names UNCHANGED
2. Keeping technical terms like "prompt", "token", "API", "SDK", "model" in English (they are widely used in Czech tech community)
3. Translating all explanatory text, instructions, headings, and comments to Czech
4. Translating Python/code COMMENTS (lines starting with #) to Czech
5. Keeping markdown formatting (**, *, #, -, >, ``` etc.) intact
6. Keeping any URLs, file paths, and placeholders unchanged
7. Preserving newlines and spacing exactly as in the original

Return ONLY the translated text, nothing else. Do not add any explanation or preamble."""


def translate_text(text: str) -> str:
    """Translate a piece of text to Czech using OpenAI."""
    if not text.strip():
        return text

    # Skip if it's purely code (no English words to translate)
    # But still process it for comments

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Translate this to Czech:\n\n{text}"}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"  ERROR translating: {e}")
        return text


def translate_notebook(filepath: Path) -> None:
    """Translate a Jupyter notebook file in place."""
    print(f"\nTranslating: {filepath.relative_to(Path('/Users/krystofdvorak/anthropic-courses-cs'))}")

    with open(filepath, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    cells = nb.get('cells', [])
    total = len(cells)

    for i, cell in enumerate(cells):
        cell_type = cell.get('cell_type', '')
        source = cell.get('source', [])

        if isinstance(source, list):
            text = ''.join(source)
        else:
            text = source

        if not text.strip():
            continue

        if cell_type == 'markdown':
            print(f"  [{i+1}/{total}] markdown cell ({len(text)} chars)...")
            translated = translate_text(text)
            if isinstance(source, list):
                cell['source'] = [translated]
            else:
                cell['source'] = translated
            time.sleep(0.5)  # Rate limiting

        elif cell_type == 'code':
            # Only translate if there are comments (lines starting with #)
            lines = text.split('\n')
            has_comments = any(line.strip().startswith('#') for line in lines)
            if has_comments and len(text) < 3000:  # Only translate shorter code cells with comments
                print(f"  [{i+1}/{total}] code cell with comments ({len(text)} chars)...")
                translated = translate_text(text)
                if isinstance(source, list):
                    cell['source'] = [translated]
                else:
                    cell['source'] = translated
                time.sleep(0.5)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

    print(f"  Done!")


def translate_readme(filepath: Path) -> None:
    """Translate a README.md file in place."""
    print(f"\nTranslating README: {filepath.relative_to(Path('/Users/krystofdvorak/anthropic-courses-cs'))}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if not content.strip():
        return

    # Split into chunks if very long (>3000 chars)
    if len(content) <= 3000:
        translated = translate_text(content)
    else:
        # Split by double newline (paragraphs) and translate in chunks
        chunks = content.split('\n\n')
        translated_chunks = []
        current_chunk = ''

        for chunk in chunks:
            if len(current_chunk) + len(chunk) < 2500:
                current_chunk += '\n\n' + chunk if current_chunk else chunk
            else:
                if current_chunk:
                    translated_chunks.append(translate_text(current_chunk))
                    time.sleep(0.5)
                current_chunk = chunk

        if current_chunk:
            translated_chunks.append(translate_text(current_chunk))

        translated = '\n\n'.join(translated_chunks)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(translated)

    print(f"  Done!")


def main():
    base = Path('/Users/krystofdvorak/anthropic-courses-cs')

    # Get files to translate - can filter by argument
    filter_path = sys.argv[1] if len(sys.argv) > 1 else None

    # Find all notebooks
    notebooks = sorted(base.rglob('*.ipynb'))
    readmes = sorted(base.rglob('README.md'))

    if filter_path:
        notebooks = [n for n in notebooks if filter_path in str(n)]
        readmes = [r for r in readmes if filter_path in str(r)]

    print(f"Found {len(notebooks)} notebooks and {len(readmes)} READMEs to translate")

    # Translate READMEs first
    for readme in readmes:
        translate_readme(readme)

    # Translate notebooks
    for notebook in notebooks:
        translate_notebook(notebook)

    print("\n\nAll translations complete!")


if __name__ == '__main__':
    main()
