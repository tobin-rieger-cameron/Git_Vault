import os
import json
import re
import numpy as np
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import openai  # You'll need: pip install openai
from sentence_transformers import SentenceTransformer  # pip install sentence-transformers
import networkx as nx  # pip install networkx
from sklearn.cluster import KMeans  # pip install scikit-learn
from sklearn.metrics.pairwise import cosine_similarity

@dataclass
class Note:
    """Represents an Obsidian note with metadata"""
    path: str
    title: str
    content: str
    tags: List[str]
    links: List[str]
    backlinks: List[str]
    created: datetime
    modified: datetime
    embedding: Optional[np.ndarray] = None

class ObsidianBrain:
    """AI-powered Obsidian vault organizer and query system"""
    
    def __init__(self, vault_path: str, openai_api_key: str = None):
        self.vault_path = Path(vault_path)
        
        # Ensure vault path exists
        if not self.vault_path.exists():
            raise FileNotFoundError(f"Vault path does not exist: {vault_path}")
        
        # Create database path in a writable location
        self.db_path = self.vault_path / ".obsidian_brain.db"
        
        # Ensure the parent directory exists and is writable
        self.vault_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize AI models
        print("Loading sentence transformer model...")
        try:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            print("Model loaded successfully!")
        except Exception as e:
            print(f"Error loading sentence transformer: {e}")
            print("Please install with: pip install sentence-transformers")
            raise
        
        # OpenAI client (optional, for advanced LLM features)
        if openai_api_key:
            openai.api_key = openai_api_key
            self.llm_enabled = True
        else:
            self.llm_enabled = False
            print("Warning: No OpenAI API key provided. LLM features disabled.")
        
        # Initialize database
        self.init_database()
        
        # Load and process vault
        self.notes = {}
        self.knowledge_graph = nx.Graph()
        self.load_vault()
    
    def init_database(self):
        """Initialize SQLite database for storing embeddings and metadata"""
        try:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to database
            self.conn = sqlite3.connect(str(self.db_path))
            cursor = self.conn.cursor()
            print(f"Database initialized at: {self.db_path}")
        except Exception as e:
            print(f"Error initializing database: {e}")
            # Fallback to temp directory
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            self.db_path = temp_dir / "obsidian_brain.db"
            self.conn = sqlite3.connect(str(self.db_path))
            cursor = self.conn.cursor()
            print(f"Using temporary database at: {self.db_path}")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                path TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                tags TEXT,
                links TEXT,
                embedding BLOB,
                created TIMESTAMP,
                modified TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clusters (
                cluster_id INTEGER,
                note_path TEXT,
                FOREIGN KEY (note_path) REFERENCES notes (path)
            )
        ''')
        
        self.conn.commit()
    
    def parse_obsidian_note(self, file_path: Path) -> Note:
        """Parse an Obsidian markdown file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title (filename without extension)
        title = file_path.stem
        
        # Extract tags (both #tag and YAML frontmatter)
        tags = []
        
        # YAML frontmatter tags
        yaml_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if yaml_match:
            yaml_content = yaml_match.group(1)
            tag_match = re.search(r'^tags:\s*\[(.*?)\]', yaml_content, re.MULTILINE)
            if tag_match:
                tags.extend([tag.strip().strip('"\'') for tag in tag_match.group(1).split(',')])
        
        # Inline tags
        inline_tags = re.findall(r'#(\w+)', content)
        tags.extend(inline_tags)
        
        # Extract wikilinks [[note name]]
        links = re.findall(r'\[\[([^\]]+)\]\]', content)
        
        # Get file stats
        stat = file_path.stat()
        created = datetime.fromtimestamp(stat.st_ctime)
        modified = datetime.fromtimestamp(stat.st_mtime)
        
        return Note(
            path=str(file_path),
            title=title,
            content=content,
            tags=list(set(tags)),  # Remove duplicates
            links=links,
            backlinks=[],  # Will be computed later
            created=created,
            modified=modified
        )
    
    def load_vault(self):
        """Load all notes from the Obsidian vault"""
        print(f"Loading vault from {self.vault_path}")
        
        # Find all markdown files
        md_files = list(self.vault_path.rglob("*.md"))
        
        for file_path in md_files:
            # Skip template and system folders
            if any(part.startswith('.') or part.startswith('_') for part in file_path.parts):
                continue
                
            try:
                note = self.parse_obsidian_note(file_path)
                self.notes[note.title] = note
                print(f"Loaded: {note.title}")
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
        
        # Compute backlinks
        self.compute_backlinks()
        
        # Generate embeddings
        self.generate_embeddings()
        
        # Build knowledge graph
        self.build_knowledge_graph()
        
        print(f"Loaded {len(self.notes)} notes")
    
    def compute_backlinks(self):
        """Compute backlinks for all notes"""
        for note in self.notes.values():
            for link in note.links:
                if link in self.notes:
                    self.notes[link].backlinks.append(note.title)
    
    def generate_embeddings(self):
        """Generate semantic embeddings for all notes"""
        print("Generating embeddings...")
        
        for note in self.notes.values():
            # Combine title, content, and tags for embedding
            text = f"{note.title}\n{note.content}\nTags: {', '.join(note.tags)}"
            
            # Generate embedding
            embedding = self.embedder.encode(text)
            note.embedding = embedding
        
        # Save to database
        self.save_to_database()
    
    def save_to_database(self):
        """Save notes and embeddings to database"""
        cursor = self.conn.cursor()
        
        for note in self.notes.values():
            cursor.execute('''
                INSERT OR REPLACE INTO notes 
                (path, title, content, tags, links, embedding, created, modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                note.path,
                note.title,
                note.content,
                json.dumps(note.tags),
                json.dumps(note.links),
                note.embedding.tobytes(),
                note.created,
                note.modified
            ))
        
        self.conn.commit()
    
    def build_knowledge_graph(self):
        """Build a knowledge graph from note connections"""
        print("Building knowledge graph...")
        
        # Add nodes
        for title, note in self.notes.items():
            self.knowledge_graph.add_node(title, note=note)
        
        # Add edges based on links
        for note in self.notes.values():
            for link in note.links:
                if link in self.notes:
                    self.knowledge_graph.add_edge(note.title, link)
        
        # Add edges based on semantic similarity
        self.add_semantic_edges()
    
    def add_semantic_edges(self, threshold=0.7):
        """Add edges based on semantic similarity"""
        notes_list = list(self.notes.values())
        embeddings = np.array([note.embedding for note in notes_list])
        
        # Compute cosine similarity matrix
        similarity_matrix = cosine_similarity(embeddings)
        
        for i, note1 in enumerate(notes_list):
            for j, note2 in enumerate(notes_list[i+1:], i+1):
                similarity = similarity_matrix[i][j]
                
                if similarity > threshold:
                    self.knowledge_graph.add_edge(
                        note1.title, 
                        note2.title, 
                        weight=similarity,
                        type='semantic'
                    )
    
    def semantic_search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search for notes using semantic similarity"""
        query_embedding = self.embedder.encode(query)
        
        similarities = []
        for title, note in self.notes.items():
            similarity = cosine_similarity(
                [query_embedding], 
                [note.embedding]
            )[0][0]
            similarities.append((title, similarity))
        
        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def cluster_notes(self, n_clusters: int = None) -> Dict[int, List[str]]:
        """Cluster notes based on semantic similarity"""
        embeddings = np.array([note.embedding for note in self.notes.values()])
        titles = list(self.notes.keys())
        
        # Auto-determine number of clusters if not specified
        if n_clusters is None:
            n_clusters = min(5, len(self.notes))  # Default to 5 or number of notes, whichever is smaller
        
        # Ensure we don't have more clusters than notes
        n_clusters = min(n_clusters, len(self.notes))
        
        if n_clusters < 2:
            # Not enough notes to cluster meaningfully
            return {0: titles}
        
        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # Group notes by cluster
        clusters = {}
        for i, title in enumerate(titles):
            cluster_id = cluster_labels[i]
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(title)
        
        return clusters
    
    def find_related_notes(self, note_title: str, max_results: int = 5) -> List[str]:
        """Find notes related to a given note"""
        if note_title not in self.notes:
            return []
        
        # Get direct connections from knowledge graph
        connected = list(self.knowledge_graph.neighbors(note_title))
        
        # Get semantically similar notes
        note_embedding = self.notes[note_title].embedding
        similarities = []
        
        for title, note in self.notes.items():
            if title != note_title:
                similarity = cosine_similarity(
                    [note_embedding], 
                    [note.embedding]
                )[0][0]
                similarities.append((title, similarity))
        
        # Sort and combine results
        similarities.sort(key=lambda x: x[1], reverse=True)
        related = [title for title, _ in similarities[:max_results]]
        
        # Prioritize direct connections
        result = connected + [note for note in related if note not in connected]
        return result[:max_results]
    
    def suggest_tags(self, content: str, top_k: int = 5) -> List[str]:
        """Suggest tags for new content based on existing notes"""
        content_embedding = self.embedder.encode(content)
        
        # Find most similar notes
        similarities = []
        for note in self.notes.values():
            if note.tags:  # Only consider notes with tags
                similarity = cosine_similarity(
                    [content_embedding], 
                    [note.embedding]
                )[0][0]
                similarities.append((note, similarity))
        
        # Sort by similarity and extract tags
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        tag_scores = {}
        for note, similarity in similarities[:10]:  # Top 10 similar notes
            for tag in note.tags:
                if tag not in tag_scores:
                    tag_scores[tag] = 0
                tag_scores[tag] += similarity
        
        # Return top tags
        sorted_tags = sorted(tag_scores.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in sorted_tags[:top_k]]
    
    def llm_query(self, question: str, context_size: int = 3) -> str:
        """Answer questions using LLM with relevant context"""
        if not self.llm_enabled:
            return "LLM features are disabled. Please provide an OpenAI API key."
        
        # Find relevant notes
        relevant_notes = self.semantic_search(question, top_k=context_size)
        
        # Build context
        context = "Relevant notes from your knowledge base:\n\n"
        for title, similarity in relevant_notes:
            note = self.notes[title]
            context += f"## {title}\n{note.content[:500]}...\n\n"
        
        # Create prompt
        prompt = f"""Based on the following notes from a personal knowledge base, please answer the question.

{context}

Question: {question}

Please provide a comprehensive answer based on the information in the notes above. If the notes don't contain enough information to fully answer the question, please say so."""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error querying LLM: {e}"
    
    def generate_concept_articles(self, concept: str, num_articles: int = 5, use_local_llm: bool = True) -> Dict[str, str]:
        """Generate multiple articles about a given concept"""
        articles = {}
        
        if use_local_llm or not self.llm_enabled:
            # Use local generation when OpenAI is not available
            articles = self._generate_articles_locally(concept, num_articles)
        else:
            # Use OpenAI for generation
            articles = self._generate_articles_openai(concept, num_articles)
        
        return articles
    
    def _generate_articles_locally(self, concept: str, num_articles: int) -> Dict[str, str]:
        """Generate articles using predefined templates and knowledge"""
        templates = {
            "Introduction": f"""# Introduction to {concept.title()}

{concept.title()} is a fundamental field of study that encompasses various principles, methods, and applications.

## Overview
This article provides an introduction to the core concepts and foundations of {concept}.

## Key Principles
- Fundamental concepts and definitions
- Historical development and evolution
- Core methodologies and approaches
- Modern applications and relevance

## Importance
Understanding {concept} is crucial for developing a comprehensive knowledge base and applying these principles in practical scenarios.

## Next Steps
- Explore specific subtopics within {concept}
- Study practical applications
- Engage with advanced concepts

Tags: #{concept.replace(' ', '')} #Introduction #Fundamentals
""",
            
            "History": f"""# History of {concept.title()}

The development of {concept} has a rich historical background spanning centuries of human intellectual progress.

## Ancient Origins
Early civilizations laid the groundwork for what would become modern {concept}.

## Classical Period
Significant developments during the classical era established fundamental principles.

## Modern Era
The industrial age and beyond brought revolutionary changes and applications.

## Contemporary Developments
Recent advances continue to shape our understanding and application of {concept}.

## Key Figures
Throughout history, numerous scholars and practitioners have contributed to the field.

## Timeline
- Ancient period: Early foundations
- Classical era: Systematic development
- Modern period: Rapid advancement
- Contemporary: Current innovations

Tags: #{concept.replace(' ', '')} #History #Development #Timeline
""",
            
            "Applications": f"""# Applications of {concept.title()}

{concept.title()} finds practical application across numerous fields and disciplines.

## Real-World Uses
- Industry applications
- Academic research
- Technology integration
- Problem-solving scenarios

## Case Studies
Examples of successful implementation demonstrate the practical value of {concept}.

## Benefits
- Improved efficiency
- Enhanced understanding
- Innovative solutions
- Practical outcomes

## Challenges
- Implementation difficulties
- Resource requirements
- Skill development needs
- Adaptation barriers

## Future Prospects
Emerging trends suggest expanding applications and continued relevance.

Tags: #{concept.replace(' ', '')} #Applications #Practice #Implementation
""",
            
            "Theory": f"""# Theoretical Foundations of {concept.title()}

The theoretical framework underlying {concept} provides the conceptual basis for understanding and application.

## Core Theories
Fundamental theoretical principles that govern {concept}.

## Frameworks
Structured approaches to understanding and organizing knowledge within {concept}.

## Models
Conceptual models that help explain complex relationships and processes.

## Principles
- Foundational principles
- Governing laws and rules
- Logical structures
- Systematic approaches

## Relationships
How different theoretical components interact and influence each other.

## Implications
The broader implications of theoretical understanding for practical application.

Tags: #{concept.replace(' ', '')} #Theory #Foundations #Principles #Framework
""",
            
            "Advanced Topics": f"""# Advanced Topics in {concept.title()}

Exploring sophisticated concepts and cutting-edge developments in {concept}.

## Complex Concepts
Advanced ideas that build upon fundamental knowledge.

## Specialized Areas
- Niche applications
- Expert-level topics
- Research frontiers
- Innovative approaches

## Current Research
Ongoing investigations and emerging discoveries in the field.

## Methodologies
Advanced techniques and sophisticated approaches.

## Integration
How advanced concepts connect with other fields and disciplines.

## Future Directions
Anticipated developments and emerging trends.

## Prerequisites
Understanding of foundational concepts is essential for grasping advanced topics.

Tags: #{concept.replace(' ', '')} #Advanced #Research #Specialized #Cutting-edge
"""
        }
        
        # Select articles based on availability and number requested
        selected_templates = list(templates.items())[:num_articles]
        
        return {title: content for title, content in selected_templates}
    
    def _generate_articles_openai(self, concept: str, num_articles: int) -> Dict[str, str]:
        """Generate articles using OpenAI API"""
        article_types = [
            "Introduction and Fundamentals",
            "Historical Development", 
            "Core Principles and Theory",
            "Practical Applications",
            "Advanced Topics and Research",
            "Methods and Techniques",
            "Related Fields and Connections",
            "Common Problems and Solutions"
        ]
        
        articles = {}
        
        for i, article_type in enumerate(article_types[:num_articles]):
            prompt = f"""Write a comprehensive article about "{article_type}" related to {concept}. 

The article should be:
- Well-structured with clear headings
- Informative and educational
- Around 500-800 words
- Written in markdown format
- Include relevant tags at the end

Title the article: "{article_type} in {concept.title()}"

Make it suitable for a personal knowledge base."""
            
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000
                )
                
                article_title = f"{article_type} in {concept.title()}"
                articles[article_title] = response.choices[0].message.content
                
            except Exception as e:
                print(f"Error generating article '{article_type}': {e}")
                # Fallback to local generation for this article
                fallback = self._generate_articles_locally(concept, 1)
                if fallback:
                    articles[article_type] = list(fallback.values())[0]
        
        return articles
    
    def create_concept_vault(self, concept: str, num_articles: int = 5, organize: bool = True):
        """Generate a complete knowledge vault for a concept"""
        print(f"\n=== Generating Knowledge Vault for '{concept.title()}' ===")
        
        # Generate articles
        print("Generating articles...")
        articles = self.generate_concept_articles(concept, num_articles)
        
        # Create folder for the concept
        concept_folder = self.vault_path / concept.replace(' ', '_').title()
        concept_folder.mkdir(exist_ok=True)
        
        # Save articles to files
        saved_files = []
        for title, content in articles.items():
            # Clean filename
            filename = title.replace('/', '-').replace('\\', '-') + '.md'
            file_path = concept_folder / filename
            
            try:
                file_path.write_text(content, encoding='utf-8')
                saved_files.append(str(file_path))
                print(f"Created: {filename}")
            except Exception as e:
                print(f"Error saving {filename}: {e}")
        
        # Reload vault to include new articles
        print("Processing new articles...")
        self.load_vault()
        
        if organize:
            # Analyze and organize the new content
            print("\n=== AI Analysis of Generated Content ===")
            
            # Find articles related to the concept
            concept_notes = []
            for title, note in self.notes.items():
                if concept.lower() in note.content.lower() or concept.lower() in title.lower():
                    concept_notes.append(title)
            
            print(f"Found {len(concept_notes)} articles related to '{concept}':")
            for note_title in concept_notes:
                print(f"  - {note_title}")
            
            # Semantic analysis
            if concept_notes:
                print(f"\n=== Semantic Relationships ===")
                base_note = concept_notes[0]
                related = self.find_related_notes(base_note, max_results=len(concept_notes))
                
                print(f"Semantic connections from '{base_note}':")
                for related_note in related:
                    if related_note in concept_notes:
                        # Calculate similarity
                        sim = cosine_similarity(
                            [self.notes[base_note].embedding],
                            [self.notes[related_note].embedding]
                        )[0][0]
                        print(f"  - {related_note}: {sim:.3f} similarity")
            
            # Suggest organization
            print(f"\n=== Suggested Organization ===")
            organization = self.auto_organize()
            
            concept_key = None
            for folder_name, notes in organization.items():
                if any(concept.lower() in note.lower() for note in notes):
                    concept_key = folder_name
                    break
            
            if concept_key:
                print(f"Recommended folder structure for {concept}:")
                print(f"{concept_key}/")
                for note in organization[concept_key]:
                    if concept.lower() in note.lower():
                        print(f"  - {note}")
        
        print(f"\n✅ Successfully created {len(articles)} articles about '{concept}'")
        print(f"📁 Saved in: {concept_folder}")
        
        return saved_files
    
    def auto_organize(self):
        """Automatically organize the vault by suggesting folder structure"""
        # Determine appropriate number of clusters based on vault size
        num_notes = len(self.notes)
        if num_notes < 5:
            n_clusters = max(1, num_notes // 2)  # Small vaults: fewer clusters
        elif num_notes < 20:
            n_clusters = min(5, num_notes)
        else:
            n_clusters = min(8, num_notes // 3)  # Larger vaults: more clusters
            
        clusters = self.cluster_notes(n_clusters=n_clusters)
        
        organization = {}
        for cluster_id, note_titles in clusters.items():
            # Find common themes in cluster
            cluster_tags = []
            for title in note_titles:
                cluster_tags.extend(self.notes[title].tags)
            
            # Most common tag becomes folder name
            if cluster_tags:
                from collections import Counter
                most_common_tag = Counter(cluster_tags).most_common(1)[0][0]
                organization[most_common_tag] = note_titles
            else:
                organization[f"Topic_{cluster_id + 1}"] = note_titles
        
        return organization

# Example usage
def main():
    # For testing, create a simple demo vault if it doesn't exist
    demo_vault_path = Path("demo_vault")
    
    # Create demo vault structure
    if not demo_vault_path.exists():
        print("Creating demo vault...")
        demo_vault_path.mkdir()
        
        # Create some sample notes
        sample_notes = {
            "Machine Learning Basics.md": """# Machine Learning Basics

Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.

## Key Concepts
- Supervised learning
- Unsupervised learning  
- Neural networks

Tags: #AI #MachineLearning #DataScience
""",
            "Deep Learning.md": """# Deep Learning

Deep learning uses neural networks with multiple layers to model complex patterns.

## Applications
- Computer vision
- Natural language processing
- Speech recognition

Links: [[Machine Learning Basics]]

Tags: #AI #DeepLearning #NeuralNetworks
""",
            "Data Science Projects.md": """# Data Science Projects

Collection of interesting data science projects and methodologies.

## Project Ideas
- Predictive analytics
- Customer segmentation
- Recommendation systems

Tags: #DataScience #Projects #Analytics
"""
        }
        
        for filename, content in sample_notes.items():
            (demo_vault_path / filename).write_text(content, encoding='utf-8')
        
        print(f"Demo vault created at: {demo_vault_path.absolute()}")
    
    # Initialize the brain
    try:
        brain = ObsidianBrain(
            vault_path=str(demo_vault_path),
            openai_api_key=None  # Set your API key here if you have one
        )
        
        # Semantic search
        print("\n=== Semantic Search ===")
        results = brain.semantic_search("artificial intelligence and neural networks")
        for title, similarity in results:
            print(f"{title}: {similarity:.3f}")
        
        # Find related notes
        print("\n=== Related Notes ===")
        if brain.notes:
            first_note = list(brain.notes.keys())[0]
            related = brain.find_related_notes(first_note)
            print(f"Notes related to '{first_note}':")
            for note in related:
                print(f"  - {note}")
        
        # Suggest tags for new content
        print("\n=== Tag Suggestions ===")
        new_content = "This article discusses convolutional neural networks for image classification"
        suggested_tags = brain.suggest_tags(new_content)
        print(f"Suggested tags for new content: {suggested_tags}")
        
        # Auto-organize vault
        print("\n=== Auto Organization ===")
        organization = brain.auto_organize()
        for folder, notes in organization.items():
            print(f"\n{folder}/")
            for note in notes:
                print(f"  - {note}")
        
        print(f"\nProcessed {len(brain.notes)} notes successfully!")
        print("You can now modify the vault_path in the main() function to point to your actual Obsidian vault.")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure you have installed required packages:")
        print("   pip install sentence-transformers networkx scikit-learn numpy")
        print("2. Check that the vault path exists and is accessible")
        print("3. Ensure you have write permissions in the directory")

if __name__ == "__main__":
    main()