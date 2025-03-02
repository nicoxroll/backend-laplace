from fastapi import FastAPI, HTTPException
from transformers import BertForMaskedLM, BertTokenizer
import torch

app = FastAPI()

# Cargar modelo
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertForMaskedLM.from_pretrained('bert-base-uncased')

@app.post("/expand")
async def expand_query(query: dict):
    try:
        inputs = tokenizer(query["text"], return_tensors="pt", truncation=True)
        with torch.no_grad():
            outputs = model(**inputs)
        
        # Lógica de expansión...
        expanded = query["text"] + " optimized code python performance"
        
        return {"expanded_query": expanded}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))