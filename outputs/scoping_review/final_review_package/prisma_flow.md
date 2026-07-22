# PRISMA-Style Flow Summary

```mermaid
flowchart TD
    A[Records identified: n = 1435<br/>PubMed/MEDLINE: 381<br/>External sources: 1054] --> B[Deduplication and citation reconciliation<br/>n = 488 duplicate or alias records removed]
    B --> C[Deduplicated records for abstract/metadata relevance screening<br/>n = 947]
    C --> D[Excluded as not relevant to the OA digital/conversational review question<br/>n = 652]
    C --> E[Retained for context relevance review<br/>n = 295]
    E --> F[Context-only evidence map<br/>n = 286]
    E --> G[Main evidence included in synthesis<br/>n = 9 studies]
```

Note: Counts are reported after DOI/title deduplication and final citation reconciliation. Source-row audit files are retained for traceability but are not used as manuscript denominators. Model-assisted adjudication was used only as an internal audit aid after screening; it is not shown as a separate filtration step.
