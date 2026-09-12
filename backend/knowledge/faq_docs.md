# Goal-Stack Orchestrator Platform — Frequently Asked Questions

## What is Goal-Stack Orchestrator?

Goal-Stack Orchestrator is an enterprise-grade conversational AI platform that enables businesses to build AI-powered chatbots and virtual assistants. It supports over 135 languages and can be deployed across 35+ channels including web, mobile, WhatsApp, and voice. The platform serves enterprise customers across industries like banking, healthcare, retail, and telecom.

## What is the Orchestrator LLM (OrchLLM)?

The Orchestrator LLM is Goal-Stack Orchestrator's intelligent conversation management layer. It reads the entire conversation context, identifies user intents, and routes the conversation to the appropriate flow, tool, or knowledge base. Its key capability is handling multi-intent conversations — where a user might have multiple goals in a single conversation — and managing context switches between them.

## How does context switching work in Goal-Stack Orchestrator?

Context switching in Goal-Stack Orchestrator allows the AI agent to handle situations where a user changes topics mid-conversation. For example, if a user is booking a flight and suddenly asks about baggage policies, the Orchestrator LLM detects this topic change, routes to the appropriate handler for the new topic, and can later resume the original booking flow. The system maintains conversation context across these switches.

## What are the known limitations of OrchLLM?

The Orchestrator LLM has several documented limitations:

1. **No mother-child AI agent hierarchy support** — OrchLLM does not support parent-child delegation patterns where a supervisor agent decomposes tasks across subordinate agents.
2. **Goal nodes are excluded from switching logic** — The orchestrator's context-switching mechanism does not encompass goal-node hierarchies.
3. **Single-layer orchestration** — The system manages multi-intent conversations within a single conversational flow rather than through hierarchical agent structures.

These limitations mean that for complex, multi-step task delegation requiring hierarchical structures, users need to use Goal-Stack Orchestrator's multi-agent workflow capabilities instead.

## What channels does Goal-Stack Orchestrator support?

Goal-Stack Orchestrator supports deployment across 35+ channels including:
- **Messaging**: WhatsApp, Facebook Messenger, Telegram, Slack, Microsoft Teams
- **Web**: Website chat widgets, mobile app SDKs
- **Voice**: Phone/IVR systems, voice assistants
- **Email**: Automated email response handling
- **Social**: Instagram, Twitter/X DMs

## What is Goal-Stack Orchestrator's Dynamic Automation Platform (DAP)?

The Dynamic Automation Platform (DAP) is Goal-Stack Orchestrator's core technology stack. It combines:
- **NLU Engine**: Natural language understanding for intent detection and entity extraction
- **Orchestrator LLM**: Intelligent conversation routing and context management
- **Knowledge Base**: Enterprise document ingestion and retrieval for grounded AI responses
- **Workflow Builder**: Visual drag-and-drop interface for creating conversation flows
- **Analytics Dashboard**: Real-time monitoring of bot performance, user satisfaction, and conversation metrics

## How does Goal-Stack Orchestrator handle multiple intents in a single message?

When a user sends a message containing multiple intents (e.g., "Book me a flight to London and also tell me about visa requirements"), the Orchestrator LLM:
1. Identifies all intents present in the message
2. Prioritizes them based on conversation context and business rules
3. Routes to the most relevant handler first
4. Queues the secondary intent for follow-up after the primary intent is resolved

## What makes Goal-Stack Orchestrator different from other chatbot platforms?

Key differentiators include:
- **Enterprise focus**: Built for large-scale deployments with SOC 2, GDPR, and HIPAA compliance
- **Multilingual**: Native support for 135+ languages without translation layers
- **Orchestrator LLM**: Unique conversation management layer that goes beyond simple intent matching
- **Hybrid AI**: Combines LLM capabilities with deterministic workflow automation for predictable, auditable outcomes
- **Zero-shot learning**: Ability to handle new intents without explicit training data, powered by LLM understanding

