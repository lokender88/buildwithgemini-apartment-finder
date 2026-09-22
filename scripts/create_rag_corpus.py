"""Create serverless Vertex AI RAG Engine corpus and import Gutenberg dataset.

Follows the rag-engine-setup skill guide for serverless Vertex AI RAG corpus creation.
"""

import vertexai
from vertexai.preview import rag

PROJECT_ID = "qwiklabs-gcp-01-2679c4d7a8a5"
LOCATION = "us-central1"
GCS_PATH = "gs://apartment-finder-assets-qwiklabs-gcp-01-2679c4d7a8a5/rag/pg49513.txt"

PARSING_PROMPT = (
    "Extract the individual useful facts and information described in this text. "
    "Ignore and omit all metadata, boilerplate, and legal notices. "
    "Output clean, self-contained prose."
)


def main():
    print(f"Initializing Vertex AI for project={PROJECT_ID}, location={LOCATION}...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # 1. Create Serverless RAG Corpus
    print("Creating RAG Corpus with publisher_model='publishers/google/models/text-embedding-005'...")
    corpus = rag.create_corpus(
        display_name="apartment-finder-rag-corpus",
        embedding_model_config=rag.EmbeddingModelConfig(
            publisher_model="publishers/google/models/text-embedding-005"
        ),
    )
    corpus_name = corpus.name
    print(f"\n==========================================")
    print(f"CREATED CORPUS NAME: {corpus_name}")
    print(f"==========================================\n")

    # 2. Import and index document
    print(f"Importing and indexing '{GCS_PATH}' into corpus...")
    resp = rag.import_files(
        corpus_name=corpus_name,
        paths=[GCS_PATH],
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
        ),
        llm_parser=rag.LlmParserConfig(
            model_name="gemini-2.5-flash",
            custom_parsing_prompt=PARSING_PROMPT,
        ),
    )
    print(f"Import completed! Imported files count: {resp.imported_rag_files_count}")

    # Output the corpus name to a text file for easy reference
    with open("scripts/corpus_info.txt", "w") as f:
        f.write(corpus_name)
    print("Saved corpus name to scripts/corpus_info.txt")


if __name__ == "__main__":
    main()
