"""
Ollama client for Language Coach
Handles communication with local Ollama instance
"""
import httpx
import json
import time
from typing import Dict, Any, Optional
from config import settings


class OllamaClient:
    """Client for interacting with Ollama API"""
    
    def __init__(
        self,
        base_url: str = None,
        model_name: str = None,
        timeout: int = 120,
        max_retries: int = 3
    ):
        self.base_url = base_url or settings.ollama_url
        self.model_name = model_name or settings.model_name
        self.timeout = timeout
        self.max_retries = max_retries
    
    def _make_request(
        self,
        endpoint: str,
        data: Dict[str, Any],
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Make HTTP request to Ollama with retry logic"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=data)
                response.raise_for_status()
                
                # Parse streaming response
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if 'response' in chunk:
                                full_response += chunk['response']
                            if chunk.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue
                
                return {"response": full_response, "success": True}
        
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count  # Exponential backoff
                print(f"Request failed, retrying in {wait_time}s... (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(wait_time)
                return self._make_request(endpoint, data, retry_count + 1)
            else:
                return {
                    "response": "",
                    "success": False,
                    "error": f"Connection failed after {self.max_retries} retries: {str(e)}"
                }
        
        except Exception as e:
            return {
                "response": "",
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        format: str = "json",
        model: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate response from Ollama with caching
        """
        target_model = model or self.model_name
        
        # Check cache if enabled
        if use_cache:
            from cache import cache
            import hashlib
            cache_key = f"ollama:{target_model}:{hashlib.md5((prompt + (system_prompt or '')).encode()).hexdigest()}"
            cached_res = cache.get(cache_key)
            if cached_res:
                return cached_res

        data = {
            "model": target_model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        
        if system_prompt:
            data["system"] = system_prompt
        
        if format == "json":
            data["format"] = "json"
        
        result = self._make_request("api/generate", data)
        
        # Save to cache if successful
        if use_cache and result.get('success'):
            from cache import cache
            cache.set(cache_key, result)
            
        return result
    
    def check_model_availability(self) -> bool:
        """Check if the configured model is available"""
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get('models', [])
                
                # Check if our model exists
                model_names = [m.get('name', '') for m in models]
                return any(self.model_name in name for name in model_names)
        
        except Exception as e:
            print(f"Failed to check model availability: {e}")
            return False
    
    def parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON response from Ollama, handling potential formatting issues
        
        Args:
            response_text: Raw response text
        
        Returns:
            Parsed JSON dict or None if parsing fails
        """
        # Try direct parsing first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        if "```json" in response_text:
            try:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Try to find JSON object in text
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
        
        return None


# Global Ollama client instance
ollama_client = OllamaClient()
