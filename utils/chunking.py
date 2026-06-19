import re
import json
import ollama

def chunk_text_intelligently(text, base_name, max_words=600, model_name='llama3'):
    """
    Split text into chunks, then use Ollama to format the text specifically for Trading RAG.
    """
    lines = text.splitlines(keepends=True)
    chunks = []
    current_chunk = ""
    current_words = 0
    
    # Split by lines to preserve original markdown formatting and newlines
    for line in lines:
        word_count = len(line.split())
        if current_words + word_count > max_words and current_words > 0:
            chunks.append(current_chunk)
            current_chunk = line
            current_words = word_count
        else:
            current_chunk += line
            current_words += word_count
            
    if current_chunk:
        chunks.append(current_chunk)
        
    atomic_notes = []
    
    prompt_template = """
Anda adalah asisten AI profesional spesialis ekstraksi informasi dan knowledge management.
Tugas Anda adalah mengekstrak, merangkum, dan merestrukturisasi potongan teks berikut menjadi 'Knowledge Summary' yang sangat terstruktur, komprehensif, namun mudah dibaca baik oleh manusia maupun AI.
Hasil ekstraksi ini akan digunakan sebagai basis data untuk sistem Retrieval-Augmented Generation (RAG).

KHUSUS JIKA TEKS BERKAITAN DENGAN SAHAM/TRADING: 
Pastikan hasil ekstraksi Anda dioptimalkan (melalui Header Dinamis) untuk keperluan berikut:
1. Tanya Jawab (RAG)
2. Membuat Scanner Saham
3. Membuat Alert Trading
4. Bahan Analisa Saham
5. Checklist Trading
6. Jurnal Evaluasi Trading

Format jawaban Anda HANYA dalam bentuk JSON valid tanpa teks tambahan di luar JSON.

Struktur JSON yang diharapkan:
{{
  "filename_slug": "kata-kunci-pendek-maks-3-kata",
  "tags": ["tag1", "tag2"],
  "rag_content": "## 🧠 Core Summary\\n[Ringkasan inti yang padat dan komprehensif dari materi ini...]\\n\\n## 💡 Key Concepts & Definitions\\n[Penjelasan konsep utama, teori, istilah, atau ide dasar...]\\n\\n## 📌 Important Details / Application\\n[Rincian penting, studi kasus, pedoman, atau penerapan praktis dari materi...]\\n\\n## [TAMBAHKAN 1 ATAU 2 HEADER DINAMIS SESUAI KONTEKS, misal: 💻 Code Snippets, 🥘 Ingredients, 📈 Trading Setup, ⏳ Timeline, dll]\\n[Isi dari header dinamis tersebut...]\\n\\n## 📝 Original Context & Quotes\\n[Kutipan penting, pesan moral, atau konteks asli dari sumber...]"
}}

Teks mentah:
{text_chunk}
"""
    
    for idx, chunk in enumerate(chunks):
        filename = f"{base_name}-part-{idx+1}.md"
        formatted_content = chunk
        tags = ""
        
        try:
            # Prompt the local LLM
            prompt = prompt_template.replace("{text_chunk}", chunk[:2500])  # slightly larger limit
            
            print(f"\n⏳ Memproses chunk {idx+1} dari {len(chunks)} menggunakan AI ({model_name})...", flush=True)
            
            response = ollama.chat(model=model_name, messages=[
                {'role': 'user', 'content': prompt}
            ], format='json', stream=True)
            
            response_text = ""
            for chunk_resp in response:
                content = chunk_resp['message']['content']
                response_text += content
                print(content, end='', flush=True)
            
            print("\n✅ Selesai memproses chunk.")
            
            # Since we forced format='json', we should be able to parse it directly
            try:
                parsed_json = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback regex if LLM still wraps in markdown blocks
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        parsed_json = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        raise Exception("Regex matched but still not valid JSON")
                else:
                    raise Exception("Valid JSON not found in LLM response")
            
            # Extract filename
            slug = parsed_json.get("filename_slug", "")
            slug = re.sub(r'[^a-zA-Z0-9\s-]', '', slug).strip().lower()
            slug = re.sub(r'[\s]+', '-', slug)
            if slug:
                filename = f"{base_name}-{slug}.md"
            
            # Extract content
            rag_content = parsed_json.get("rag_content", "")
            if rag_content.strip():
                formatted_content = rag_content
            
            # Extract tags
            tags_list = parsed_json.get("tags", [])
            if tags_list and isinstance(tags_list, list):
                tags = "\n".join([f"#{t}" for t in tags_list]) + "\n\n"
                formatted_content = tags + formatted_content
                
        except Exception as e:
            # Fallback if parsing fails or Ollama is off
            print(f"Warning: Chunk {idx+1} failed AI processing ({str(e)}). Using raw text.")
            # We don't 'pass' here, we just let it use the fallback formatted_content (raw chunk)

            
        atomic_notes.append({
            "filename": filename,
            "content": formatted_content
        })
        
    return atomic_notes
