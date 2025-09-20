# AI-DLC Tool Evolution: A Phased Rust Implementation

This document provides a strategic analysis of the `ai-dlc` command-line tool and proposes a detailed, phased roadmap for its implementation in the **Rust** programming language. The plan is structured to deliver value incrementally, starting with a standalone utility and evolving into a full-fledged, server-backed orchestration system.

### 1. Current Tool Analysis

(This section remains unchanged, summarizing the tool's current capabilities as a prompt engineering utility.)

### 2. Strategic Fit within the AI-DLC Ecosystem

(This section remains unchanged, establishing the tool as the "librarian" and "workshop" for the template library.)

### 3. Core Technology Stack: Rust

(This section remains unchanged, detailing the rationale for choosing Rust and the key frameworks like Axum, Clap, and Tokio.)

### 4. The New Phased Architectural Evolution

The project will be executed in three distinct, sequential phases:

*   **Phase 1: Standalone Scaffolding CLI:** The immediate goal is to deliver a valuable, self-contained CLI tool for generating best-practice templates. This provides utility to users right away without any complex setup.
*   **Phase 2: The Local-First Integrated System:** This phase introduces the full workflow orchestration system (server, worker, queue), but runs it entirely on the developer's local machine.
*   **Phase 3: Cloud & Multi-User Deployment:** The final phase involves deploying the system built in Phase 2 to a cloud environment to enable true team collaboration.

---

### 5. Phase 1: Standalone Scaffolding CLI

**Goal:** To build and distribute a single, dependency-free binary that allows users to scaffold new projects with best-practice templates for various AI providers.

**Architecture:** A simple, single-binary Rust application. There are no servers, databases, or containers in this phase.

**Core Feature: The `scaffold` Command**

*   **Purpose:** To generate starter templates, rules, and checks for one or more AI providers.
*   **Functionality:** The standard templates for providers (Claude, Gemini, etc.) are bundled directly into the `ai-dlc-cli` binary at compile time using a Rust macro like `include_dir!`. The `scaffold` command extracts these assets into the user's filesystem.
*   **Interface:**
    *   `ai-dlc scaffold`: Runs an interactive wizard for selecting providers.
    *   `ai-dlc scaffold --provider gemini --provider claude`: Scaffolds assets for specific providers.
    *   `ai-dlc scaffold --all`: Scaffolds assets for all supported providers.
*   **Outcome:** This command creates directories like `templates/` and `rules/`. It does not create any server-related configuration.

---

### 6. Phase 2: The Local-First Integrated System

**Goal:** To introduce the full workflow orchestration system, running entirely on the developer's local machine via Docker Compose. This enables advanced features like project state tracking and asynchronous task execution.

**Architecture:** This phase adds the server, worker, and Redis components, all running locally.

**New Features Introduced in Phase 2:**
*   **`ai-dlc services` command:** A new command group (`setup`, `start`, `stop`) to manage the local Docker-based server environment.
*   **`ai-dlc project` and `ai-dlc feature` commands:** To interact with the orchestration server to track workflows.
*   **Orchestrated `ai-dlc generate`:** The `generate` command is enhanced to be a client to the local server, dispatching jobs to the background worker.

---

### 7. Phase 3: Cloud & Multi-User Deployment

**Goal:** To deploy the server and database components built in Phase 2 to a cloud environment, enabling team collaboration, central logging, and a single source of truth.

**Process:** This phase is focused on infrastructure and deployment, not new application features. It involves creating the necessary cloud resources and reconfiguring the `ai-dlc` clients to point to public endpoints.

---

### 8. Updated Technical & Architectural Roadmap

This revised roadmap prioritizes incremental value delivery.

#### Phase 1: Standalone Scaffolding CLI
1.  **Setup Project:** Establish the Cargo Workspace with a single `ai-dlc-cli` crate.
2.  **Bundle Assets:** Integrate the `include_dir` crate and embed the `templates/` and `rules/` directories into the binary.
3.  **Implement `scaffold` Command:** Build the CLI interface using `clap` and implement the logic to extract the bundled assets to the filesystem.
4.  **Package & Distribute:** Create a release process to build and distribute the single `ai-dlc-cli` binary for major platforms.

#### Phase 2: Local-First Integrated System
1.  **Expand Workspace:** Add the `ai-dlc-server` and `ai-dlc-worker` crates to the Cargo workspace.
2.  **Add Docker & Redis:** Create a `docker-compose.yml` file to manage a local Redis instance.
3.  **Build Server & Worker:** Implement the server (`axum`) and worker applications, defining the API and job formats for communication via Redis.
4.  **Enhance CLI:** Implement the `services`, `project`, and `feature` commands. Modify the `generate` command to act as a client to the local server.

#### Phase 3: Cloud & Multi-User Deployment
1.  **Infrastructure as Code:** Develop scripts (e.g., Terraform, Kubernetes manifests) to deploy the `ai-dlc-server` and a managed Redis/database instance to the cloud.
2.  **CI/CD for Deployment:** Create a continuous deployment pipeline to automatically deploy new versions of the server application.
