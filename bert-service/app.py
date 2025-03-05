from fastapi import FastAPI, HTTPException
from transformers import AutoTokenizer, AutoModelForMaskedLM
import torch
import re

app = FastAPI()

# Use AutoTokenizer/AutoModel for more flexibility
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
model = AutoModelForMaskedLM.from_pretrained("bert-base-uncased")

@app.post("/expand")
async def expand_query(query: dict):
    try:
        # Extract the query text
        text = query.get("text", "")
        if not text:
            raise ValueError("Missing 'text' field in the request")
            
        # Get key terms from the query (simple approach: take non-stopwords)
        terms = [word for word in re.findall(r'\b\w+\b', text.lower()) 
                if len(word) > 3 and word not in ['with', 'that', 'this', 'from', 'what', 'have', 'your']]
        
        expanded_terms = []
        
        # For each significant term, find related terms using BERT
        for term in terms[:2]:  # Limit to top 2 terms to avoid too many expansions
            # Create a masked sequence
            masked_text = f"The term {term} is related to [MASK]."
            inputs = tokenizer(masked_text, return_tensors="pt", truncation=True)
            
            with torch.no_grad():
                outputs = model(**inputs)
            
            # Get predictions for the mask token
            mask_token_index = torch.where(inputs["input_ids"] == tokenizer.mask_token_id)[1].item()
            logits = outputs.logits
            top_3_tokens = torch.topk(logits[0, mask_token_index], 3).indices.tolist()
            
            # Decode tokens to text and add to expanded terms
            for token_id in top_3_tokens:
                token = tokenizer.decode([token_id]).strip()
                if token not in [term, ".", ","] and len(token) > 2:
                    expanded_terms.append(token)
        
        # Create expanded query by adding top terms
        expanded = text
        if expanded_terms:
            expanded += " " + " ".join(expanded_terms)
            
        return {"expanded_query": expanded, "expansion_terms": expanded_terms}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add a health endpoint
@app.get("/health")
async def health_check():
    # Respuesta completa que Weaviate espera
    return {"status": "ok"}  # Cambiar de "healthy" a "ok"