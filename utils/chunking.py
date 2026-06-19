import re
import json
import ollama

def chunk_text_intelligently(text, base_name, max_words=600):
    """
    Split text into chunks, then use Ollama to format the text specifically for Trading RAG.
    """
    words = text.split()
    chunks = []
    
    # Split by simple word count for flat texts
    for i in range(0, len(words), max_words):
        chunk_words = words[i:i + max_words]
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)
        
    atomic_notes = []
    
    prompt_template = """
Anda adalah asisten AI profesional untuk trader saham. 
Tugas Anda adalah mengekstrak, merangkum, dan merestrukturisasi potongan teks berikut menjadi 'Knowledge Summary' yang sangat terstruktur, komprehensif, namun mudah dibaca baik oleh manusia maupun AI.
Hasil ekstraksi ini akan digunakan untuk berbagai keperluan: 
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
  "rag_content": "## 🧠 Summary Knowledge (RAG & Analisa)\\n[Ringkasan inti yang padat dan komprehensif dari materi ini...]\\n\\n## 💡 Key Concept\\n[Penjelasan konsep utama, teori, atau strategi dasar...]\\n\\n## 🔍 Scanner & Alert Criteria\\n[Parameter teknikal/fundamental spesifik yang bisa diubah menjadi screener saham atau alert (misal: Harga > EMA 20, Volume membesar)...]\\n\\n## ✅ Trading Checklist\\n[Langkah-langkah atau syarat (SOP) yang harus dipenuhi sebelum entry/exit...]\\n\\n## 📓 Jurnal Evaluasi\\n[Poin-poin penting untuk bahan review/evaluasi trading di masa depan (kesalahan umum, psikologi, mitigasi risiko)...]\\n\\n## 📝 Original Context\\n[Kutipan penting atau konteks asli dari sumber...]"
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
            prompt = prompt_template.format(text_chunk=chunk[:2500])  # slightly larger limit
            
            print(f"\n⏳ Memproses chunk {idx+1} dari {len(chunks)} menggunakan AI...", flush=True)
            
            response = ollama.chat(model='llama3', messages=[
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
                    parsed_json = json.loads(json_match.group(0))
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
                tags = "\\n".join([f"#{t}" for t in tags_list]) + "\\n\\n"
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
