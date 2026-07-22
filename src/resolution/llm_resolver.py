import os
import json
import time
from ollama import Client
from typing import List
from src.core.models import ResolutionCandidate, LLMMatchDecision
from src.resolution.normalizer import normalize_name
from src.core.config import config

def _resolve_with_gemini(candidates: List[ResolutionCandidate]) -> List[LLMMatchDecision]:
    from google import genai
    decisions: List[LLMMatchDecision] = []
    model_name = config['llm'].get('gemini', {}).get('model_name', 'gemini-2.5-flash')
    
    # Initialize Gemini Client (automatically picks up GEMINI_API_KEY from environment)
    client = genai.Client()
    
    print(f"\n🧠 Starting LLM Resolution Phase for {len(candidates)} candidates using Gemini ({model_name})...")
    
    for i, candidate in enumerate(candidates, 1):
        clean_messy = normalize_name(candidate.messy_name)
        print(f"   -> Sending BL {i} of {len(candidates)} to Gemini (Name: '{candidate.messy_name}')...")
        
        system_prompt = """You are a master data analyst. Your job is to match a 'Cleaned Input Name' to the correct 'Master Account'.

RULES:
1. If the input name contains the Master Account name plus extra words (like 'LIMITED', 'PLC', 'NIGERIA'), IT IS A MATCH.
2. If the core entity brand is the same, IT IS A MATCH.
3. If they are different companies, return matched: false.

Output strictly valid JSON matching the schema for LLMMatchDecision. Do NOT include markdown code blocks like ```json."""
        
        prompt = f"{system_prompt}\n\nCleaned Input Name: \"{clean_messy}\"\nMaster Candidates: {candidate.candidate_master_names}"
        
        try:
            interaction = client.interactions.create(
                model=model_name,
                input=prompt
            )
            
            # Clean up the output in case the model returns markdown formatting
            output_text = interaction.output_text.strip()
            if output_text.startswith("```json"):
                output_text = output_text[7:]
            if output_text.startswith("```"):
                output_text = output_text[3:]
            if output_text.endswith("```"):
                output_text = output_text[:-3]
                
            decision = LLMMatchDecision(**json.loads(output_text.strip()))
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
            
        # Rate limiting: wait 4 seconds between requests to avoid free tier 15 RPM limits
        if i < len(candidates):
            time.sleep(4)
            
    return decisions

def _resolve_with_ollama(candidates: List[ResolutionCandidate]) -> List[LLMMatchDecision]:
    decisions: List[LLMMatchDecision] = []
    
    # Load settings from config
    model_name = config['llm']['ollama']['model_name']
    temperature = config['llm']['temperature']
    ollama_host = config['llm']['ollama'].get('host', 'https://ollama.com')
    
    # Initialize Ollama Client with API Key from environment
    api_key = os.environ.get('OLLAMA_API_KEY', '')
    client = Client(
        host=ollama_host,
        headers={'Authorization': f'Bearer {api_key}'} if api_key else {}
    )
    
    print(f"\n🧠 Starting LLM Resolution Phase for {len(candidates)} candidates using Ollama ({model_name})...")
    
    for i, candidate in enumerate(candidates, 1):
        clean_messy = normalize_name(candidate.messy_name)
        print(f"   -> Sending BL {i} of {len(candidates)} to LLM (Name: '{candidate.messy_name}')...")
        
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

def resolve_candidates(candidates: List[ResolutionCandidate]) -> List[LLMMatchDecision]:
    provider = config['llm'].get('provider', 'gemini')
    if provider == 'gemini':
        return _resolve_with_gemini(candidates)
    else:
        return _resolve_with_ollama(candidates)