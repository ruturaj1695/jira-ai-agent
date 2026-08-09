"""Ingest markdown/text knowledge files into the Chroma knowledge base."""

import argparse

from rtb_jira_ai_agent.ingestion import ingest_text_file


parser = argparse.ArgumentParser(description="Ingest a text or markdown file into Chroma")
parser.add_argument("path", help="Path to the .txt or .md file")
args = parser.parse_args()

count = ingest_text_file(args.path)
print(f"Indexed {count} chunks from {args.path}")
