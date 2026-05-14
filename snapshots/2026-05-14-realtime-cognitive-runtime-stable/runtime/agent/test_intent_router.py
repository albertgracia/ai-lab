from runtime.agent.intent_router import detect_intent


tests = [

    "Analiza arquitectura del AI-LAB",

    "Implementa script python para routing",

    "Reinicia docker y revisa logs",

    "Investiga memoria semántica",

    "Audita governance runtime",
]


for t in tests:

    result = detect_intent(t)

    print("\n====================")
    print("PROMPT:", t)
    print("INTENT:", result.intent)
    print("MODE:", result.mode)
    print("CAPABILITIES:", result.capabilities)
    print("TAGS:", result.context_tags)
    print("MODEL:", result.suggested_model)
