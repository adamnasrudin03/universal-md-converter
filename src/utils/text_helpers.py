import platform
import subprocess
import re

def clean_raw_text(text):
    """
    Cleans raw text by removing excessive whitespace, tabs, and newlines.
    This saves LLM context window tokens and improves output formatting.
    """
    if not text:
        return text
    # Replace 3 or more consecutive newlines with exactly 2 newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Replace multiple spaces/tabs with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Clean spaces at the start and end of each line
    text = '\n'.join(line.strip() for line in text.split('\n'))
    # One more pass for newlines because stripping lines might have created empty lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def safe_truncate(text, max_chars):
    """Truncate text to max_chars without breaking mid-word.
    
    Finds the last space within the truncated text to produce a clean cut.
    This is the single canonical implementation — all modules should import
    from here instead of defining their own copy.
    """
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(' ')
    # Only break at a space if one exists reasonably close to the end (within 80%).
    # If no space found (e.g., long URL or base64), just hard-cut at max_chars.
    if last_space > max_chars * 0.8:
        return truncated[:last_space]
    return truncated


def get_total_ram_gb():
    """Returns the total system RAM in GB using psutil if available, fallback to sysctl/proc."""
    total_ram_gb = 0
    try:
        import psutil
        total_ram_gb = psutil.virtual_memory().total / (1024**3)
    except ImportError:
        try:
            system = platform.system()
            if system == "Darwin":  # macOS
                res = subprocess.run(
                    ['sysctl', '-n', 'hw.memsize'],
                    capture_output=True, text=True
                )
                if res.returncode == 0:
                    total_ram_bytes = int(res.stdout.strip())
                    total_ram_gb = total_ram_bytes / (1024**3)
            elif system == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if 'MemTotal' in line:
                            kb = int(line.split()[1])
                            total_ram_gb = kb / (1024**2)
                            break
        except Exception:
            pass
    return total_ram_gb

def get_available_ram_gb():
    """Returns the currently available system RAM in GB using psutil."""
    try:
        import psutil
        return psutil.virtual_memory().available / (1024**3)
    except ImportError:
        # Fallback to total if psutil is not installed (should not happen if requirements.txt is installed)
        return get_total_ram_gb()


def check_system_requirements():
    """Checks system specs and warns the user if minimum requirements are not met."""
    ram_gb = get_total_ram_gb()
    if ram_gb > 0 and ram_gb < 8.0:
        print(f"⚠️  WARNING: Your system has {ram_gb:.1f} GB of RAM.")
        print("   This application uses local AI models (Ollama) and Whisper,")
        print("   which require significant memory. Minimum 8 GB is required,")
        print("   but 16 GB or more is highly recommended.")
        print("   Running this script on your system may cause severe lag or crashes.")
        print("   You may also experience Out of Memory (OOM) errors.")
        
        response = input("Do you want to continue anyway? (y/N): ")
        if response.strip().lower() != 'y':
            print("Aborting.")
            import sys
            sys.exit(1)


def get_recommended_model():
    """Detects system RAM and returns an appropriate Ollama model name.
    
    Returns 'llama3' for systems with >= 16GB RAM, otherwise 'llama3.2'.
    Used as the default model across all scripts (main.py, reconvert.py, etc.).
    """
    model = "llama3.2"  # Default to lightweight
    try:
        total_ram_gb = get_total_ram_gb()

        if total_ram_gb >= 15.5:  # 16GB RAM or more
            model = "llama3"
            print(f"🖥️  System RAM: {total_ram_gb:.1f} GB. Auto-selecting heavy model: '{model}'")
        elif total_ram_gb > 0:
            print(f"🖥️  System RAM: {total_ram_gb:.1f} GB. Auto-selecting lightweight model: '{model}'")
        else:
            print(f"🖥️  Auto-selecting lightweight model: '{model}' (Failed to read RAM)")

    except Exception:
        print(f"🖥️  Auto-selecting lightweight model: '{model}' (System check error)")

    return model

def get_recommended_concurrency():
    """Determines safe concurrency level based on dynamically available system RAM.
    
    Returns 3 for systems with >= 8GB FREE RAM, otherwise 1 (sequential).
    """
    concurrency = 1
    available_ram_gb = get_available_ram_gb()
    if available_ram_gb >= 8.0:  # If we have 8GB *free* right now, we can run multiple LLM queries
        concurrency = 3

    return concurrency
