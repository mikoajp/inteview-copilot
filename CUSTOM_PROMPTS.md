# Custom System Prompts Guide

This guide explains how to use custom system prompts in Interview Copilot to tailor AI responses to your specific needs.

## Overview

By default, Interview Copilot uses a predefined system prompt optimized for Polish job interviews. However, you can now provide your own custom system prompt to:
- Change the response style and tone
- Adjust answer length
- Focus on specific industries or roles
- Use different languages
- Add specific instructions for AI behavior

## How It Works

When you provide a custom system prompt, it replaces the default prompt as the base instructions for the AI. Your interview context (CV, company, position) is automatically appended to your custom prompt.

### Default Prompt (Polish)

```
Jesteś ekspertem od rozmów rekrutacyjnych.

ZASADY:
- 2-4 zdania (zwięźle!)
- Konkretne przykłady
- Pozytywny ton
- Po polsku

TWOJE CV: [your CV]
FIRMA: [company name]
STANOWISKO: [position]
```

### Custom Prompt Example

```
You are an experienced software engineer preparing for a senior role interview.
Provide detailed technical answers with code examples when relevant.
Keep responses under 5 sentences. Focus on best practices and scalability.

TWOJE CV: [your CV]
FIRMA: [company name]
STANOWISKO: [position]
```

## Usage Examples

### REST API

#### Update Context with Custom Prompt

```bash
curl -X POST http://localhost:5000/api/context \
  -H "Content-Type: application/json" \
  -d '{
    "cv": "Senior Developer with 5 years experience...",
    "company": "Google",
    "position": "Senior Software Engineer",
    "custom_system_prompt": "You are a technical expert. Provide concise, technical answers with examples. Focus on system design and architecture."
  }'
```

#### Generate Answer with Custom Prompt

```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is your experience with microservices?",
    "context": {
      "cv": "...",
      "company": "Google",
      "position": "Senior Engineer",
      "custom_system_prompt": "Answer as a senior architect. Include specific technologies and patterns."
    },
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

#### Get Current Context

```bash
curl http://localhost:5000/api/context
```

Response:
```json
{
  "cv": "...",
  "company": "Google",
  "position": "Senior Engineer",
  "custom_system_prompt": "Your custom prompt here"
}
```

### WebSocket

#### Send Custom Prompt via WebSocket

```javascript
const ws = new WebSocket('ws://localhost:5000/ws/audio');

ws.onopen = () => {
  // Update context with custom prompt
  ws.send(JSON.stringify({
    type: 'context',
    data: {
      cv: 'Your CV...',
      company: 'Company Name',
      position: 'Position Title',
      custom_system_prompt: 'Your custom system prompt instructions...'
    }
  }));
};
```

## Custom Prompt Templates

### Technical Role (English)

```
You are a senior software engineer preparing for technical interviews.
Provide detailed answers with specific examples and technologies.
Include code snippets when relevant. Keep responses under 5 sentences.
Focus on best practices, scalability, and maintainability.
```

### Management Role (Polish)

```
Jesteś doświadczonym menedżerem IT przygotowującym się do rozmowy o stanowisko kierownicze.
Odpowiedzi powinny koncentrować się na zarządzaniu zespołem, strategii i procesach.
Podawaj konkretne przykłady z doświadczenia. Maksymalnie 4-5 zdań.
Zachowaj profesjonalny i pewny ton.
```

### Data Science Role (English)

```
You are a data scientist with expertise in machine learning and statistics.
Provide mathematically sound answers with specific algorithms and techniques.
Include metrics and evaluation methods. Keep responses concise (3-5 sentences).
Focus on practical applications and real-world scenarios.
```

### Sales Role (Polish)

```
Jesteś ekspertem sprzedaży z doświadczeniem w B2B.
Odpowiedzi powinny pokazywać umiejętności negocjacji i budowania relacji.
Używaj konkretnych liczb i wyników. Maksymalnie 3-4 zdania.
Podkreślaj orientację na klienta i osiąganie celów.
```

### Startup Environment (English)

```
You are a versatile engineer experienced in fast-paced startup environments.
Emphasize adaptability, quick learning, and wearing multiple hats.
Provide practical, hands-on examples. Keep responses brief (2-4 sentences).
Focus on impact and results rather than processes.
```

## Best Practices

### 1. Be Specific

❌ Bad:
```
Answer questions professionally.
```

✅ Good:
```
You are a senior DevOps engineer. Provide technical answers focusing on
CI/CD, infrastructure as code, and cloud platforms. Include specific tools
and technologies. Keep responses under 4 sentences.
```

### 2. Set Clear Constraints

```
- Response length: 2-4 sentences
- Language: English
- Technical level: Senior
- Include: Examples, metrics, specific technologies
- Avoid: Generic answers, buzzwords without substance
```

### 3. Match Your Industry

For **Finance**:
```
You are a financial analyst. Focus on regulatory compliance, risk management,
and quantitative analysis. Provide data-driven answers.
```

For **Healthcare**:
```
You are a healthcare IT professional. Emphasize patient privacy (HIPAA),
data security, and clinical workflow optimization.
```

### 4. Adjust for Interview Stage

**Phone Screen**:
```
Provide concise overview answers (2-3 sentences). Focus on key achievements
and relevant experience.
```

**Technical Deep Dive**:
```
Provide detailed technical explanations with code examples, architecture
diagrams description, and trade-offs analysis. 4-6 sentences.
```

## Tips

1. **Test Your Prompt**: Try different variations to see what works best
2. **Keep It Focused**: Don't try to cover everything in one prompt
3. **Update Per Interview**: Customize for each company and role
4. **Combine with Context**: Your CV, company, and position are automatically added
5. **Language Flexibility**: You can mix languages if needed (e.g., English instructions with Polish responses)

## Clearing Custom Prompt

To revert to the default prompt, send an empty string:

```bash
curl -X POST http://localhost:5000/api/context \
  -H "Content-Type: application/json" \
  -d '{
    "cv": "...",
    "company": "...",
    "position": "...",
    "custom_system_prompt": ""
  }'
```

## Advanced Usage

### Conditional Instructions

```
You are a full-stack developer.

If the question is about frontend: Focus on React, TypeScript, and UX.
If the question is about backend: Focus on Node.js, databases, and APIs.
If the question is about architecture: Focus on microservices and scalability.

Always include a specific example from real projects.
Keep responses under 4 sentences.
```

### Role-Specific Personality

```
You are a senior engineer known for:
- Clear communication (explain complex topics simply)
- Collaborative mindset (mention teamwork and mentoring)
- Problem-solving approach (describe your thought process)
- Continuous learning (show curiosity and growth)

Answer as if you're having a conversation with a peer.
```

## Troubleshooting

### Responses Too Long

Add explicit constraints:
```
Maximum 3 sentences. Be extremely concise.
```

### Responses Too Generic

Add specificity requirements:
```
Always include: specific technology names, concrete metrics, and real examples.
```

### Wrong Tone

Specify the desired tone:
```
Use a confident but humble tone. Be professional yet approachable.
```

## Security Note

- Never include sensitive information in system prompts
- Custom prompts are stored in session (in-memory by default)
- If using database mode, prompts are stored per user
- Prompts are not logged or shared

## Support

For questions or issues with custom prompts, please open an issue on GitHub.
