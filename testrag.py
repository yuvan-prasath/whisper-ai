from rag import ingest_document, retrieve_context

# Step 1 - Ingest your document
print("Ingesting document...")
ingest_document("company_info.txt", org_id="neumann")

# Step 2 - Test retrieval
print("\nTesting retrieval...")

questions = [
    "What is HireLens?",
    "How much does Neumann Synapse cost?",
    "What languages does the healthcare assistant support?",
    "Where is the company located?"
]

for question in questions:
    print(f"\nQuestion: {question}")
    context = retrieve_context(question, org_id="neumann")
    print(f"Retrieved context:\n{context}")
    print("-" * 50)