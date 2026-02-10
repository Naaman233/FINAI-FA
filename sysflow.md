           ┌───────────────┐
           │   User Query  │
           └───────┬───────┘
                   │
                   ▼
      ┌───────────────────────────┐
      │  Multi-Label Intent       │
      │  Detection (HF API)       │
      │  Model: bart-large-mnli   │
      │  Output: List of intents  │
      └─────────┬─────────────────┘
                │
                ▼
       ┌─────────────────────┐
       │  Route Intents       │
       │  (summarize,         │
       │   generate_insight,  │
       │   financial_query)   │
       └─────────┬───────────┘
                 │
        ┌────────┴─────────┐
        │                  │
        ▼                  ▼
 ┌───────────────┐  ┌────────────────┐
 │ Fetch Financial│  │  Fallback      │
 │  Context      │  │  Response       │
 │  (data.xlsx)  │  │  Non-finance    │
 └───────────────┘  │  Questions      │
        │            └───────────────┘
        ▼
 ┌─────────────────────────┐
 │  LLM Response Generation │
 │  Model: gpt-4-turbo      │
 │  Input: user query +     │
 │         financial context│
 └─────────┬───────────────┘
           │
           ▼
     ┌─────────────┐
     │  Cache LLM  │
     │  Responses  │
     └─────┬───────┘
           │
           ▼
     ┌─────────────┐
     │  Final      │
     │  Response   │
     │  to User    │
     └─────────────┘
