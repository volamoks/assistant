import uuid

class AgentSignatureMiddleware:
    """
    Middleware for tracking agent usage in LiteLLM dashboard.
    Tries to identify agent from: x-agent-id header, model name, or defaults to main-session.
    """
    
    async def __call__(self, request, call_next):
        # Try to get agent ID from header
        agent_id = request.headers.get("x-agent-id")
        
        # If not in header, try to infer from model name
        if not agent_id:
            # Get model from query params or body
            model = getattr(request, 'model', None) or request.query_params.get('model', '')
            
            # Map model names to agent identifiers
            model_lower = model.lower() if model else ''
            
            if 'coder' in model_lower:
                agent_id = 'coder'
            elif 'researcher' in model_lower:
                agent_id = 'researcher'
            elif 'analyst' in model_lower:
                agent_id = 'analyst'
            elif 'architect' in model_lower:
                agent_id = 'architect'
            elif 'cron' in model_lower:
                agent_id = 'cron-agent'
            elif 'main' in model_lower:
                agent_id = 'main-session'
            else:
                agent_id = 'default'
        
        # Set the user field for LiteLLM tracking
        request.user = agent_id
        
        return await call_next(request)
