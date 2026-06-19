import os
import re
import argparse
import json

def _safe_truncate(text, max_chars):
    """Truncate text to max_chars without breaking multi-byte UTF-8 characters."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.8:
        return truncated[:last_space]
    return truncated

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

REQUIRED_SECTIONS = [
    r"## 🧠 Core Summary",
    r"## 💡 Key Concepts & Definitions",
    r"## 📌 Important Details / Application",
    r"## 📝 Original Context & Quotes"
]

def heuristic_validation(content):
    """Validasi menggunakan aturan regex dasar dan panjang teks."""
    score = 0
    max_score = 100
    feedback = []
    
    # Check for tags (must be #word, not ## heading)
    if re.search(r'^#(?!#)[a-zA-Z]\w*', content, re.MULTILINE):
        score += 10
    else:
        feedback.append("Tags are missing.")
        
    # Check for sections
    section_points = 80 / len(REQUIRED_SECTIONS)
    
    for section in REQUIRED_SECTIONS:
        if re.search(section, content):
            score += section_points
        else:
            feedback.append(f"Missing section: {section.replace('## ', '').strip()}")
            
    # Check for length
    words = content.split()
    if len(words) < 50:
        score -= 20
        feedback.append("Content is suspiciously short (under 50 words).")
    elif len(words) > 50:
        score += 10 # Bonus for sufficient length
        
    score = min(max_score, max(0, score))
    status = "OK" if score >= 80 else "NEEDS RECONVERT"
    
    return round(score, 2), status, feedback

def llm_validation(content, model_name='llama3'):
    """Validasi komprehensif menggunakan Ollama LLM."""
    if not OLLAMA_AVAILABLE:
        return 0, "ERROR", ["Ollama package is not installed."]
        
    prompt = f"""
Anda adalah AI Quality Control untuk sistem basis data Retrieval-Augmented Generation (RAG).
Tugas Anda adalah mengevaluasi hasil ekstraksi dokumen (markdown) berikut. 
Berikan skor dari 0 hingga 100 berdasarkan kriteria berikut:
1. Struktur: Apakah memiliki 4 bagian inti (Core Summary, Key Concepts, Important Details, Original Context)? Apakah ada header dinamis tambahan yang sesuai konteks?
2. Kualitas Konten: Apakah isinya informatif, akurat, dan komprehensif sesuai topik aslinya?
3. Format: Apakah formatnya rapi dan mudah dibaca oleh manusia maupun AI (RAG-ready)?

Format jawaban HANYA berupa JSON valid:
{{
  "score": 85,
  "status": "OK", // "OK" jika score >= 80, jika kurang gunakan "NEEDS RECONVERT"
  "feedback": ["alasan 1", "alasan 2"]
}}

Dokumen untuk dievaluasi:
{_safe_truncate(content, 3000)}
"""
    try:
        response = ollama.chat(model=model_name, messages=[
            {'role': 'user', 'content': prompt}
        ], format='json')
        
        # Handle both dict and object-style responses from ollama-python
        if isinstance(response, dict):
            response_text = response.get('message', {}).get('content', '')
        else:
            msg = getattr(response, 'message', None)
            response_text = getattr(msg, 'content', '') if msg else ''
        try:
            parsed_json = json.loads(response_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    parsed_json = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    return 0, "ERROR", ["LLM Validation failed: Regex matched but still not valid JSON"]
            else:
                return 0, "ERROR", ["LLM Validation failed: Valid JSON not found in LLM response"]
        
        score = parsed_json.get("score", 0)
        # Clamp score to valid range and validate status
        score = min(100, max(0, score))
        status = parsed_json.get("status", "NEEDS RECONVERT")
        if status not in ("OK", "NEEDS RECONVERT", "ERROR"):
            status = "OK" if score >= 80 else "NEEDS RECONVERT"
        feedback = parsed_json.get("feedback", [])
        if not isinstance(feedback, list):
            feedback = [str(feedback)]
        
        return score, status, feedback
    except Exception as e:
        return 0, "ERROR", [f"LLM Validation failed: {str(e)}"]

def validate_file(file_path, use_llm=False, model_name='llama3'):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if use_llm and OLLAMA_AVAILABLE:
            score, status, feedback = llm_validation(content, model_name)
        else:
            score, status, feedback = heuristic_validation(content)
            
        return {
            "file": os.path.basename(file_path),
            "score": score,
            "status": status,
            "feedback": feedback
        }
    except Exception as e:
        return {"file": os.path.basename(file_path), "score": 0, "status": "ERROR", "feedback": [str(e)]}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validasi output Markdown hasil generate.")
    parser.add_argument("path", help="Path file atau direktori output yang ingin divalidasi")
    parser.add_argument("--llm", action="store_true", help="Gunakan Ollama LLM untuk validasi yang lebih mendalam")
    parser.add_argument("--model", default="llama3", help="Model Ollama yang digunakan (default: llama3)")
    
    args = parser.parse_args()
    
    target_path = args.path
    
    if not os.path.exists(target_path):
        print(f"Error: Path {target_path} tidak ditemukan.")
        exit(1)
        
    print(f"Memulai validasi pada: {target_path}")
    print(f"Metode: {'LLM (' + args.model + ')' if args.llm else 'Heuristic/Regex'}\n")
    
    def print_result(res):
        status_color = "\033[92m" if res['status'] == "OK" else "\033[91m"
        reset_color = "\033[0m"
        print(f"📄 File: {res['file']}")
        print(f"   Score: {res['score']}/100")
        print(f"   Status: {status_color}{res['status']}{reset_color}")
        if res['feedback'] and res['status'] != "OK":
            print("   Feedback:")
            for fb in res['feedback']:
                print(f"     - {fb}")
        print("-" * 40)
    
    if os.path.isfile(target_path):
        print(f"> Memvalidasi {target_path}...", flush=True)
        res = validate_file(target_path, args.llm, args.model)
        print_result(res)
    elif os.path.isdir(target_path):
        for root, dirs, files in os.walk(target_path):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    print(f"> Memvalidasi {file}...", flush=True)
                    res = validate_file(file_path, args.llm, args.model)
                    print_result(res)
