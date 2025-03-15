import pandas as pd
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, CrossEncoder
from sklearn.metrics.pairwise import cosine_similarity
import html
import json
import re

class MovieEmbedder:
    def __init__(self, df, embed_model="sentence-transformers/all-mpnet-base-v2"):  
        """Initialize the MovieEmbedder class."""
        self.embed_model = SentenceTransformer(embed_model)
        self.df = df

    @staticmethod
    def safe_parse(value, default=None):
        """Safely parse a JSON-like string into a Python object."""
        if pd.isna(value) or not isinstance(value, str):
            return default if default is not None else {}
        try:
            return json.loads(value)
        except (ValueError, SyntaxError):
            return default if default is not None else {}

    @staticmethod
    def clean_text(text):
        """Remove HTML tags and extra whitespace from text."""
        text = re.sub(r"<.*?>", "", text)  # Remove HTML tags
        text = text.replace("\r", " ").replace("\n", " ")  # Remove newlines
        return text.strip()

    def format_entry(self, row):
        """Format metadata into a structured text description."""
        parts = []

        if pd.isna(row.tmdb_id):
            return None
        
        tmdb_info = self.safe_parse(row.get("tmdb_info", "{}"))
        tmdb_keywords = self.safe_parse(row.get("tmdb_keywords", "{}"))
        tmdb_reviews = self.safe_parse(row.get("tmdb_reviews", "{}"))
        tmdb_credits = self.safe_parse(row.get("tmdb_credits", "{}"))
        
        title = tmdb_info.get("title", "This")
        genres = [genre["name"] for genre in tmdb_info.get("genres", [])]
        if title and genres:
            parts.append(f"{title} is a {', '.join(genres)} film.")
        elif title:
            parts.append(f"{title} is a film.")
        elif genres:
            parts.append(f"This is a {', '.join(genres)} film.")
        
        # Content rating (if available)
        if "content_rating" in tmdb_info:
            parts.append(f"It has a parental guidance content rating of {tmdb_info['content_rating']}.")

        # Keywords
        keywords = [kw["name"] for kw in tmdb_keywords.get("keywords", [])]
        if keywords:
            parts.append(f"Important themes include: {', '.join(keywords)}.")

        # Director and cast
        directors = tmdb_credits.get("directors", [])
        cast = tmdb_credits.get("cast", [])[:5]  # Limit to top 5 actors
        if directors and cast:
            parts.append(f"It is directed by {', '.join(directors)} and stars {', '.join(cast)}.")
        elif directors:
            parts.append(f"It is directed by {', '.join(directors)}.")
        elif cast:
            parts.append(f"It stars {', '.join(cast)}.")

        # Ratings
        rating = tmdb_info.get("vote_average")
        rating_count = tmdb_info.get("vote_count")
        if rating and rating_count:
            parts.append(f"The movie has a rating of {rating} based on {rating_count} reviews.")

        # Plot (Required field)
        plot = tmdb_info.get("overview", "").strip()
        if plot:
            parts.append(f"Plot: {self.clean_text(plot)}")
        else:
            return None  # Skip entry if plot is missing

        # Reviews (sorted by shortest first)
        reviews = tmdb_reviews.get("results", [])
        sorted_reviews = sorted(reviews, key=lambda r: len(r.get("content", "")))

        review_texts = []
        for review in sorted_reviews:
            content = self.clean_text(review.get("content", ""))
            sentences = re.split(r"(?<=[.!?])\s+", content)  # Split into sentences
            review_excerpt = " ".join(sentences[:5])  # Take up to 5 sentences
            if review_excerpt:
                review_texts.append(f'A reviewer said: "{review_excerpt}"')

        if review_texts:
            parts.append(" ".join(review_texts))

        return " ".join(parts)

    def prepare_text(self):
        """Apply formatting to dataframe rows and filter out missing entries."""
        self.df["text_to_embed"] = self.df.apply(self.format_entry, axis=1)
        self.df = self.df.dropna(subset=["text_to_embed"])  # Drop any rows where formatting failed

    def generate_embeddings(self):
        """Generate sentence embeddings and store them in the DataFrame."""
        tqdm.pandas(desc="Embedding movies")
        self.df["embedding"] = self.df["text_to_embed"].progress_apply(
            lambda x: self.embed_model.encode(x).tolist()
        )

    def save_embeddings(self, output_path):
        """Save the DataFrame with embeddings to a CSV file."""
        self.df.to_csv(output_path, index=False)
        print(f"✅ Movie dataset saved to {output_path}")

    def load_embeddings(self, csv_path):
        """Load movie embeddings from a CSV file."""
        self.df = pd.read_csv(csv_path)
        self.df["embedding"] = self.df["embedding"].apply(lambda x: np.array(eval(x)))

    def get_mood_recommendations(self, user_query, top_k=5, rerank_top_n=20):
        """
        Retrieves movies using embedding similarity and reranks them with a cross-encoder.
        Now reranks using `text_to_embed` for consistency.
        """
        if self.df is None or "embedding" not in self.df.columns:
            raise ValueError("❌ Movie embeddings are not loaded. Run `load_embeddings()` first.")

        # Encode user query
        query_embedding = self.embed_model.encode(user_query)

        # Compute cosine similarity
        similarities = cosine_similarity([query_embedding], np.stack(self.df["embedding"].values))[0]
        self.df["similarity"] = similarities

        return self.df
