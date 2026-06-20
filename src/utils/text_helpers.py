import platform
import subprocess


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


def get_recommended_model():
    """Detects system RAM and returns an appropriate Ollama model name.
    
    Returns 'llama3' for systems with >= 16GB RAM, otherwise 'llama3.2'.
    Used as the default model across all scripts (main.py, reconvert.py, etc.).
    """
    model = "llama3.2"  # Default to lightweight
    try:
        system = platform.system()
        total_ram_gb = 0

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
