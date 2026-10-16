# Presentation Website Scope & Architectural Boundaries

> **V1 Specification Status: FROZEN**  
> An optional static presentation website may accompany SENTRON. This document defines the strict architectural boundaries and scope limitations for that website.

---

## 1. Role of the Website

The website is strictly an **educational presentation and documentation layer**. It is **NOT** the SENTRON protection engine.

- **Purpose**: Present product concepts, architecture diagrams, user guides, team information, and interactive static demonstrations.
- **Hosting / Technology**: Static HTML5, Vanilla CSS, and minimal Vanilla JavaScript located under `website/`.
- **Zero Desktop Control**: The website has no administrative control over the user's desktop, cannot monitor host hardware, and cannot enforce agent policies.

---

## 2. Strict Architectural Boundaries

1. **No Website-to-Desktop Control Bridge**:
   - The desktop application must **NEVER expose an unauthenticated local HTTP or WebSocket control server** for web browser interaction in V1.
   - The website cannot command the desktop application to allow, block, or execute agent actions.
2. **Mandatory Labeling of Simulations**:
   - Any telemetry graphs, resource alerts, or AgentGuard policy evaluations rendered in web demos must be **prominently labeled as "SYNTHETIC DEMO SIMULATION"**.
   - Simulated data must never be presented as live metrics from the visitor's computer.
3. **No Visitor Hardware Inspection**:
   - The website must never claim that it can inspect, secure, or monitor the website visitor's computer.
4. **Zero Secrets in Frontend Assets**:
   - No API keys, tokens, internal IP addresses, or developer credentials may appear in client-side HTML, CSS, or JS.
5. **No Telemetry or Remote Analytics**:
   - Do not include third-party tracking scripts, advertising trackers, or external analytics in the presentation site.
