# System Diagrams - Condominium Analytics

This document contains visual diagrams to help explain the Condominium Analytics application to different audiences.

## Simple Flow Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PDF Reports   │    │  Smart System   │    │   Easy Access   │
│                 │    │                 │    │                 │
│ • Monthly bills │───▶│ • Reads PDFs    │───▶│ • Ask questions │
│ • Expense data  │    │ • Understands   │    │ • Get answers   │
│ • Trial balance │    │   content       │    │ • View details  │
└─────────────────┘    │ • Stores info   │    └─────────────────┘
                       └─────────────────┘
```

## Step-by-Step User Journey

```
Step 1: SETUP (Behind the scenes)
┌─────────────────────────────────────────────────────────────┐
│ PDF Documents → AI Processing → Smart Database Creation     │
│ (Trial Balance)   (Understands)   (603 Documents Ready)    │
└─────────────────────────────────────────────────────────────┘

Step 2: USER INTERACTION (What you see)
┌─────────────────────────────────────────────────────────────┐
│ Type Question → AI Understands → Smart Search → Get Answer │
│ "Power costs?"   (Natural Lang.)   (Find relevant)  (Real) │
└─────────────────────────────────────────────────────────────┘
```

## Detailed System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CONDOMINIUM ANALYTICS SYSTEM                         │
└─────────────────────────────────────────────────────────────────────────┘

PHASE 1: DATA PREPARATION (One-time setup)
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   PDF FILES │───▶│ AI READER   │───▶│ SMART STORE │───▶│ READY TO    │
│             │    │             │    │             │    │ ANSWER      │
│ • Jan 2025  │    │ • Extracts  │    │ • 603 docs  │    │ • Questions │
│ • Feb 2025  │    │   expenses  │    │ • Organized │    │ • Searches  │
│ • Mar 2025  │    │ • Categories│    │ • Indexed   │    │ • Analysis  │
│ • etc...    │    │ • Amounts   │    │ • Semantic  │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘

PHASE 2: USER INTERACTION (Real-time)
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ USER TYPES  │───▶│ AI CLAUDE   │───▶│ SMART SEARCH│───▶│ INSTANT     │
│ QUESTION    │    │ UNDERSTANDS │    │ IN DATABASE │    │ ANSWER      │
│             │    │             │    │             │    │             │
│ "How much   │    │ • Natural   │    │ • Finds     │    │ "Power:     │
│ for power   │    │   language  │    │   relevant  │    │ R$ 2,450    │
│ in Jan?"    │    │ • Context   │    │   expenses  │    │ paid to     │
│             │    │ • Intent    │    │ • Multiple  │    │ CEMIG"      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Before vs After Comparison

```
┌─────────────────────────────────────────────────────────────┐
│                    BEFORE vs AFTER                         │
├─────────────────────────────────────────────────────────────┤
│ BEFORE: Manual Process                                      │
│ ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│ │ Question│─▶│ Find PDF│─▶│ Read    │─▶│ Calculate│        │
│ │ about   │  │ files   │  │ through │  │ manually │        │
│ │ expenses│  │ manually│  │ pages   │  │          │        │
│ └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│                    Time: 10-30 minutes                     │
├─────────────────────────────────────────────────────────────┤
│ AFTER: Condominium Analytics                               │
│ ┌─────────┐                            ┌─────────┐        │
│ │ Type    │─────────────────────────────▶│ Get     │        │
│ │ question│         AI handles           │ instant │        │
│ │ in chat │         everything           │ answer  │        │
│ └─────────┘                            └─────────┘        │
│                    Time: 5 seconds                        │
└─────────────────────────────────────────────────────────────┘
```

## Benefits Comparison

```
┌────────────────────────────────────────────────────────────────┐
│                     TRADITIONAL vs SMART                       │
├────────────────────────────────────────────────────────────────┤
│ TRADITIONAL METHOD          │  CONDOMINIUM ANALYTICS            │
│                            │                                   │
│ • Search through files     │  • Ask in plain language         │
│ • Read multiple pages      │  • AI finds exact information    │
│ • Manual calculations      │  • Instant calculations          │
│ • 15-30 minutes           │  • 5 seconds                     │
│ • Prone to errors         │  • Accurate results              │
│ • Need computer access     │  • Works on any device           │
└────────────────────────────────────────────────────────────────┘
```

## Real Example Walkthrough

```
EXAMPLE: "How much did we spend on power in January 2025?"

Step 1: User Input
┌─────────────────────────────────────┐
│ User types natural question:        │
│ "How much did we spend on power     │
│ in January 2025?"                   │
└─────────────────────────────────────┘
                    ↓
Step 2: AI Understanding
┌─────────────────────────────────────┐
│ Claude AI processes:                │
│ • Identifies: "power" = utilities   │
│ • Time period: "January 2025"      │
│ • Action: "spend" = expense query   │
└─────────────────────────────────────┘
                    ↓
Step 3: Smart Search
┌─────────────────────────────────────┐
│ System searches 603 documents for:  │
│ • Category: utilities/power         │
│ • Period: 2025-01                   │
│ • Type: expenses                    │
└─────────────────────────────────────┘
                    ↓
Step 4: Result
┌─────────────────────────────────────┐
│ "Power expenses for January 2025:   │
│ R$ 2,450.30 paid to CEMIG on       │
│ 15/01/2025"                        │
└─────────────────────────────────────┘
```

## Architecture Components

```
Title: "Condominium Analytics - Technical Architecture"

┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ PDF Input   │───▶│ Processing  │───▶│ Storage     │
│             │    │             │    │             │
│ • Monthly   │    │ • AI Reader │    │ • ChromaDB  │
│   reports   │    │ • Data      │    │ • 603 docs  │
│ • 6 months  │    │   extraction│    │ • Semantic  │
│ • PACTO     │    │ • Semantic  │    │   vectors   │
│   property  │    │   chunking  │    │             │
└─────────────┘    └─────────────┘    └─────────────┘

┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ User Query  │───▶│ AI Analysis │───▶│ Response    │
│             │    │             │    │             │
│ • Natural   │    │ • Claude AI │    │ • Instant   │
│   language  │    │ • Context   │    │   answer    │
│ • Web       │    │   assembly  │    │ • Relevant  │
│   interface │    │ • Smart     │    │   data      │
│             │    │   search    │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

## One-Slide Summary

```
┌────────────────────────────────────────────────────────────────────┐
│                  CONDOMINIUM ANALYTICS AT A GLANCE                 │
│                                                                    │
│  INPUT              PROCESSING           OUTPUT                    │
│  ┌─────────┐       ┌─────────┐         ┌─────────┐               │
│  │ Monthly │  ───▶ │   AI    │  ───▶   │ Instant │               │
│  │ Reports │       │ System  │         │Answers  │               │
│  │         │       │         │         │         │               │
│  │6 months │       │603 docs │         │< 5 sec  │               │
│  │of data  │       │indexed  │         │response │               │
│  └─────────┘       └─────────┘         └─────────┘               │
│                                                                    │
│  EXAMPLES OF QUESTIONS:                                           │
│  • "How much for utilities in January?"                          │
│  • "What did we pay for elevator maintenance?"                   │
│  • "Show total expenses for February 2025"                       │
│                                                                    │
│  TRY IT: https://condominium-analytics-xxztp26via-uc.a.run.app/  │
└────────────────────────────────────────────────────────────────────┘
```

## For Visual Tools

### Color Scheme Suggestions
- **PDF/Input:** Light Blue (#E3F2FD)
- **Processing:** Green (#E8F5E8)
- **Storage:** Orange (#FFF3E0)
- **User Interface:** Purple (#F3E5F5)
- **Results:** Dark Blue (#1976D2)

### Recommended Tools
- **Miro** - For collaborative diagrams
- **Lucidchart** - For flowcharts
- **Canva** - For presentations
- **Draw.io** - Free online tool
- **PowerPoint/Google Slides** - For presentations

## Usage by Audience

- **Simple flows** - For executives and stakeholders
- **Technical diagrams** - For developers and IT teams
- **Before/after comparisons** - For decision makers
- **Step-by-step examples** - For end users and training
- **Architecture components** - For technical documentation

---

**Live Application:** [https://condominium-analytics-xxztp26via-uc.a.run.app/](https://condominium-analytics-xxztp26via-uc.a.run.app/)