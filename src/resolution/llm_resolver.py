import os
import json
import time
from ollama import Client
from typing import List
from tenacity import retry, wait_exponential, stop_after_attempt
from src.core.models import ResolutionCandidate, LLMMatchDecision
from src.resolution.normalizer import normalize_name
from src.core.config import config

@retry(wait=wait_exponential(multiplier=2, min=5, max=60), stop=stop_after_attempt(5))
def _call_gemini_with_retry(client, model_name, prompt):
    # Automatically retries if an exception (like 429 Quota Exceeded) is raised
    return client.models.generate_content(
        model=model_name,
        contents=prompt
    )

def _resolve_with_gemini(candidates: List[ResolutionCandidate]) -> List[LLMMatchDecision]:
    from google import genai
    decisions: List[LLMMatchDecision] = []
    model_name = config['llm'].get('gemini', {}).get('model_name', 'gemini-3.6-flash')
    
    # Initialize Gemini Client (automatically picks up GEMINI_API_KEY from environment)
    client = genai.Client()
    
    print(f"\n🧠 Starting LLM Resolution Phase for {len(candidates)} candidates using Gemini ({model_name})...")
    
    for i, candidate in enumerate(candidates, 1):
        clean_messy = normalize_name(candidate.messy_name)
        print(f"   -> Sending BL {i} of {len(candidates)} to Gemini (Name: '{candidate.messy_name}')...")
        
        system_prompt = f"""You are a master data analyst. Your job is to match a 'Cleaned Input Name' to the correct 'Master Account'.

RULES:
1. If the input name contains the Master Account name plus extra words (like 'LIMITED', 'PLC', 'NIGERIA'), IT IS A MATCH.
2. If the core entity brand is the same, IT IS A MATCH.
3. If they are different companies, return matched: false.

Output strictly valid JSON matching this exact schema:
{json.dumps(LLMMatchDecision.model_json_schema(), indent=2)}

Do NOT include markdown code blocks like ```json."""
        
        prompt = f"{system_prompt}\n\nCleaned Input Name: \"{clean_messy}\"\nMaster Candidates: {candidate.candidate_master_names}"
        
        try:
            response = _call_gemini_with_retry(client, model_name, prompt)
            
            # Clean up the output in case the model returns markdown formatting
            output_text = (response.text or "").strip()
            if output_text.startswith("```json"):
                output_text = output_text[7:]
            if output_text.startswith("```"):
                output_text = output_text[3:]
            if output_text.endswith("```"):
                output_text = output_text[:-3]
                
            data = json.loads(output_text.strip())
            
            # 1. Safely inject the required original_messy_name BEFORE Pydantic validation
            data['original_messy_name'] = candidate.messy_name
            
            # 2. Safely cast confidence_score to integer (e.g. 0.95 -> 95)
            if 'confidence_score' in data:
                try:
                    score = float(data['confidence_score'])
                    if 0 < score <= 1.0:
                        data['confidence_score'] = int(score * 100)
                    else:
                        data['confidence_score'] = int(score)
                except ValueError:
                    data['confidence_score'] = 0
            else:
                data['confidence_score'] = 0
                
            decision = LLMMatchDecision(**data)
            decisions.append(decision)
            
        except Exception as e:
            decisions.append(LLMMatchDecision(
                original_messy_name=candidate.messy_name, 
                matched=False, 
                resolved_master_name=None, 
                confidence_score=0, 
                reasoning=f"LLM Error: {str(e)}"
            ))
            
        # Polite baseline delay
        if i < len(candidates):
            time.sleep(2)
            
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