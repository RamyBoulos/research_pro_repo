# Examiner Coach Research Project Report

This directory contains the LaTeX source for the research project report:

**Research Project Report: Examiner Coach: A Modular RAG Prototype for OSCE
Examiner Feedback Training**

The report belongs to the Computational Modelling and Simulation M.Sc.,
Life Science Track, at Technische Universitaet Dresden. The project was carried
out in the context of the Else Kroener Fresenius Center (EKFZ) for Digital
Health.

## Canonical Source

The canonical report source is:

```text
docs/paper/main.tex
```

The report is assembled from section files under:

```text
docs/paper/sections/
```

Figures and logos used by the report are stored under:

```text
docs/paper/figures/
```

## Report Scope

The report presents Examiner Coach as a backend-focused research prototype for
OSCE examiner feedback training. It covers:

- the institutional feedback-training problem;
- the six-criterion feedback-quality model;
- the modular RAG architecture;
- KISSKI/SAIA-based transcription, embedding, chat, and document-conversion
  services;
- the comparison of direct retrieval, HyDE retrieval, filtered retrieval, and
  unfiltered retrieval;
- the LLM-as-a-judge validation workflow used in the debug notebook.

The frontend is treated as a supporting interface for recording audio,
displaying results, and enabling coaching interaction. It is not the central
technical contribution of the report.

## References

References are maintained manually in:

```text
docs/paper/sections/10_references.tex
```

They are intentionally split into two groups:

- **Knowledge Base References**: feedback and medical-education sources used to
  build the local retrieval knowledge base.
- **Technical References**: RAG, reranking, long-context, and AI-service
  references that support the technical design.

The manual reference section is the source of truth for the report. The
`references.bib` file is not currently used by `main.tex`.

## Build

From `docs/paper/`, the report can be built with:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

For temporary builds that avoid writing generated files into the report
directory, use an output directory such as `/tmp/research-paper-build`.
