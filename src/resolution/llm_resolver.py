import os
import json
from ollama import Client
from typing import List
from src.core.models import ResolutionCandidate, LLMMatchDecision
from src.resolution.normalizer import normalize_name
from src.core.config import config

def resolve_candidates(candidates: List[ResolutionCandidate]) -> List[LLMMatchDecision]:
    decisions: List[LLMMatchDecision] = []
    
    # Load settings from config
    model_name = config['llm']['model_name']
    temperature = config['llm']['temperature']
    ollama_host = config['llm'].get('host', 'http://localhost:11434')
    
    # Initialize Ollama Client with API Key from environment
    api_key = os.environ.get('OLLAMA_API_KEY', '')
    client = Client(
        host=ollama_host,
        headers={'Authorization': f'Bearer {api_key}'} if api_key else {}
    )
    
    print(f"\n🧠 Starting LLM Resolution Phase for {len(candidates)} candidates using {model_name}...")
    
    for i, candidate in enumerate(candidates, 1):
        clean_messy = normalize_name(candidate.messy_name)
        print(f"   -> Sending BL {i} of {len(candidates)} to LLM (Name: '{candidate.messy_name}')...")
        
        # Provide the LLM with the CLEANED name to make its job easier
        system_prompt = """You are a master data analyst. Your job is to match a 'Cleaned Input Name' to the correct 'Master Account'.

RULES:
1. If the input name contains the Master Account name plus extra words (like 'LIMITED', 'PLC', 'NIGERIA'), IT IS A MATCH.
2. If the core entity brand is the same, IT IS A MATCH.
3. If they are different companies, return matched: false.

Output valid JSON matching the required schema. Ensure your 'reasoning' is uniquely descriptive for each choice. Do not just copy the examples."""
        
        try:
            response = client.chat(
                model=model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f"Cleaned Input Name: \"{clean_messy}\"\nMaster Candidates: {candidate.candidate_master_names}"}
                ],
                format=LLMMatchDecision.model_json_schema(),
                options={'temperature': temperature}
            )
            
            # The LLM evaluated the 'clean_messy', but we ensure the output saves the 'original_messy_name' for tracking
            decision = LLMMatchDecision(**json.loads(response['message']['content']))
            decision.original_messy_name = candidate.messy_name 
            decisions.append(decision)
            
        except Exception as e:
            decisions.append(LLMMatchDecision(
                original_messy_name=candidate.messy_name, 
                matched=False, 
                resolved_master_name=None, 
                confidence_score=0, 
                reasoning=f"LLM Error: {str(e)}"
            ))
            
    return decisions