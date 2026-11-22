#!/usr/bin/env python3
"""
Alethian v3.0 — Forensic Benchmark Test Document Generator
Generates 5 distinct PDF test documents across all forensic verification categories:
1. 01_Human_Authentic_Research.pdf       - Human authored (Tier 0 Human, High Originality)
2. 02_Synthetic_AI_Generated.pdf         - Pure LLM synthetic prose (Tier 3 Elevated Synthetic)
3. 03_Hybrid_ChangePoint_Sample.pdf      - Human intro + AI body (Tier 2 Mixed AI, Change-point detection)
4. 04_Adversarial_Tampered_AI.pdf        - AI text with zero-width spaces & Cyrillic homoglyphs (Tamper Alert)
5. 05_High_Overlap_Twin_Document.pdf     - Verbatim duplicate passages (85% twin document remediation test)
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

OUTPUT_DIR = "/home/akshit/Projects/Plag-checkv1/Alethian/test_documents"
os.makedirs(OUTPUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Heading1'],
    fontName='Helvetica-Bold',
    fontSize=18,
    leading=22,
    spaceAfter=12,
    textColor=colors.HexColor('#181a1f')
)

author_style = ParagraphStyle(
    'DocAuthor',
    parent=styles['Normal'],
    fontName='Helvetica-Oblique',
    fontSize=10,
    leading=14,
    spaceAfter=18,
    textColor=colors.HexColor('#475569')
)

heading_style = ParagraphStyle(
    'DocHeading',
    parent=styles['Heading2'],
    fontName='Helvetica-Bold',
    fontSize=12,
    leading=16,
    spaceBefore=12,
    spaceAfter=6,
    textColor=colors.HexColor('#1e293b')
)

body_style = ParagraphStyle(
    'DocBody',
    parent=styles['BodyText'],
    fontName='Times-Roman',
    fontSize=10.5,
    leading=15,
    spaceAfter=10,
    textColor=colors.HexColor('#111827')
)

# ---------------------------------------------------------------------------
# 1. Human Authentic Research Document
# ---------------------------------------------------------------------------
def make_human_doc():
    filename = os.path.join(OUTPUT_DIR, "01_Human_Authentic_Research.pdf")
    doc = SimpleDocTemplate(filename, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    story = []

    story.append(Paragraph("State Machine Replication and Quorum Dynamics in Partition-Tolerant Distributed Consensus", title_style))
    story.append(Paragraph("Dr. Evelyn Vance & Marcus Thorne · Department of Computer Systems Engineering", author_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Abstract", heading_style))
    story.append(Paragraph(
        "Modern distributed storage architectures depend on consensus algorithms that guarantee safety under asynchronous "
        "network conditions while preserving liveness during periods of bounded message delay. In this work, we present an empirical "
        "critique of Paxos variants and the Raft consensus framework, examining their behavior during asymmetric partial partitions. "
        "Through controlled chaos injection across a ten-node geodistributed cluster, we demonstrate that subtle edge cases in leader election "
        "heartbeats can trigger sustained leader oscillation, degrading throughput by up to sixty-four percent without violating safety invariants.",
        body_style
    ))

    story.append(Paragraph("1. Introduction and Architectural Foundations", heading_style))
    story.append(Paragraph(
        "For decades, the theoretical foundation of distributed consensus has revolved around the FLP impossibility result, which "
        "establishes that no deterministic asynchronous protocol can guarantee consensus in the presence of even a single unannounced crash failure. "
        "Practical engineering implementations circumvents this fundamental limit by relying on randomized timers, partial synchrony assumptions, "
        "and majority quorum intersections. However, our field observations indicate that real-world cluster degradation rarely mimics clean, binary node crashes. "
        "Instead, degraded NICs, packet drops, and asymmetric routing topologies create insidious intermediate states where a node may receive consensus "
        "heartbeats from peer replicas yet remain unable to transmit outbound RPC responses.",
        body_style
    ))
    story.append(Paragraph(
        "When such partial partitions manifest in a production deployment, conventional heartbeat monitoring mechanisms frequently misdiagnose "
        "the partition as an isolated follower failure. Consequently, the isolated node enters a candidate election loop, incrementing its local term "
        "counter and broadcasting disruptive RequestVote messages whenever intermittent network connectivity momentarily resumes. In Raft implementations, "
        "a higher term received by an active, legitimate leader forces that leader to step down immediately into follower state, triggering a cascading cycle "
        "of uncoordinated re-elections.",
        body_style
    ))

    story.append(PageBreak())

    story.append(Paragraph("2. Empirical Evaluation and Quorum Stability", heading_style))
    story.append(Paragraph(
        "To rigorously quantify the systemic impact of these election storms, we deployed an instrumented Raft cluster using etcd-raft engine bindings. "
        "We systematically injected artificial packet delays of between 150ms and 800ms targeting arbitrary subsets of follower nodes. Our empirical findings "
        "confirm that standard pre-vote extensions mitigate simplistic partition thrashing by requiring candidate nodes to establish speculative quorum reachability "
        "prior to incrementing their persistent term metadata.",
        body_style
    ))
    story.append(Paragraph(
        "Nonetheless, under multi-hop routing degradation where quorum visibility remains non-transitive, pre-vote phases can become deadlocked. In such topologies, "
        "node A can communicate with node B, and node B can communicate with node C, but node A cannot directly exchange datagrams with node C. Such non-transitive "
        "splits fundamentally violate the transitive assumption upon which simple majority quorums rely, resulting in severe tail-latency spikes in log commit horizons.",
        body_style
    ))
    story.append(Paragraph(
        "We propose an adaptive lease-extension mechanism whereby the reigning leader dynamically modulates its heartbeat period in response to moving-average network jitter. "
        "By dynamically dampening election timeouts during periods of elevated variance, the consensus engine reduces unnecessary leadership transitions by seventy-eight percent, "
        "providing resilient transactional continuity under severe network anomalies.",
        body_style
    ))

    doc.build(story)
    print(f"Created: {filename}")

# ---------------------------------------------------------------------------
# 2. Pure Synthetic AI-Generated Document
# ---------------------------------------------------------------------------
def make_ai_doc():
    filename = os.path.join(OUTPUT_DIR, "02_Synthetic_AI_Generated.pdf")
    doc = SimpleDocTemplate(filename, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    story = []

    story.append(Paragraph("The Strategic Imperative of Autonomous Multi-Agent Architectures in Enterprise Systems", title_style))
    story.append(Paragraph("Comprehensive Technical Overview · AI Research Group", author_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Executive Overview", heading_style))
    story.append(Paragraph(
        "In the contemporary technological landscape, the integration of autonomous multi-agent systems has emerged as a transformative paradigm. "
        "As organizations strive to optimize operational efficiency and drive innovation, artificial intelligence agents offer unprecedented opportunities "
        "for workflow automation, decision support, and scalable problem-solving. This document explores the core architectural principles, "
        "practical implementation methodologies, and future trajectories of multi-agent collaboration in complex enterprise environments.",
        body_style
    ))

    story.append(Paragraph("Foundational Concepts of Agentic Orchestration", heading_style))
    story.append(Paragraph(
        "Furthermore, it is essential to understand the underlying mechanisms that enable multi-agent systems to function effectively. "
        "Unlike traditional monolithic systems, multi-agent frameworks distribute computational tasks across specialized autonomous units. "
        "Each agent operates with designated responsibilities, leveraging domain-specific capabilities to achieve collective objectives. "
        "Moreover, by utilizing standardized communication protocols and shared memory architectures, these systems ensure seamless interoperability "
        "and robust performance across heterogeneous enterprise infrastructures.",
        body_style
    ))
    story.append(Paragraph(
        "In addition, the implementation of dynamic role allocation enables agents to adapt to shifting organizational demands in real time. "
        "When unexpected disruptions occur, autonomous agents can collaboratively renegotiate task assignments, mitigating bottlenecks and enhancing resilience. "
        "Consequently, organizations that adopt agentic architectures experience significant improvements in resource utilization, agility, and system uptime.",
        body_style
    ))

    story.append(PageBreak())

    story.append(Paragraph("Strategic Implementation and Scalability", heading_style))
    story.append(Paragraph(
        "Moreover, the successful deployment of multi-agent architectures requires careful consideration of security, governance, and ethical alignment. "
        "As autonomous agents interact with critical business data, organizations must institute comprehensive audit trails, role-based access controls, "
        "and deterministic guardrails. By doing so, enterprises can harness the immense power of generative artificial intelligence while maintaining compliance "
        "with regulatory standards and industry best practices.",
        body_style
    ))
    story.append(Paragraph(
        "In conclusion, it is crucial to recognize that the transition toward autonomous agentic workflows represents a fundamental evolution in software engineering. "
        "By embracing decentralized intelligence, fostering modular collaboration, and establishing rigorous oversight frameworks, forward-thinking enterprises "
        "can unlock new frontiers of productivity and secure a sustainable competitive advantage in an increasingly digital world.",
        body_style
    ))

    doc.build(story)
    print(f"Created: {filename}")

# ---------------------------------------------------------------------------
# 3. Hybrid Change-Point Document
# ---------------------------------------------------------------------------
def make_hybrid_doc():
    filename = os.path.join(OUTPUT_DIR, "03_Hybrid_ChangePoint_Sample.pdf")
    doc = SimpleDocTemplate(filename, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    story = []

    story.append(Paragraph("Post-Quantum Cryptographic Migration: Algorithmic Verification and Implementation Challenges", title_style))
    story.append(Paragraph("Julian Sterling · Senior Information Security Investigator", author_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. Historical Cryptographic Context and Threat Modeling", heading_style))
    story.append(Paragraph(
        "The cryptographic foundations protecting global digital infrastructure rest heavily upon the computational hardness of discrete logarithms "
        "and integer factorization. RSA, Diffie-Hellman, and elliptic curve schemes have provided robust guarantees for over four decades. "
        "However, Peter Shor's 1994 quantum polynomial-time algorithm completely undermines these mathematical assumptions once fault-tolerant quantum computing reaches scale. "
        "In our institutional assessment, adversary state actors are already harvesting encrypted diplomatic and financial traffic today under 'store now, decrypt later' protocols.",
        body_style
    ))
    story.append(Paragraph(
        "Consequently, the migration to post-quantum cryptography (PQC) cannot be treated as a routine library upgrade. Unlike previous transitions—such as moving from "
        "SHA-1 to SHA-256 or expanding RSA key sizes from 1024 to 2048 bits—post-quantum algorithms introduce substantially larger public keys, vastly increased ciphertext overhead, "
        "and non-trivial side-channel vulnerability profiles that require comprehensive memory architecture re-engineering.",
        body_style
    ))

    story.append(PageBreak())

    # --- Change point boundary occurs here: transition to synthetic prose ---
    story.append(Paragraph("2. Algorithmic Optimization and Future Implementation Paradigms", heading_style))
    story.append(Paragraph(
        "Furthermore, it is important to recognize that the implementation of lattice-based cryptographic algorithms represents a critical milestone for modern security teams. "
        "Moreover, by leveraging advanced mathematical constructs such as learning with errors and module lattices, contemporary protocols achieve exceptional resilience against quantum adversaries. "
        "Additionally, organizations must adopt a proactive approach to cryptographic agility, ensuring that legacy infrastructure can seamlessly transition to next-generation standards.",
        body_style
    ))
    story.append(Paragraph(
        "In conclusion, it is vital to emphasize that cryptographic modernization is an essential strategic imperative. By implementing automated governance frameworks, "
        "conducting comprehensive risk assessments, and collaborating with industry partners, enterprise stakeholders can effectively safeguard digital assets against emerging quantum threats.",
        body_style
    ))

    doc.build(story)
    print(f"Created: {filename}")

# ---------------------------------------------------------------------------
# 4. Adversarially Tampered Document (Zero-Width + Homoglyphs)
# ---------------------------------------------------------------------------
def make_tampered_doc():
    filename = os.path.join(OUTPUT_DIR, "04_Adversarial_Tampered_AI.pdf")
    doc = SimpleDocTemplate(filename, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    story = []

    # Insert Cyrillic homoglyphs into text to trigger UTS #39 Confusable Normalizer
    # Cyrillic small 'а' (\u0430), small 'е' (\u0435), small 'о' (\u043e)
    # Zero-width spaces (\u200B)
    zw = "\u200B"
    tampered_p1 = (
        f"In{zw} the{zw} contemporary{zw} technological{zw} landscape, artificial intelligence models demonstrate exceptional capabilities. "
        f"Furt\u0430ermore, it is essenti\u0430l to underst\u0430nd how de\u0435p learning tr\u0430nsforms clinic\u0430l workflows. "
        f"By leveraging аdvаncеd аlgorithms, medicаl pr\u043ectlitionеrs c\u0430n enh\u0430nce di\u0430gnostic \u0430ccur\u0430cy \u0430nd stre\u0430mline p\u0430tient c\u0430re."
    )
    tampered_p2 = (
        f"M\u043ere\u043ever, the integr\u0430ti\u043en \u043ef \u0430ut\u043en\u043em\u043eus di\u0430gn\u043estic tools ensures c\u043ensistent perform\u0430nce across hospit\u0430l netw\u043erks. "
        f"In c\u043enclusi\u043en, it is cruci\u0430l to n\u043ete th\u0430t techn\u043el\u043egic\u0430l \u043edv\u0430ncements will continue to rev\u043eluti\u043enize glob\u0430l he\u0430lthc\u0430re systems."
    )

    story.append(Paragraph("Adversarial Robustness in Diagnostic Machine Learning Workflows", title_style))
    story.append(Paragraph("Academic Integrity Security Evaluation Benchmark", author_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Section 1: Automated Clinical Assessment", heading_style))
    story.append(Paragraph(tampered_p1, body_style))
    story.append(Paragraph(tampered_p2, body_style))

    # Add second page of text to satisfy minimum tokens
    story.append(PageBreak())
    story.append(Paragraph("Section 2: Extended Evaluation Metrics", heading_style))
    story.append(Paragraph(
        f"Furthermore, recent advances in computer vision and natural language processing provide unparalleled opportunities for precision diagnostics. "
        f"By incorporating multimodal patient records, neural architectures can synthesize clinical history, radiological imaging, and genomic sequencing data "
        f"into unified predictive models. Consequently, healthcare providers can identify pathological anomalies at earlier stages, improving clinical outcomes.",
        body_style
    ))
    story.append(Paragraph(
        f"In conclusion, the deployment of intelligent healthcare systems requires comprehensive validation, robust privacy safeguards, and continuous auditing. "
        f"Organizations that prioritize ethical AI implementation will ensure patient safety while maximizing therapeutic efficiency.",
        body_style
    ))

    doc.build(story)
    print(f"Created: {filename}")

# ---------------------------------------------------------------------------
# 5. High-Overlap Twin Document (85% Overlap Remediation Test)
# ---------------------------------------------------------------------------
def make_overlap_doc():
    filename = os.path.join(OUTPUT_DIR, "05_High_Overlap_Twin_Document.pdf")
    doc = SimpleDocTemplate(filename, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    story = []

    story.append(Paragraph("Virtual Memory Architecture and Address Translation in Monolithic Operating Systems", title_style))
    story.append(Paragraph("Operating Systems Research Laboratory · Technical Report", author_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. Virtual Address Translation and Multi-Level Paging", heading_style))
    story.append(Paragraph(
        "Virtual memory is a foundational memory management capability of modern general-purpose operating systems. "
        "It provides each executing process with an isolated, contiguous address space while enabling the kernel to manage "
        "physical random-access memory dynamically. Under the x86-64 architecture, address translation is governed by a multi-level page table structure, "
        "typically organized as a four-level hierarchy comprising the Page Global Directory (PGD), Page Upper Directory (PUD), "
        "Page Middle Directory (PMD), and Page Table Entry (PTE). The CPU's Memory Management Unit (MMU) traverses this hierarchical tree "
        "using the base physical address stored in control register CR3.",
        body_style
    ))
    story.append(Paragraph(
        "To minimize the substantial latency overhead associated with repeated memory lookups during page table walks, the processor relies on a "
        "Translation Lookaside Buffer (TLB). The TLB operates as an associative hardware cache that stores recent virtual-to-physical address mappings. "
        "When a TLB miss occurs, the MMU must perform a full page table walk, incurring memory bus latency of several dozen nanoseconds. "
        "In high-throughput multi-threaded workloads, frequent context switches trigger involuntary TLB invalidations, drastically reducing effective memory bandwidth.",
        body_style
    ))

    story.append(PageBreak())

    story.append(Paragraph("2. Page Fault Handling and Demand Paging Mechanisms", heading_style))
    story.append(Paragraph(
        "Demand paging dictates that physical page frames are allocated only when a process explicitly accesses an unmapped virtual address. "
        "When the MMU encounters a page entry with its Present bit cleared, it generates an architectural page fault exception (Interrupt 14). "
        "The kernel's trap handler intercepts this interrupt, saves process registers to the stack frame, and queries the virtual memory area (VMA) "
        "descriptors associated with the active mm_struct to determine if the access was legally authorized.",
        body_style
    ))
    story.append(Paragraph(
        "If the address falls within a valid readable segment, the kernel allocates a zeroed physical page frame, updates the corresponding PTE with the "
        "new physical frame address and access permissions, flushes the localized TLB entry, and resumes process execution seamlessly. "
        "Conversely, if the access violates memory segmentation boundaries or attempts an unauthorized write to a read-only code segment, "
        "the kernel delivers a SIGSEGV segmentation violation signal, terminating the errant process.",
        body_style
    ))

    doc.build(story)
    print(f"Created: {filename}")

if __name__ == '__main__':
    make_human_doc()
    make_ai_doc()
    make_hybrid_doc()
    make_tampered_doc()
    make_overlap_doc()
    print("\nAll 5 forensic benchmark test documents successfully generated in:")
    print(OUTPUT_DIR)
