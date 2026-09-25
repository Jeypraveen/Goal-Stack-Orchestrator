# Jps.ai Platform - Frequently Asked Questions

Jps.ai is a conversational AI demo inspired by Yellow.ai's Orchestrator LLM. It demonstrates how to manage complex conversation state using a goal-stack architecture.

## What is the Orchestrator LLM (Jps LLM)?

The Orchestrator LLM (Jps LLM) is a core component of this multi-agent architecture demo. It acts as the central router that receives every user message, analyzes the intent against the current goal stack, and delegates execution to specialized sub-agents (like the Booking Agent or FAQ Agent). It uses a large parameter model for zero-shot decision making.

Unlike traditional flow-based systems, Jps LLM dynamically manages state as a stack-allowing it to handle mid-conversation interruptions, out-of-bounds questions, and resumption natively.

## What are the known limitations of Jps LLM?

Jps LLM is highly capable, but currently has two known limitations:

1. **No mother-child AI agent hierarchy support** - Jps LLM does not support parent-child delegation patterns where a supervisor agent decomposes tasks across subordinate agents.
2. **Deterministic execution boundaries** - While Jps LLM handles the intent routing, the actual state transition is handled by a deterministic orchestrator loop. Agents cannot recursively call other agents; they must yield control back to the central router.
3. **Single-layer orchestration** - The system manages multi-intent conversations within a single conversational flow rather than through hierarchical agent structures.

These limitations mean that for complex, multi-step task delegation requiring hierarchical structures, users need to use Jps.ai's multi-agent workflow capabilities instead.

## What channels does Jps.ai support?

Jps.ai supports deployment across 35+ channels including:
- **Messaging**: WhatsApp, Facebook Messenger, Telegram, Slack, Microsoft Teams
- **Web**: Website chat widgets, mobile app SDKs
- **Voice**: Phone/IVR systems, voice assistants
- **Email**: Automated email response handling
- **Social**: Instagram, Twitter/X DMs

## What is Jps.ai's Dynamic Automation Platform (DAP)?

The Dynamic Automation Platform (DAP) is Jps.ai's core technology stack. It combines:
- **NLU Engine**: Natural language understanding for intent detection and entity extraction
- **Orchestrator LLM**: Intelligent conversation routing and context management
- **Knowledge Base**: Enterprise document ingestion and retrieval for grounded AI responses
- **Workflow Builder**: Visual drag-and-drop interface for creating conversation flows
- **Analytics Dashboard**: Real-time monitoring of bot performance, user satisfaction, and conversation metrics

## How does Jps.ai handle multiple intents in a single message?

When a user sends a message containing multiple intents (e.g., "Book me a flight to London and also tell me about visa requirements"), the Orchestrator LLM:
1. Identifies all intents present in the message
2. Prioritizes them based on conversation context and business rules
3. Routes to the most relevant handler first
4. Queues the secondary intent for follow-up after the primary intent is resolved

## What makes Jps.ai different from other chatbot platforms?

Key features demonstrated include:
- **Goal-Stack Architecture**: Handles non-linear conversations.
- **Orchestrator LLM**: Unique conversation management layer that goes beyond simple intent matching.
- **Hybrid AI**: Combines LLM capabilities with deterministic workflow automation.
- **Zero-shot learning**: Ability to handle new intents without explicit training data, powered by LLM understanding.

