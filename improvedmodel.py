from transformers import pipeline, AutoModelForQuestionAnswering, AutoTokenizer

# Load a more advanced pre-trained QA model
model_name = "bert-large-uncased-whole-word-masking-finetuned-squad"
qa_pipeline = pipeline("question-answering", model="./fine_tuned_model", tokenizer="./fine_tuned_model")
ner_pipeline = pipeline("ner", grouped_entities=True)  # For named entity recognition

def process_text(input_text):
    # Define the questions for QA
    questions = [
        "Who is mentioned in the text?",
        "What is the date?",
        "Where is the location?",
        "What is the sentiment of the text?"
    ]
    
    # Placeholder for results
    results = {}

    # Use QA pipeline for structured questions
    for question in questions:
        try:
            answer = qa_pipeline(question=question, context=input_text)
            if answer['score'] > 0.5:  # Use a confidence threshold
                results[question] = answer['answer']
            else:
                results[question] = "No confident answer found."
        except Exception as e:
            results[question] = f"Error: {e}"
    
    # Use NER pipeline to identify key entities
    entities = ner_pipeline(input_text)
    entity_summary = {entity['entity_group']: entity['word'] for entity in entities}

    # Combine QA results and NER outputs
    results["Named Entities"] = entity_summary

    # Print results
    for question, answer in results.items():
        print(f"{question}: {answer}")

# Example input text
example_text = """
John Doe visited New York City on January 15, 2023. He loved the experience and enjoyed his time at Central Park.
"""

# Process the text
process_text(example_text)
