"""
AI Answerability & Market Intelligence Engine.

Provides deterministic, offline analysis of website question answerability:
  1. Industry Archetype Detection (Restaurant, E-Commerce, SaaS, Healthcare, Education, General Business)
  2. Answerability Evaluation across 5 core high-intent questions
  3. AI Query Simulation (Prompt simulation & hallucination risk analysis)
  4. Question Gap Analysis (Market Question Coverage %)
  5. Auto-Generated Ready-to-Paste FAQ Schema (JSON-LD) for gaps
  6. Prioritized Smart Growth Roadmap (Priority 1/2/3 with Impact & Effort)
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse


@dataclass
class QuestionCheckResult:
    id: str
    question: str
    simulated_prompt: str
    status: str  # "ANSWERABLE", "PARTIAL", "NOT_ANSWERABLE"
    evidence_found: str
    ai_risk: str
    faq_schema_snippet: Dict[str, Any]
    impact: str  # "HIGH", "MEDIUM", "LOW"
    effort: str  # "LOW", "MEDIUM", "HIGH"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "simulated_prompt": self.simulated_prompt,
            "status": self.status,
            "evidence_found": self.evidence_found,
            "ai_risk": self.ai_risk,
            "faq_schema_snippet": self.faq_schema_snippet,
            "impact": self.impact,
            "effort": self.effort,
        }


@dataclass
class SmartRoadmapItem:
    priority: int
    action_title: str
    why: str
    impact: str
    effort: str
    suggested_faq_json_ld: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "priority": self.priority,
            "action_title": self.action_title,
            "why": self.why,
            "impact": self.impact,
            "effort": self.effort,
            "suggested_faq_json_ld": self.suggested_faq_json_ld,
        }


@dataclass
class MarketIntelligenceReport:
    detected_industry: str
    industry_label: str
    confidence: float
    market_question_coverage_pct: int
    questions_checked: int
    clear_count: int
    partial_count: int
    missing_count: int
    questions: List[QuestionCheckResult] = field(default_factory=list)
    question_gaps: List[str] = field(default_factory=list)
    roadmap: List[SmartRoadmapItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected_industry": self.detected_industry,
            "industry_label": self.industry_label,
            "confidence": self.confidence,
            "market_question_coverage_pct": self.market_question_coverage_pct,
            "questions_checked": self.questions_checked,
            "clear_count": self.clear_count,
            "partial_count": self.partial_count,
            "missing_count": self.missing_count,
            "questions": [q.to_dict() for q in self.questions],
            "question_gaps": self.question_gaps,
            "roadmap": [r.to_dict() for r in self.roadmap],
        }


class MarketIntelligenceEngine:
    """
    Evaluates what questions an AI assistant can answer about a business,
    detects question gaps, and provides an actionable Smart Growth Roadmap.
    """

    INDUSTRY_DEFINITIONS = {
        "RESTAURANT": {
            "label": "Restaurant & Dining",
            "schema_types": {"Restaurant", "FoodEstablishment", "CafeOrCoffeeShop", "BarOrPub", "FastFoodRestaurant"},
            "url_keywords": ["menu", "food", "dining", "dish", "chef", "table", "reservation", "order", "cuisine"],
            "text_keywords": ["menu", "restaurant", "chef", "dine", "cuisine", "reservations", "cocktails", "appetizers", "dessert", "bar"],
            "questions": [
                {
                    "id": "REST-Q1",
                    "question": "What are the opening hours and operational days?",
                    "prompt": "What are the opening hours for {brand} and are they open on weekends?",
                    "regex_strong": r"(?:mon|tue|wed|thu|fri|sat|sun|daily|open daily|hours).*?(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)|\b\d{1,2}\s*-\s*\d{1,2}\b)",
                    "keywords_strong": ["opening hours", "hours of operation", "open daily", "business hours", "closing time"],
                    "keywords_partial": ["hours", "open", "closed", "schedule"],
                    "ai_risk": "AI assistants will either hallucinate hours or inform diners to call, leading to lost customer visits.",
                    "action_title": "Add Clear Opening Hours & Schedule",
                    "why": "Diners and conversational AI agents frequently query whether a venue is currently open before visiting.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "What are your business hours?",
                    "faq_a": "We are open Monday through Friday from 11:00 AM to 10:00 PM, and Saturday to Sunday from 10:00 AM to 11:00 PM.",
                },
                {
                    "id": "REST-Q2",
                    "question": "Where is the restaurant located and how do I get there?",
                    "prompt": "Where is {brand} located and is there parking or public transit nearby?",
                    "regex_strong": r"(?:address|located at|find us at|street|avenue|blvd|suite|\b\d{3,5}\s+[A-Za-z]+)",
                    "keywords_strong": ["address", "location", "directions", "find us", "map", "parking"],
                    "keywords_partial": ["located", "visit", "street"],
                    "ai_risk": "Navigation and map AI bots cannot route visitors or pin exact physical location.",
                    "action_title": "Publish Physical Address & Landmark Directions",
                    "why": "Physical presence is fundamental for local search, Geo-spatial AI queries, and foot traffic.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "Where are you located?",
                    "faq_a": "We are conveniently located at [Street Address, City, Postal Code] with on-site parking available.",
                },
                {
                    "id": "REST-Q3",
                    "question": "What food and beverage items are served on the menu?",
                    "prompt": "What kind of food does {brand} serve and what are some popular dishes?",
                    "regex_strong": r"(?:menu|appetizer|entree|dessert|drinks|wine|cocktails|starters|mains|pasta|pizza|burger|salad)",
                    "keywords_strong": ["menu", "starters", "main course", "entrees", "desserts", "beverages", "wine list"],
                    "keywords_partial": ["food", "dishes", "plates", "servings"],
                    "ai_risk": "AI food recommendation agents cannot answer menu questions, directing diners to competitor menus.",
                    "action_title": "Publish Comprehensive Digital Menu with Descriptions",
                    "why": "Potential customers search for specific dishes and cuisine types before committing to a venue.",
                    "impact": "HIGH",
                    "effort": "MEDIUM",
                    "faq_q": "What type of food do you serve?",
                    "faq_a": "We offer a diverse menu featuring [Cuisine Type, e.g., authentic Italian pasta, wood-fired pizza, and seasonal desserts].",
                },
                {
                    "id": "REST-Q4",
                    "question": "Are vegetarian, vegan, or gluten-free dietary options available?",
                    "prompt": "Does {brand} offer vegetarian, vegan, or gluten-free options?",
                    "regex_strong": r"(?:vegetarian|vegan|gluten-free|gluten free|dairy-free|halal|kosher|allerg|plant-based)",
                    "keywords_strong": ["vegetarian", "vegan", "gluten-free", "allergies", "plant-based", "halal", "kosher"],
                    "keywords_partial": ["dietary", "diet", "healthy options"],
                    "ai_risk": "Diners with dietary preferences or allergies will be warned away by AI assistants seeking safe dining.",
                    "action_title": "Highlight Dietary Accommodations (Vegetarian, Vegan, GF)",
                    "why": "Dietary queries are among the highest-converting conversational searches for dining.",
                    "impact": "MEDIUM",
                    "effort": "LOW",
                    "faq_q": "Do you accommodate vegetarian and dietary restrictions?",
                    "faq_a": "Yes! We proudly offer dedicated vegetarian, vegan, and gluten-free options across our menu.",
                },
                {
                    "id": "REST-Q5",
                    "question": "Can customers reserve a table or order online?",
                    "prompt": "How can I book a table or make a reservation at {brand}?",
                    "regex_strong": r"(?:reserve|reservation|book a table|opentable|resy|tock|order online|table booking)",
                    "keywords_strong": ["reservation", "reserve a table", "book online", "order online", "opentable", "resy"],
                    "keywords_partial": ["booking", "order", "call to reserve"],
                    "ai_risk": "Autonomous booking agents (e.g., Google Duplex, Apple Intelligence) cannot complete reservations.",
                    "action_title": "Implement Online Reservation or Booking Process",
                    "why": "Direct reservation workflows eliminate friction and capture high-intent diners immediately.",
                    "impact": "HIGH",
                    "effort": "MEDIUM",
                    "faq_q": "How can I reserve a table?",
                    "faq_a": "You can easily reserve a table online through our website or by contacting us at [Phone Number].",
                },
            ],
        },
        "ECOMMERCE": {
            "label": "E-Commerce & Retail",
            "schema_types": {"Product", "Offer", "MerchantReturnPolicy", "Store", "OnlineStore"},
            "url_keywords": ["shop", "products", "cart", "checkout", "store", "catalog", "item", "buy"],
            "text_keywords": ["cart", "checkout", "shipping", "add to cart", "product", "price", "buy now", "return policy", "order tracking"],
            "questions": [
                {
                    "id": "ECOM-Q1",
                    "question": "What are the product prices and accepted currencies?",
                    "prompt": "How much do products on {brand} cost and what currencies are supported?",
                    "regex_strong": r"(?:\$\s*\d+|\b\d+\s*(?:USD|EUR|GBP|CAD|AUD)\b|\bprice\b.*?\d+)",
                    "keywords_strong": ["price", "pricing", "$", "usd", "cost", "total", "discount"],
                    "keywords_partial": ["pricing", "cost", "buy"],
                    "ai_risk": "AI shopping assistants cannot quote accurate prices, excluding items from AI shopping comparisons.",
                    "action_title": "Expose Clear Product Pricing & Schema Offers",
                    "why": "Transparent pricing with Schema.org Offer metadata is mandatory for AI shopping engines.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "How much do your products cost?",
                    "faq_a": "Our products range from $19.99 to $99.99 with all prices clearly displayed on each item page.",
                },
                {
                    "id": "ECOM-Q2",
                    "question": "What are the shipping destinations, costs, and delivery times?",
                    "prompt": "What are the shipping fees and estimated delivery times for {brand}?",
                    "regex_strong": r"(?:shipping policy|delivery time|standard shipping|express shipping|ships within|\d+-\d+\s*business days|free shipping)",
                    "keywords_strong": ["shipping policy", "free shipping", "delivery time", "ships within", "business days", "courier"],
                    "keywords_partial": ["shipping", "delivery", "dispatch"],
                    "ai_risk": "AI agents answering 'Will this arrive before Friday?' will state uncertainty and favor competitors.",
                    "action_title": "Publish Explicit Shipping & Delivery Guidelines",
                    "why": "Shipping speed and fees are the #1 driver of cart abandonment and conversational purchase queries.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "What are your shipping rates and delivery times?",
                    "faq_a": "We offer standard shipping (3-5 business days) and express delivery (1-2 business days). Free shipping applies on orders over $50.",
                },
                {
                    "id": "ECOM-Q3",
                    "question": "What is the return, exchange, and refund policy?",
                    "prompt": "Can I return an item to {brand} and what is the return window?",
                    "regex_strong": r"(?:return policy|refund policy|\b\d+\s*day returns|30-day|money back guarantee|free returns|return window)",
                    "keywords_strong": ["return policy", "refund policy", "30-day return", "money-back guarantee", "exchanges"],
                    "keywords_partial": ["returns", "refund", "exchange"],
                    "ai_risk": "Customers asking AI bots about purchase safety will receive warnings of unverified return policies.",
                    "action_title": "Display Transparent Return & Refund Terms",
                    "why": "A clear return policy builds high buyer trust and satisfies Google Merchant requirements.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "What is your return and refund policy?",
                    "faq_a": "We accept returns within 30 days of delivery for a full refund or exchange. Items must be unused and in original packaging.",
                },
                {
                    "id": "ECOM-Q4",
                    "question": "What payment methods are supported at checkout?",
                    "prompt": "What payment methods does {brand} accept (e.g., Apple Pay, PayPal, Credit Card)?",
                    "regex_strong": r"(?:visa|mastercard|amex|paypal|apple pay|google pay|klarna|afterpay|credit card)",
                    "keywords_strong": ["visa", "mastercard", "paypal", "apple pay", "google pay", "payment methods"],
                    "keywords_partial": ["payment", "checkout", "cards"],
                    "ai_risk": "Shoppers asking conversational checkout assistants will drop off if payment compatibility is unknown.",
                    "action_title": "List Accepted Payment Methods & Badges",
                    "why": "Clarifying payment options prevents late-funnel friction and reassures mobile buyers.",
                    "impact": "MEDIUM",
                    "effort": "LOW",
                    "faq_q": "What payment methods do you accept?",
                    "faq_a": "We accept all major credit cards (Visa, MasterCard, Amex), PayPal, Apple Pay, and Google Pay.",
                },
                {
                    "id": "ECOM-Q5",
                    "question": "How can customers track orders or contact support?",
                    "prompt": "How can I track my package or contact customer support for {brand}?",
                    "regex_strong": r"(?:track order|track my package|order status|contact support|customer service|help desk|live chat)",
                    "keywords_strong": ["track order", "order status", "customer support", "help center", "contact us"],
                    "keywords_partial": ["support", "help", "contact"],
                    "ai_risk": "AI post-purchase assistants cannot resolve order status inquiries, resulting in support tickets.",
                    "action_title": "Provide Order Tracking & Dedicated Support Channels",
                    "why": "Self-service tracking reduces customer service overhead and boosts repeat purchase confidence.",
                    "impact": "HIGH",
                    "effort": "MEDIUM",
                    "faq_q": "How do I track my order?",
                    "faq_a": "Once your order ships, you will receive a tracking link via email. You can also track your status directly in your account dashboard.",
                },
            ],
        },
        "SAAS_TECH": {
            "label": "Software & Technology",
            "schema_types": {"SoftwareApplication", "TechArticle", "APIReference"},
            "url_keywords": ["docs", "api", "pricing", "features", "solutions", "integrations", "platform", "changelog", "auth"],
            "text_keywords": ["api", "sdk", "saas", "pricing", "free trial", "documentation", "integrations", "uptime", "enterprise", "developer"],
            "questions": [
                {
                    "id": "SAAS-Q1",
                    "question": "What are the subscription pricing tiers and plan differences?",
                    "prompt": "What are the pricing tiers for {brand} and what features are included in each?",
                    "regex_strong": r"(?:free tier|per month|billed annually|\$\d+\s*/\s*(?:mo|month|seat|user)|pricing plans|tier)",
                    "keywords_strong": ["pricing", "starter plan", "pro plan", "enterprise plan", "per user", "billed annually"],
                    "keywords_partial": ["pricing", "plans", "costs"],
                    "ai_risk": "B2B procurement AI tools cannot assess cost feasibility and will skip your product in vendor analyses.",
                    "action_title": "Publish Transparent Pricing Tiers & Feature Matrix",
                    "why": "Clear pricing tables allow automated procurement tools to quickly qualify your platform.",
                    "impact": "HIGH",
                    "effort": "MEDIUM",
                    "faq_q": "What pricing plans do you offer?",
                    "faq_a": "We offer flexible tiers: Starter at $29/mo, Professional at $79/mo, and custom Enterprise solutions for large teams.",
                },
                {
                    "id": "SAAS-Q2",
                    "question": "Is there a free trial, free plan, or interactive demo available?",
                    "prompt": "Can I try {brand} for free or book a product demo?",
                    "regex_strong": r"(?:free trial|start free|try for free|14-day trial|book a demo|request demo|no credit card required)",
                    "keywords_strong": ["free trial", "book a demo", "try free", "interactive demo", "sandbox"],
                    "keywords_partial": ["trial", "demo", "start"],
                    "ai_risk": "Prospects evaluating low-risk adoption will be directed to competitors offering frictionless trials.",
                    "action_title": "Clarify Free Trial Duration & Demo Availability",
                    "why": "Eliminating signup ambiguity directly increases lead capture and self-serve onboarding.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "Do you offer a free trial?",
                    "faq_a": "Yes! We offer a 14-day free trial with full feature access and no credit card required.",
                },
                {
                    "id": "SAAS-Q3",
                    "question": "What third-party platforms and integrations are supported?",
                    "prompt": "What software and tools does {brand} integrate with (e.g., Slack, Zapier, Salesforce)?",
                    "regex_strong": r"(?:integrations?|connects with|zapier|slack|github|salesforce|webhook|rest api|export to)",
                    "keywords_strong": ["integrations", "connected apps", "webhooks", "slack integration", "zapier", "api integration"],
                    "keywords_partial": ["integrates", "connect", "tools"],
                    "ai_risk": "Architects asking 'Does X integrate with our stack?' will assume non-compatibility.",
                    "action_title": "Document Ecosystem Integrations & Webhook Support",
                    "why": "Integration capability is a primary filter when software buyers search conversational engines.",
                    "impact": "HIGH",
                    "effort": "MEDIUM",
                    "faq_q": "What tools and platforms do you integrate with?",
                    "faq_a": "Our platform natively integrates with Slack, GitHub, Salesforce, and over 1,000+ apps via Zapier and webhooks.",
                },
                {
                    "id": "SAAS-Q4",
                    "question": "Is there accessible developer or API documentation available?",
                    "prompt": "Where can I find API documentation, SDKs, or developer guides for {brand}?",
                    "regex_strong": r"(?:api reference|developer docs|curl|sdk|endpoint|authentication|bearer token|docs\.[a-z]+)",
                    "keywords_strong": ["api reference", "developer documentation", "sdk", "rest api", "endpoints"],
                    "keywords_partial": ["docs", "api", "guide"],
                    "ai_risk": "AI coding assistants (GitHub Copilot, Cursor) cannot generate code integrations against your system.",
                    "action_title": "Expose Public API Reference & Developer Guides",
                    "why": "Machine agents require clean endpoint specs and code examples to integrate autonomously.",
                    "impact": "HIGH",
                    "effort": "HIGH",
                    "faq_q": "Do you provide an API for developers?",
                    "faq_a": "Yes, we provide a full REST API with comprehensive endpoint documentation and client SDKs.",
                },
                {
                    "id": "SAAS-Q5",
                    "question": "What security standards, compliance (GDPR/SOC2), and data protections are in place?",
                    "prompt": "Is {brand} SOC2 compliant, GDPR compliant, and how is customer data secured?",
                    "regex_strong": r"(?:soc\s*2|gdpr|hipaa|iso\s*27001|encryption at rest|end-to-end encryption|privacy policy|data security)",
                    "keywords_strong": ["soc 2", "gdpr compliant", "encryption", "iso 27001", "data privacy", "security posture"],
                    "keywords_partial": ["security", "privacy", "compliance"],
                    "ai_risk": "Enterprise procurement checks will immediately disqualify products lacking public security verification.",
                    "action_title": "Detail Security Standards & Compliance Certifications",
                    "why": "Security and privacy documentation is the critical hurdle for enterprise software contracts.",
                    "impact": "HIGH",
                    "effort": "MEDIUM",
                    "faq_q": "Is our data secure and compliant?",
                    "faq_a": "Yes. We maintain SOC 2 Type II compliance, full GDPR adherence, and 256-bit AES encryption at rest and in transit.",
                },
            ],
        },
        "HEALTHCARE": {
            "label": "Healthcare & Medical",
            "schema_types": {"MedicalOrganization", "Physician", "Hospital", "MedicalClinic", "Dentist"},
            "url_keywords": ["doctor", "clinic", "patient", "appointment", "treatment", "health", "dental", "medical"],
            "text_keywords": ["doctor", "clinic", "physician", "patient", "appointment", "treatment", "therapy", "medical", "insurance"],
            "questions": [
                {
                    "id": "HLTH-Q1",
                    "question": "What medical services and clinical specialties are provided?",
                    "prompt": "What treatments and medical specialties does {brand} offer?",
                    "regex_strong": r"(?:services offered|specialties|treatments|clinical care|pediatric|cardiology|orthopedic|dental|therapy)",
                    "keywords_strong": ["specialties", "medical services", "treatments", "procedures", "clinical care"],
                    "keywords_partial": ["care", "treatment", "doctor"],
                    "ai_risk": "Patients querying medical assistants for treatment options will be redirected elsewhere.",
                    "action_title": "List Medical Specialties & Specific Procedures",
                    "why": "Patients search for targeted symptoms and specific clinical treatments.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "What services do you provide?",
                    "faq_a": "We specialize in [Clinical Specialties, e.g., preventive care, specialized treatments, and diagnostic evaluations].",
                },
                {
                    "id": "HLTH-Q2",
                    "question": "How can patients schedule an appointment or consultation?",
                    "prompt": "How do I book an appointment with {brand}?",
                    "regex_strong": r"(?:book an appointment|schedule appointment|request consultation|online booking|call to schedule)",
                    "keywords_strong": ["book appointment", "schedule consultation", "patient portal", "online appointment"],
                    "keywords_partial": ["appointment", "booking", "schedule"],
                    "ai_risk": "AI healthcare navigators will fail to guide patients through booking.",
                    "action_title": "Offer Direct Online Appointment Scheduling",
                    "why": "Online booking significantly cuts intake phone time and captures after-hours appointments.",
                    "impact": "HIGH",
                    "effort": "MEDIUM",
                    "faq_q": "How can I book an appointment?",
                    "faq_a": "You can schedule online through our appointment portal or by calling our desk at [Phone Number].",
                },
                {
                    "id": "HLTH-Q3",
                    "question": "What insurance plans and payment options are accepted?",
                    "prompt": "Does {brand} accept my insurance plan or offer payment assistance?",
                    "regex_strong": r"(?:insurance accepted|in-network|medicare|medicaid|copay|payment plans|hsa|fsa)",
                    "keywords_strong": ["insurance accepted", "in-network providers", "copay", "medicare", "fsa/hsa accepted"],
                    "keywords_partial": ["insurance", "coverage", "payment"],
                    "ai_risk": "Patients will hesitate to visit if AI cannot verify in-network coverage.",
                    "action_title": "Clarify In-Network Insurance Carriers & Payment Options",
                    "why": "Insurance coverage is the primary deciding factor for patient provider selection.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "What insurance plans do you accept?",
                    "faq_a": "We are in-network with most major insurance carriers including Blue Cross, Aetna, Cigna, and Medicare.",
                },
                {
                    "id": "HLTH-Q4",
                    "question": "Where is the clinic located and what are the clinic hours?",
                    "prompt": "Where is {brand} located and what are the clinic operating hours?",
                    "regex_strong": r"(?:clinic hours|office hours|suite|medical center|parking for patients|handicap accessible)",
                    "keywords_strong": ["clinic hours", "office location", "patient parking", "handicap access"],
                    "keywords_partial": ["hours", "location", "address"],
                    "ai_risk": "Patients may arrive when closed or struggle with accessible parking details.",
                    "action_title": "Publish Clinic Hours & Accessibility Information",
                    "why": "Physical logistics and accessibility are paramount for patient trust.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "What are your clinic hours and location?",
                    "faq_a": "Our clinic is located at [Address] and is open Monday through Friday from 8:00 AM to 5:00 PM.",
                },
                {
                    "id": "HLTH-Q5",
                    "question": "What are the credentials and qualifications of the medical staff?",
                    "prompt": "What are the qualifications of the doctors at {brand}?",
                    "regex_strong": r"(?:board certified|md\b|do\b|dds\b|phd\b|residency|fellowship|medical school|licensed)",
                    "keywords_strong": ["board certified", "physician credentials", "medical background", "residency"],
                    "keywords_partial": ["credentials", "experience", "doctor"],
                    "ai_risk": "Medical AI assistants assessing authority (E-E-A-T) will rank uncredentialed providers lower.",
                    "action_title": "Highlight Practitioner Board Certifications & Credentials",
                    "why": "High medical authority requires explicit proof of practitioner licenses and certifications.",
                    "impact": "MEDIUM",
                    "effort": "LOW",
                    "faq_q": "Are your practitioners board-certified?",
                    "faq_a": "Yes, our medical team consists of board-certified physicians with extensive clinical training.",
                },
            ],
        },
        "EDUCATION": {
            "label": "Education & Academy",
            "schema_types": {"EducationalOrganization", "Course", "CollegeOrUniversity", "School"},
            "url_keywords": ["courses", "programs", "admissions", "tuition", "faculty", "curriculum", "academy", "campus", "degrees"],
            "text_keywords": ["course", "degree", "tuition", "admissions", "curriculum", "faculty", "students", "enroll", "scholarships"],
            "questions": [
                {
                    "id": "EDU-Q1",
                    "question": "What academic programs, degrees, or courses are offered?",
                    "prompt": "What courses and degree programs does {brand} offer?",
                    "regex_strong": r"(?:degree programs|courses offered|curriculum|major|certificate|undergraduate|postgraduate|syllabus)",
                    "keywords_strong": ["degree programs", "courses offered", "curriculum overview", "majors and minors"],
                    "keywords_partial": ["programs", "courses", "classes"],
                    "ai_risk": "Academic advising AI bots cannot recommend suitable courses or degrees.",
                    "action_title": "Publish Comprehensive Program Catalog & Syllabi",
                    "why": "Prospective students search for specific curricula and accredited degrees.",
                    "impact": "HIGH",
                    "effort": "MEDIUM",
                    "faq_q": "What programs and courses are available?",
                    "faq_a": "We offer accredited programs ranging from professional certificates to comprehensive degree curricula.",
                },
                {
                    "id": "EDU-Q2",
                    "question": "What are the admission requirements, eligibility criteria, and deadlines?",
                    "prompt": "How do I apply to {brand} and what are the admission deadlines?",
                    "regex_strong": r"(?:admission requirements|application deadline|how to apply|eligibility|prerequisites|gpa requirement)",
                    "keywords_strong": ["admission requirements", "application deadline", "eligibility criteria", "how to apply"],
                    "keywords_partial": ["admission", "apply", "deadline"],
                    "ai_risk": "Applicants relying on AI guidance will miss critical application cutoffs.",
                    "action_title": "Outline Step-by-Step Admissions & Application Deadlines",
                    "why": "Clear admission milestones streamline student onboarding and application volume.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "What are the application requirements and deadlines?",
                    "faq_a": "Applicants must submit their application form, transcripts, and personal statement by [Application Deadline].",
                },
                {
                    "id": "EDU-Q3",
                    "question": "How much is tuition, fees, and are scholarships available?",
                    "prompt": "How much does tuition cost at {brand} and what financial aid is available?",
                    "regex_strong": r"(?:tuition fee|financial aid|scholarships|cost of attendance|grants|payment plan|per credit)",
                    "keywords_strong": ["tuition cost", "financial aid", "scholarships", "cost of attendance", "payment options"],
                    "keywords_partial": ["tuition", "fees", "cost"],
                    "ai_risk": "Cost comparison AI engines will exclude the institution due to hidden pricing.",
                    "action_title": "Expose Tuition Rates & Financial Aid Options",
                    "why": "Tuition transparency is the single most queried topic by prospective students.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "How much is tuition and is financial aid available?",
                    "faq_a": "Tuition is estimated at $[Amount] per term, with competitive scholarships and federal financial aid available.",
                },
                {
                    "id": "EDU-Q4",
                    "question": "Is the institution accredited and recognized?",
                    "prompt": "Is {brand} accredited and recognized by educational authorities?",
                    "regex_strong": r"(?:accredited by|accreditation|recognized by|state approved|certified institution)",
                    "keywords_strong": ["accredited by", "institutional accreditation", "recognized credential"],
                    "keywords_partial": ["accreditation", "certified", "licensed"],
                    "ai_risk": "AI counselors will flag unverified degree status as a risk to students.",
                    "action_title": "Display Accreditation Bodies & Certification Badges",
                    "why": "Accreditation guarantees transferability of credits and degree legitimacy.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "Is your institution accredited?",
                    "faq_a": "Yes, we are fully accredited by [Accrediting Agency / Education Board].",
                },
                {
                    "id": "EDU-Q5",
                    "question": "Where is the campus located and are online/hybrid classes offered?",
                    "prompt": "Does {brand} offer online classes and where is the campus located?",
                    "regex_strong": r"(?:online classes|remote learning|hybrid program|campus location|campus tour|distance education)",
                    "keywords_strong": ["online learning", "campus location", "hybrid programs", "distance education"],
                    "keywords_partial": ["online", "campus", "remote"],
                    "ai_risk": "Remote students querying AI will assume classes are strictly physical.",
                    "action_title": "Clarify Online vs On-Campus Learning Formats",
                    "why": "Modern learners demand clarity on virtual flexibility and physical locations.",
                    "impact": "MEDIUM",
                    "effort": "LOW",
                    "faq_q": "Do you offer remote or online learning options?",
                    "faq_a": "Yes! We provide flexible hybrid and 100% online coursework alongside our physical campus facilities.",
                },
            ],
        },
        "GENERAL_BUSINESS": {
            "label": "General Business & Services",
            "schema_types": {"Organization", "LocalBusiness", "ProfessionalService"},
            "url_keywords": ["about", "services", "contact", "pricing", "team"],
            "text_keywords": ["services", "company", "clients", "contact", "solutions", "team", "business"],
            "questions": [
                {
                    "id": "BIZ-Q1",
                    "question": "What primary services or products does the business provide?",
                    "prompt": "What core services and solutions does {brand} provide?",
                    "regex_strong": r"(?:our services|what we do|core capabilities|products and services|solutions we offer)",
                    "keywords_strong": ["our services", "what we do", "core solutions", "capabilities", "expert services"],
                    "keywords_partial": ["services", "products", "solutions"],
                    "ai_risk": "AI search engines cannot summarize what the business does, resulting in missed customer referrals.",
                    "action_title": "Publish a Concise 'What We Do' Service Overview",
                    "why": "Clear value propositions are critical for AI categorization and search indexing.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "What services do you offer?",
                    "faq_a": "We specialize in [Core Services / Solutions], helping our clients achieve [Primary Client Benefit].",
                },
                {
                    "id": "BIZ-Q2",
                    "question": "Who is the ideal customer or target audience for these services?",
                    "prompt": "Who are the services of {brand} designed for?",
                    "regex_strong": r"(?:who we serve|ideal for|tailored for|industries we serve|our clients|target market)",
                    "keywords_strong": ["who we serve", "tailored for", "ideal for", "industries we serve"],
                    "keywords_partial": ["clients", "customers", "businesses"],
                    "ai_risk": "AI intent-matching algorithms will fail to route qualified leads to your business.",
                    "action_title": "Specify Target Audience & Client Personas",
                    "why": "Defining who you serve helps AI match specific customer problems to your brand.",
                    "impact": "MEDIUM",
                    "effort": "LOW",
                    "faq_q": "Who do you typically work with?",
                    "faq_a": "We primarily work with [Target Audience, e.g., small-to-medium businesses, startups, and enterprise teams].",
                },
                {
                    "id": "BIZ-Q3",
                    "question": "How can clients request a quote, consultation, or pricing estimate?",
                    "prompt": "How can I get a quote or schedule a consultation with {brand}?",
                    "regex_strong": r"(?:request a quote|get an estimate|free consultation|book a call|schedule a consultation)",
                    "keywords_strong": ["request a quote", "get a quote", "free consultation", "pricing estimate"],
                    "keywords_partial": ["quote", "consultation", "estimate"],
                    "ai_risk": "Leads asking AI 'How do I hire X?' hit a dead end and move to competitors.",
                    "action_title": "Provide a Clear Quote Request or Consultation Channel",
                    "why": "Low-friction consultation booking turns AI discoverability into direct sales pipeline.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "How can I get a quote for my project?",
                    "faq_a": "You can request a free custom quote by filling out our online form or contacting our team directly.",
                },
                {
                    "id": "BIZ-Q4",
                    "question": "Where is the business located and what regions/areas are served?",
                    "prompt": "What regions or locations does {brand} serve?",
                    "regex_strong": r"(?:service area|areas we serve|nationwide|worldwide|headquarters|office location|serving clients in)",
                    "keywords_strong": ["service area", "serving nationwide", "headquartered in", "areas we serve"],
                    "keywords_partial": ["location", "office", "serving"],
                    "ai_risk": "Geo-targeted AI queries will assume your business does not serve the user's location.",
                    "action_title": "Clarify Geographic Service Areas & Headquarters",
                    "why": "Search engines heavily weight regional proximity when generating local recommendations.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "What areas do you serve?",
                    "faq_a": "We are headquartered in [Location] and proudly serve clients [Locally / Regionally / Nationwide / Globally].",
                },
                {
                    "id": "BIZ-Q5",
                    "question": "What customer testimonials, case studies, or proof of credibility exist?",
                    "prompt": "What do past clients say about {brand} and are there case studies?",
                    "regex_strong": r"(?:testimonials|case studies|client reviews|our work|trusted by|proven results|portfolio)",
                    "keywords_strong": ["testimonials", "case studies", "client reviews", "trusted by", "customer success"],
                    "keywords_partial": ["reviews", "clients", "portfolio"],
                    "ai_risk": "AI authority scoring (E-E-A-T) lacks social proof, reducing citation priority.",
                    "action_title": "Showcase Client Testimonials & Proven Case Studies",
                    "why": "Documented client success is the strongest signal for AI trust and conversion.",
                    "impact": "MEDIUM",
                    "effort": "MEDIUM",
                    "faq_q": "Do you have client reviews or references?",
                    "faq_a": "Yes, explore our client testimonials and case study portfolio on our website to see real results.",
                },
            ],
        },
    }

    def analyze(self, root_url: str, page_data_map: Dict[str, Any], brand_name: Optional[str] = None) -> MarketIntelligenceReport:
        brand = brand_name or self._infer_brand_name(root_url, page_data_map)
        detected_ind, conf = self._detect_industry(page_data_map)
        ind_def = self.INDUSTRY_DEFINITIONS.get(detected_ind, self.INDUSTRY_DEFINITIONS["GENERAL_BUSINESS"])

        aggregated_text = self._aggregate_text(page_data_map)
        all_json_ld_types = self._aggregate_json_ld_types(page_data_map)

        question_results: List[QuestionCheckResult] = []
        clear_count = 0
        partial_count = 0
        missing_count = 0
        question_gaps: List[str] = []

        for q_def in ind_def["questions"]:
            status, evidence = self._evaluate_question(q_def, aggregated_text, all_json_ld_types)
            prompt = q_def["prompt"].format(brand=brand)

            if status == "ANSWERABLE":
                clear_count += 1
            elif status == "PARTIAL":
                partial_count += 1
                question_gaps.append(q_def["question"])
            else:
                missing_count += 1
                question_gaps.append(q_def["question"])

            faq_snippet = {
                "@context": "https://schema.org",
                "@type": "Question",
                "name": q_def["faq_q"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": q_def["faq_a"],
                },
            }

            question_results.append(
                QuestionCheckResult(
                    id=q_def["id"],
                    question=q_def["question"],
                    simulated_prompt=prompt,
                    status=status,
                    evidence_found=evidence,
                    ai_risk=q_def["ai_risk"] if status != "ANSWERABLE" else "None — verified clear signal for AI assistants.",
                    faq_schema_snippet=faq_snippet,
                    impact=q_def["impact"],
                    effort=q_def["effort"],
                )
            )

        total_q = len(ind_def["questions"])
        coverage_pct = round(((clear_count * 1.0 + partial_count * 0.5) / max(1, total_q)) * 100)
        roadmap = self._build_roadmap(question_results, ind_def["questions"])

        return MarketIntelligenceReport(
            detected_industry=detected_ind,
            industry_label=ind_def["label"],
            confidence=conf,
            market_question_coverage_pct=coverage_pct,
            questions_checked=total_q,
            clear_count=clear_count,
            partial_count=partial_count,
            missing_count=missing_count,
            questions=question_results,
            question_gaps=question_gaps,
            roadmap=roadmap,
        )

    def _detect_industry(self, page_data_map: Dict[str, Any]) -> (str, float):
        if not page_data_map:
            return "GENERAL_BUSINESS", 0.50

        scores: Dict[str, float] = {ind: 0.0 for ind in self.INDUSTRY_DEFINITIONS if ind != "GENERAL_BUSINESS"}

        for url, pdata in page_data_map.items():
            url_lower = url.lower()
            text_lower = (getattr(pdata, "meta_description", "") or "").lower() + " " + (getattr(pdata, "title", "") or "").lower()
            json_types = set(getattr(pdata, "json_ld_types", []) or [])

            for ind, defs in self.INDUSTRY_DEFINITIONS.items():
                if ind == "GENERAL_BUSINESS":
                    continue

                if json_types.intersection(defs["schema_types"]):
                    scores[ind] += 4.0

                for kw in defs["url_keywords"]:
                    if kw in url_lower:
                        scores[ind] += 1.5

                for kw in defs["text_keywords"]:
                    if kw in text_lower:
                        scores[ind] += 0.8

        best_ind = max(scores, key=scores.get)
        best_score = scores[best_ind]

        if best_score >= 3.0:
            confidence = min(0.95, 0.60 + (best_score * 0.05))
            return best_ind, round(confidence, 2)

        return "GENERAL_BUSINESS", 0.80

    def _evaluate_question(self, q_def: Dict[str, Any], aggregated_text: str, json_ld_types: List[str]) -> (str, str):
        text_lower = aggregated_text.lower()

        regex_pat = q_def.get("regex_strong")
        if regex_pat and re.search(regex_pat, text_lower, re.IGNORECASE):
            m = re.search(regex_pat, text_lower, re.IGNORECASE).group(0)[:60]
            return "ANSWERABLE", f"Found explicit text pattern: '{m}'"

        for kw in q_def.get("keywords_strong", []):
            if kw in text_lower:
                return "ANSWERABLE", f"Found authoritative keyword phrase: '{kw}'"

        for pkw in q_def.get("keywords_partial", []):
            if pkw in text_lower:
                return "PARTIAL", f"Found partial contextual mention: '{pkw}', but lacks explicit details."

        return "NOT_ANSWERABLE", "No relevant content, keywords, or schema detected for this question."

    def _build_roadmap(self, results: List[QuestionCheckResult], q_defs: List[Dict[str, Any]]) -> List[SmartRoadmapItem]:
        gaps = [r for r in results if r.status != "ANSWERABLE"]

        def sort_key(item: QuestionCheckResult):
            impact_weight = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(item.impact, 3)
            effort_weight = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}.get(item.effort, 3)
            return (impact_weight, effort_weight)

        gaps.sort(key=sort_key)

        roadmap: List[SmartRoadmapItem] = []
        q_dict = {q["id"]: q for q in q_defs}

        for idx, gap in enumerate(gaps[:5], start=1):
            matching_q = q_dict.get(gap.id, {})
            roadmap.append(
                SmartRoadmapItem(
                    priority=idx,
                    action_title=matching_q.get("action_title", f"Address {gap.question}"),
                    why=matching_q.get("why", gap.ai_risk),
                    impact=gap.impact,
                    effort=gap.effort,
                    suggested_faq_json_ld=gap.faq_schema_snippet,
                )
            )

        return roadmap

    def _aggregate_text(self, page_data_map: Dict[str, Any]) -> str:
        chunks: List[str] = []
        for url, pdata in page_data_map.items():
            if hasattr(pdata, "title") and pdata.title:
                chunks.append(pdata.title)
            if hasattr(pdata, "meta_description") and pdata.meta_description:
                chunks.append(pdata.meta_description)
            if hasattr(pdata, "h1_tags") and pdata.h1_tags:
                chunks.extend(pdata.h1_tags)
            if hasattr(pdata, "button_cta_labels") and pdata.button_cta_labels:
                chunks.extend(pdata.button_cta_labels)
            if hasattr(pdata, "footer_text") and pdata.footer_text:
                chunks.append(pdata.footer_text)
        return " ".join(chunks)

    def _aggregate_json_ld_types(self, page_data_map: Dict[str, Any]) -> List[str]:
        types: List[str] = []
        for pdata in page_data_map.values():
            types.extend(getattr(pdata, "json_ld_types", []) or [])
        return list(set(types))

    def _infer_brand_name(self, root_url: str, page_data_map: Dict[str, Any]) -> str:
        for pdata in page_data_map.values():
            if getattr(pdata, "page_title_brand", None):
                return pdata.page_title_brand

        netloc = urlparse(root_url).netloc.lower()
        parts = netloc.split(".")
        if len(parts) >= 2:
            return parts[-2].capitalize()
        return "Your Brand"
