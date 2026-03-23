# Research Agent LLM Orchestration Design

**Model:** Anthropic Claude `claude-sonnet-4-6`  
**Tool:** Tavily Search API  
**Goal:** Given a user topic → sub-questions → search → read/summarize → structured Markdown report with citations

---

## 1. Step-by-Step Algorithm

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: PLANNING                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  1.1  Receive user topic                                                     │
│  1.2  LLM call (no tools): Decompose topic into 3–7 sub-questions            │
│       - Output: ResearchPlan (JSON)                                          │
│       - Sub-questions should be specific, searchable, non-overlapping         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 2: SEARCH (Tool Loop)                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  2.1  For each sub-question in plan:                                         │
│       - Call tavily_search(query=sub_question, max_results=5–8)               │
│       - Store results with source metadata (url, title, content, score)        │
│  2.2  Optional: Refine queries if results are sparse (retry with rephrased)   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 3: READ & SUMMARIZE                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  3.1  For each sub-question + its search results:                             │
│       - LLM summarizes findings, extracts key facts, quotes                   │
│       - Maps each fact/quote → source URL (citation mapping)                 │
│  3.2  Output: SubQuestionSummary[] with citations                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 4: SYNTHESIZE REPORT                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  4.1  Single LLM call with full context:                                     │
│       - Input: Topic, all SubQuestionSummary[], citation map                  │
│       - Output: Structured Markdown report                                    │
│  4.2  Report structure:                                                      │
│       - Executive Summary                                                     │
│       - Sections per sub-question (or thematic grouping)                     │
│       - Inline citations [1], [2], …                                          │
│       - References section (numbered list of URLs)                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 5: VALIDATION                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  5.1  Verify every [N] in report maps to a valid URL in References             │
│  5.2  Verify no orphan URLs (URLs in References not cited in body)            │
│  5.3  Optional: Re-run synthesis if validation fails                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tool Schema: `tavily_search`

### Anthropic Messages API Tool Definition

```json
{
  "name": "tavily_search",
  "description": "Search the web for information using the Tavily API. Use this to find current, factual information on any topic. Returns a list of results with title, URL, content snippet, and relevance score. Call once per distinct search query.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The search query. Be specific and include key terms. Use natural language questions or keyword phrases."
      },
      "max_results": {
        "type": "integer",
        "description": "Maximum number of results to return (1-20). Default 5 for focused research, 8 for broader coverage.",
        "default": 5,
        "minimum": 1,
        "maximum": 20
      }
    },
    "required": ["query"]
  }
}
```

### Tavily API Mapping

| Tool param   | Tavily API param | Notes                                      |
|-------------|------------------|--------------------------------------------|
| `query`     | `query`          | Direct mapping                             |
| `max_results` | `max_results`  | 1–20; recommend 5–8 per sub-question       |

**Optional extensions** (if backend supports):
- `search_depth`: `"basic"` (fast) vs `"advanced"` (richer content)
- `topic`: `"general"` vs `"news"` for time-sensitive topics
- `time_range`: `"week"` | `"month"` | `"year"` for recency

### Example Tool Call (Claude → Backend)

```json
{
  "type": "tool_use",
  "id": "toolu_01ABC123",
  "name": "tavily_search",
  "input": {
    "query": "What are the main benefits of RAG for enterprise search?",
    "max_results": 6
  }
}
```

### Example Tool Result (Backend → Claude)

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_01ABC123",
  "content": "{\"query\": \"What are the main benefits of RAG for enterprise search?\", \"results\": [{\"title\": \"RAG Benefits for Enterprise\", \"url\": \"https://example.com/rag-benefits\", \"content\": \"RAG improves accuracy by grounding responses in company documents...\", \"score\": 0.92}, {\"title\": \"Enterprise Search with RAG\", \"url\": \"https://example.com/enterprise-rag\", \"content\": \"Key benefits include reduced hallucinations, up-to-date knowledge...\", \"score\": 0.88}]}"
}
```

---

## 3. Prompting Strategy

### 3.1 System Prompt (Research Agent)

```
You are a Research Agent that produces well-sourced, structured reports. Your workflow:

1. **Planning**: Break the user's topic into 3–7 specific, non-overlapping sub-questions that are good search queries.
2. **Search**: Use the tavily_search tool for each sub-question. Call the tool once per sub-question with a clear, specific query.
3. **Summarize**: For each sub-question, extract key facts and map each fact to its source URL.
4. **Synthesize**: Produce a Markdown report with inline citations [1], [2], etc., and a References section listing all URLs.

**Citation rules:**
- Every factual claim must have at least one citation.
- Use numbered citations [1], [2], [3] in the text.
- Each number maps to exactly one URL in the References section.
- Include short quote snippets where they add credibility (use "quoted text" [N]).
- Do not invent sources; only cite URLs returned by tavily_search.

**Output format:**
- Executive Summary (2–4 sentences)
- Sections with clear headings (## or ###)
- Inline citations after claims: "According to X, ... [1]."
- References section at end: ## References\n\n1. [Title](URL)\n2. ...
```

### 3.2 User Prompt (Initial)

```
Research the following topic and produce a structured Markdown report with citations:

**Topic:** {user_topic}

Please:
1. Break this into sub-questions and search for each.
2. Summarize findings with source attribution.
3. Synthesize a final report with numbered citations and a References section.
```

### 3.3 Tool Result Handling

**When returning search results to Claude:**

1. **Format for readability**: Present results as structured text or JSON so Claude can parse URLs and content easily.
2. **Include metadata**: Always pass `url`, `title`, `content` (snippet), and optionally `score`.
3. **Truncate if needed**: If total content exceeds context limits, truncate per-result `content` to ~500 chars and keep URLs.
4. **Explicit numbering**: Pre-number results so Claude can reference them: `[1] https://...`, `[2] https://...`.

**Example formatted tool result (for Claude):**

```
Search results for "What are the main benefits of RAG?":

[1] https://example.com/rag-benefits
Title: RAG Benefits for Enterprise
Content: RAG improves accuracy by grounding responses in company documents. It reduces hallucinations and keeps knowledge up-to-date without retraining.

[2] https://example.com/enterprise-rag
Title: Enterprise Search with RAG
Content: Key benefits include reduced hallucinations, up-to-date knowledge, and lower training costs...
```

### 3.4 Synthesis Prompt (Phase 4)

```
You have gathered the following research for the topic "{topic}":

{SubQuestionSummary_1}
Sources: [1] url1, [2] url2, ...

{SubQuestionSummary_2}
Sources: [3] url3, [4] url4, ...

...

**Task:** Write a cohesive Markdown report that:
1. Opens with an Executive Summary.
2. Organizes content into logical sections (by sub-question or theme).
3. Cites every factual claim with [N] where N maps to the References list.
4. Ends with ## References: a numbered list of [Title](URL) for each source used.

Use only the sources provided. Do not add uncited information.
```

---

## 4. Citation Strategy

### 4.1 Numbered Citations with URL List

- **Format**: `[1]`, `[2]`, `[3]` in text → `1. [Title](URL)` in References.
- **Order**: References ordered by first appearance in the report.
- **Uniqueness**: Each URL appears once; reuse the same number if cited multiple times.

### 4.2 Quote Snippets

- Use for key statistics, definitions, or authoritative statements.
- Format: `"Exact quote from source" [N]`
- Keep quotes short (1–2 sentences max).

### 4.3 Section-to-Source Mapping

Maintain an intermediate structure:

```json
{
  "section_id": "sub_q_1",
  "section_title": "Benefits of RAG",
  "claims": [
    {
      "claim": "RAG reduces hallucinations by grounding responses in documents.",
      "citation_ids": [1, 2],
      "quote": "RAG improves accuracy by grounding responses in company documents"
    }
  ]
}
```

### 4.4 Validation Rules

| Rule | Description |
|------|-------------|
| **No uncited facts** | Every factual claim has ≥1 citation |
| **No orphan refs** | Every [N] in References is cited in the body |
| **URL integrity** | All cited URLs were returned by tavily_search |
| **Quote accuracy** | Quotes are verbatim or clearly paraphrased |

---

## 5. Error Handling & Retries

### 5.1 Tavily API Errors

| Error | Action |
|-------|--------|
| **429 Rate limit** | Exponential backoff: 2s, 4s, 8s; max 3 retries |
| **500 / 503** | Retry up to 2 times with 5s delay |
| **401 / 403** | Fail fast; do not retry (auth/config issue) |
| **Timeout** | Retry once; if fail, continue with partial results |
| **Empty results** | Proceed; LLM can note "limited sources found" |

### 5.2 LLM / Tool Loop Errors

| Scenario | Action |
|----------|--------|
| **Claude returns no tool_use** | Re-prompt: "Please use tavily_search to find information for each sub-question." |
| **Invalid tool input** | Return error in tool_result; Claude may self-correct |
| **Max tool calls exceeded** | Stop search phase; synthesize with available results |
| **Context overflow** | Summarize/truncate oldest results; keep URLs and key facts |

### 5.3 Retry Configuration

```json
{
  "tavily_retries": 3,
  "tavily_backoff_base_seconds": 2,
  "llm_retries": 1,
  "max_tool_calls_per_turn": 10,
  "max_total_tool_calls": 30
}
```

---

## 6. Recommended JSON Structures

### 6.1 ResearchPlan (Phase 1)

```json
{
  "topic": "User-provided research topic",
  "sub_questions": [
    {
      "id": "sq_1",
      "question": "Specific searchable sub-question 1",
      "rationale": "Why this sub-question matters for the report"
    },
    {
      "id": "sq_2",
      "question": "Specific searchable sub-question 2",
      "rationale": "Why this sub-question matters"
    }
  ],
  "created_at": "2025-03-16T12:00:00Z"
}
```

### 6.2 SearchQueries (Phase 2 – optional intermediate)

```json
{
  "plan_id": "plan_abc123",
  "queries": [
    {
      "sub_question_id": "sq_1",
      "query": "Exact query sent to tavily_search",
      "max_results": 5,
      "tool_call_id": "toolu_01ABC"
    }
  ]
}
```

### 6.3 SearchResults (Phase 2 output)

```json
{
  "sub_question_id": "sq_1",
  "query": "Query used",
  "results": [
    {
      "citation_id": 1,
      "url": "https://example.com/page",
      "title": "Page Title",
      "content": "Snippet or extracted content",
      "score": 0.92
    }
  ],
  "total_count": 5
}
```

### 6.4 Citations (canonical mapping)

```json
{
  "citations": [
    {
      "id": 1,
      "url": "https://example.com/page1",
      "title": "Page Title",
      "used_in_sections": ["sq_1", "sq_2"]
    }
  ]
}
```

### 6.5 SubQuestionSummary (Phase 3)

```json
{
  "sub_question_id": "sq_1",
  "section_title": "Benefits of RAG",
  "summary": "2-4 sentence summary of findings",
  "key_facts": [
    {
      "fact": "RAG reduces hallucinations.",
      "citation_ids": [1, 2],
      "quote": "Optional verbatim quote"
    }
  ],
  "sources": [
    {"id": 1, "url": "https://...", "title": "..."}
  ]
}
```

### 6.6 FinalReport (Phase 4)

```json
{
  "topic": "Original topic",
  "executive_summary": "2-4 sentence overview",
  "sections": [
    {
      "heading": "## Section Title",
      "content": "Markdown body with [1], [2] citations..."
    }
  ],
  "references": [
    {"id": 1, "title": "Source Title", "url": "https://..."}
  ],
  "raw_markdown": "# Full report as single Markdown string",
  "generated_at": "2025-03-16T12:30:00Z"
}
```

---

## 7. Flow Summary

| Phase | LLM Calls | Tool Calls | Output |
|-------|-----------|------------|--------|
| 1. Planning | 1 | 0 | ResearchPlan |
| 2. Search | 1 (orchestrator) | N (one per sub-question) | SearchResults[] |
| 3. Summarize | 1 (or N for parallel) | 0 | SubQuestionSummary[] |
| 4. Synthesize | 1 | 0 | FinalReport (Markdown) |
| 5. Validate | 0 (deterministic) | 0 | Pass/Fail + fixes |

**Total**: ~4 LLM turns, N tool calls (N = number of sub-questions).

---

## 8. Optional: Deeper Content Reading (Tavily Extract)

For sub-questions where search snippets are insufficient, add a second tool:

```json
{
  "name": "tavily_extract",
  "description": "Extract full page content from URLs. Use when search snippets are too short to answer the question.",
  "input_schema": {
    "type": "object",
    "properties": {
      "urls": {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of URLs to extract content from (max 5 per call)"
      }
    },
    "required": ["urls"]
  }
}
```

Flow: `tavily_search` → if snippet insufficient → `tavily_extract` for top 2–3 URLs → summarize.

---

## 9. Implementation Notes

- **Single vs multi-turn**: Can be single long conversation (Claude decides when to call tools) or explicit phases with separate LLM calls.
- **Streaming**: For UX, stream the final synthesis; planning and search can be non-streaming.
- **Token budget**: Reserve ~4K tokens for tool results per sub-question; cap total context.
- **Claude model**: `claude-sonnet-4-6` supports tool use; ensure `tools` and `tool_choice` (or equivalent) are set in the API request.
