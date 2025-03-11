import pandas as pd
import numpy as np
import ast
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, CrossEncoder
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi  # BM25 for lexical search
import html


class MovieEmbedder:
    def __init__(
        self,
        df,
        embed_model="sentence-transformers/all-mpnet-base-v2",
        rerank_model="BAAI/bge-reranker-large",
        hybrid_weight=0.5,
    ):  
        """Initialize the MovieEmbedder class."""
        self.embed_model = SentenceTransformer(embed_model)
        self.rerank_model = CrossEncoder(rerank_model)
        self.df = df
        self.hybrid_weight = hybrid_weight  
        self.bm25 = None  

    @staticmethod
    def parse_keywords(keywords):
        """Safely parse keyword lists stored as strings."""
        try:
            parsed = ast.literal_eval(keywords)
            return " ".join(parsed) if isinstance(parsed, list) else ""
        except (ValueError, SyntaxError):
            return ""

    def prepare_text(self):
        """Prepare structured text for embeddings with better formatting. Drops rows where 'plot' is NaN."""
        
        def safe_parse_list(value):
            """Safely parse a list-like string or return an empty list."""
            if pd.isna(value) or not isinstance(value, str):
                return []
            try:
                parsed = ast.literal_eval(value)
                return parsed if isinstance(parsed, list) else []
            except (ValueError, SyntaxError):
                return []

        def clean_director(director):
            """Clean director field, removing list-like artifacts."""
            if isinstance(director, str):
                try:
                    parsed = ast.literal_eval(director)
                    if isinstance(parsed, list):
                        return ", ".join(parsed)  # Convert list to a clean string
                except (ValueError, SyntaxError):
                    pass
            return director.strip()

        def format_entry(row):
            """Format text dynamically for better embeddings."""
            parts = []

            # Movie title and genre
            title = row.get("title", "").strip()
            genres = [g for g in safe_parse_list(row.get("genres", "")) if g.lower() != "back to top"]  # Remove "Back to top"
            title = ''
            if title and genres:
                parts.append(f"{title.title()} is a {', '.join(genres)} film.")
            elif title:
                parts.append(f"{title.title()} is a film.")
            elif genres:
                parts.append(f"This is a {', '.join(genres)} film.")

            # content rating
            content_rating = row.get("content_rating", "")
            if content_rating:
                parts.append(f"It has a parental guidance content rating of {content_rating}.")

            # Keywords
            keywords = self.parse_keywords(row.get("keywords", ""))
            if keywords:
                parts.append(f"Important themes include: {keywords}.")

            # Director and actors
            director = clean_director(row.get("director", ""))
            actors = safe_parse_list(row.get("actors", ""))
            if director and actors:
                parts.append(f"It is directed by {director} and stars {', '.join(actors)}.")
            elif director:
                parts.append(f"It is directed by {director}.")
            elif actors:
                parts.append(f"It stars {', '.join(actors)}.")

            # Rating
            rating = row.get("rating", "")
            rating_count = row.get("rating_count", "")
            if rating and rating_count:
                parts.append(f"The movie has a rating of {rating} based on {rating_count} reviews.")

            # Plot (this is required, so it should not be NaN)
            plot = str(row.get("plot", "")).strip()  # Convert NaN to an empty string
            if plot:
                parts.append(f"Plot: {html.unescape(plot)}")  # Decode HTML entities
            else:
                return None  # If plot is missing, remove this row

            # Keywords
            keywords = self.parse_keywords(row.get("keywords", ""))
            if keywords:
                parts.append(f"Important themes include: {keywords}.")

            return " ".join(parts)

        # Drop rows where 'plot' is NaN before applying transformations
        self.df = self.df.dropna(subset=["plot"])

        # Apply formatting to each row, filtering out any None results
        self.df["text_to_embed"] = self.df.apply(format_entry, axis=1)
        self.df = self.df.dropna(subset=["text_to_embed"])  # Drop any rows where formatting failed


        # Drop rows where 'plot' is NaN before applying transformations
        self.df = self.df.dropna(subset=["plot"])

        # Apply formatting to each row, filtering out any None results
        self.df["text_to_embed"] = self.df.apply(format_entry, axis=1)
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

        # # Select top N candidates for reranking
        # candidates = self.df.nlargest(rerank_top_n, "similarity")

        # # Use `text_to_embed` for reranking (ensures consistency)
        # query_movie_pairs = [(user_query, text) for text in candidates["text_to_embed"].tolist()]
        # rerank_scores = self.rerank_model.predict(query_movie_pairs)

        # # Update candidates with rerank scores and return top_k results
        # candidates["rerank_score"] = rerank_scores
        # results = candidates.nlargest(top_k, "rerank_score")[["title", "plot", "text_to_embed"]]

        return self.df