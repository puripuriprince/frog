
API request form

POST /v1/agents/chat HTTP/1.1
Host: api.frog.ai
Authorization: Bearer sk-frog_live_••••••••       # <-- account-level API key
Content-Type: application/json

{
  /* REQUIRED */
  "model": "openai/gpt-4o-mini",

  /* OPTIONAL — one of the three ↓ takes precedence, in this order  */
  "workflow_id": null,               // 1 run a cached/hosted workflow
  "workflow": null,                  // 2️ ad-hoc inline JSON spec
  /* neither present → 3 auto-plan with Planner base agent*/

  /* OPTIONAL */
  "tools": ["browser.search", "python.exec", "mcptool:endpointwhenlocal"], // maybe specify limits here or have them linked to the account

  "messages": [
    { "role": "user", "content": "Summarise latest Nvidia 10-K." }
  ],

  /* OPTIONAL */
  "stream": true
}

