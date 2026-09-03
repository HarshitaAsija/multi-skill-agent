# On-Site Engagement & Conversion Audit Reference Guide

## 1. Scope & Objective
The `engagement-audit` skill evaluates why human visitors and autonomous browsing agents arriving on the site fail to engage, convert, or navigate effectively.

## 2. Above-The-Fold Value Proposition Deficit (`ENG-01`)
First-time visitors arriving from AI search recommendations make a stay-or-bounce decision within 3 seconds:
- **Heuristic**: Landing page top viewport section requires a clear `<h1>` heading and a descriptive value proposition (> 30 visible words).
- **Impact**: Sparse, cryptic hero sections produce immediate bounce and fail to communicate product utility to AI browsing agents.

## 3. Deep Subpage Context Isolation (`ENG-02`)
Over 60% of search referral traffic lands on deep subpages (`path depth >= 4`) rather than the homepage:
- **Heuristic**: Deep pages require breadcrumb navigation (`<nav aria-label="breadcrumb">` or `BreadcrumbList` JSON-LD) and explicit navigation landmarks (`<nav>`, `<main>`).
- **Impact**: Without upward navigation anchors, visitors referred directly to deep pages experience cognitive drop-off and cannot navigate back to core product pages.

## 4. CTA Label Ambiguity & Information Scent (`ENG-03`)
Generic call-to-action button text ("Click Here", "Learn More", "Submit") provides weak information scent:
- **Heuristic**: Flags generic labels lacking explicit benefit or target action.
- **Remediation**: Use descriptive, benefit-oriented text (e.g. "Start Free Trial", "Download API Guide").

## 5. Form Input Friction & Accessibility (`ENG-04`)
- **Heuristic**: Conversion forms must attach semantic `<label for="...">` or `aria-label` attributes to all input fields.
- **Impact**: Unlabeled inputs create accessibility compliance failures and increase abandonment on conversion pages.
