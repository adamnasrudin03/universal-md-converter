import os
import re
import argparse
import json
import sys

from utils.text_helpers import safe_truncate, get_recommended_model


try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

REQUIRED_SECTIONS = [
    r"## 🧠 Core Summary"
]

MIN_SCORE_THRESHOLD = int(os.environ.get("MIN_SCORE", 85))

def heuristic_validation(content):
    """Validasi menggunakan aturan regex dasar dan panjang teks."""
    score = 0
    max_score = 100
    feedback = []
    
    # Check for tags (must be #word, not ## heading) — supports multi-word tags like #trading-pattern
    if re.search(r'^#(?!#)\S+', content, re.MULTILINE):
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
    else:
        score += 10 # Bonus for sufficient length (>= 50 words)
        
    score = min(max_score, max(0, score))
    status = "OK" if score >= MIN_SCORE_THRESHOLD else "NEEDS RECONVERT"
    
    return round(score, 2), status, feedback

def llm_validation(content, file_path=None, model_name='llama3'):
    """Validasi komprehensif menggunakan Ollama LLM dengan Ground Truth Validation jika memungkinkan."""
    if not OLLAMA_AVAILABLE:
        return 0, "ERROR", ["Ollama package is not installed."]
    
    # Check for raw text file for comparative validation
    raw_content = None
    if file_path:
        raw_filepath = f"{file_path}.raw.txt"
        if os.path.exists(raw_filepath):
            with open(raw_filepath, 'r', encoding='utf-8') as f:
                raw_content = f.read()
                
    # Pre-compute truncation to avoid nested expression inside f-string
    truncated_content = safe_truncate(content, 2500)
    
    if raw_content:
        truncated_raw = safe_truncate(raw_content, 2500)
        prompt = f"""
Anda adalah AI Quality Control untuk sistem basis data Retrieval-Augmented Generation (RAG).
Tugas Anda adalah mengevaluasi hasil ekstraksi dokumen (markdown) dengan membandingkannya dengan teks sumber aslinya (RAW TEXT).

RAW TEXT (Sumber Asli):
{truncated_raw}

DOKUMEN RAG (Hasil Ekstraksi):
{truncated_content}

Berikan skor dari 0 hingga 100 berdasarkan kriteria berikut:
1. Struktur (20 poin): Apakah memiliki bagian `Core Summary`? Apakah penggunaan Header Dinamis wajar (maksimal 3)?
2. Kualitas RAG & Anti-Redundansi (20 poin): Apakah Core Summary kaya kata kunci? Apakah informasi padat dan TIDAK redundan antar bagian?
3. Formatting & Visualisasi (20 poin): Apakah formatnya rapi (Markdown Table untuk perbandingan, Numbered List untuk langkah)? Terhindar dari wall-of-text?
4. Akurasi & Konsistensi Fakta (40 poin): PENALTI BESAR jika RAG mengandung halusinasi, informasi yang tidak ada di RAW TEXT, atau salah mengutip angka/fakta dari RAW TEXT.

Format jawaban HANYA berupa JSON valid (tanpa teks lain di luar JSON):
{{
  "score": 0,
  "status": "NEEDS RECONVERT",
  "feedback": ["alasan 1", "alasan 2"]
}}

Catatan: Ganti "score" dengan angka 0-100 hasil evaluasi Anda. "status" harus "OK" jika score >= {MIN_SCORE_THRESHOLD}, atau "NEEDS RECONVERT" jika score < {MIN_SCORE_THRESHOLD}.
"""
    else:
        prompt = f"""
Anda adalah AI Quality Control untuk sistem basis data Retrieval-Augmented Generation (RAG).
Tugas Anda adalah mengevaluasi hasil ekstraksi dokumen (markdown) berikut.
Berikan skor dari 0 hingga 100 berdasarkan kriteria berikut:

1. Struktur (25 poin): Apakah memiliki bagian `Core Summary`? (Ingat: Key Concepts, Important Details, dan Original Context bersifat OPSIONAL dan BOLEH DIHAPUS jika teks tidak relevan). Apakah penggunaan Header Dinamis wajar (maksimal 3)?
2. Kualitas RAG & Anti-Redundansi (30 poin): Apakah Core Summary kaya kata kunci? Apakah informasi padat dan TIDAK redundan antar bagian? Apakah angka dan fakta dipertahankan akurat?
3. Formatting & Visualisasi (25 poin): Apakah formatnya rapi (menggunakan Markdown Table jika ada data perbandingan, Numbered List untuk langkah-langkah)? Apakah ada bold untuk kata kunci? Apakah terhindar dari wall-of-text?
4. Akurasi & Metadata (20 poin): Apakah tag dan slug deskriptif dan spesifik (bukan generik)? Apakah isinya konsisten dan terhindar dari hallucination?

Format jawaban HANYA berupa JSON valid (tanpa teks lain di luar JSON):
{{
  "score": 0,
  "status": "NEEDS RECONVERT",
  "feedback": ["alasan 1", "alasan 2"]
}}

Catatan: Ganti "score" dengan angka 0-100 hasil evaluasi Anda. "status" harus "OK" jika score >= {MIN_SCORE_THRESHOLD}, atau "NEEDS RECONVERT" jika score < {MIN_SCORE_THRESHOLD}.

Dokumen untuk dievaluasi:
{truncated_content}
"""
    try:
        response = ollama.chat(model=model_name, messages=[
            {'role': 'user', 'content': prompt}
        ], format='json', options={'temperature': 0.0})
        
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
        
        raw_score = parsed_json.get("score", 0)
        # Coerce score to numeric — LLM might return string or other types
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0
        # Clamp score to valid range and validate status
        score = min(100, max(0, score))
        # Selalu paksa status dihitung ulang dari score untuk menghindari halusinasi LLM
        status = "OK" if score >= MIN_SCORE_THRESHOLD else "NEEDS RECONVERT"
        feedback = parsed_json.get("feedback", []) or []
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
            score, status, feedback = llm_validation(content, file_path, model_name)
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
    parser.add_argument("--model", default="auto", help="Model Ollama yang digunakan (default: auto-detect berdasarkan RAM)")
    
    args = parser.parse_args()
    
    target_path = args.path
    
    if not os.path.exists(target_path):
        print(f"Error: Path {target_path} tidak ditemukan.")
        sys.exit(1)
        
    model = args.model
    if model == "auto":
        model = get_recommended_model()

    print(f"Memulai validasi pada: {target_path}")
    print(f"Metode: {'LLM (' + model + ')' if args.llm else 'Heuristic/Regex'}\n")
    
    def print_result(res):
        status_color = "\033[92m" if res['status'] == "OK" else "\033[91m"
        reset_color = "\033[0m"
        print(f"📄 File: {res['file']}")
        print(f"   Score: {res['score']}/100")
        print(f"   Status: {status_color}{res['status']}{reset_color}")
        if res['feedback']:
            print("   Feedback:")
            for fb in res['feedback']:
                print(f"     - {fb}")
        print("-" * 40)
    
    if os.path.isfile(target_path):
        print(f"> Memvalidasi {target_path}...", flush=True)
        res = validate_file(target_path, args.llm, model)
        print_result(res)
    elif os.path.isdir(target_path):
        for root, dirs, files in os.walk(target_path):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    print(f"> Memvalidasi {file}...", flush=True)
                    res = validate_file(file_path, args.llm, model)
                    print_result(res)
