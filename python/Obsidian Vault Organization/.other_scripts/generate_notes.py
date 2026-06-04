import os
import re
from pathlib import Path

# Complete Human Understanding tree structure
knowledge_tree = {
    "Knowledge": {
        "Natural Sciences": {
            "Physical Sciences": {
                "Physics": {
                    "Classical Physics": {
                        "Mechanics": ["Kinematics", "Dynamics", "Statics", "Fluid Mechanics", "Continuum Mechanics"],
                        "Thermodynamics": ["Statistical Mechanics", "Heat Transfer", "Phase Transitions", "Entropy"],
                        "Electromagnetism": ["Electrostatics", "Magnetostatics", "Electromagnetic Induction", "Maxwell's Equations", "Electromagnetic Waves"],
                        "Optics": ["Geometric Optics", "Wave Optics", "Polarization", "Interference", "Diffraction"]
                    },
                    "Modern Physics": {
                        "Quantum Mechanics": ["Wave-Particle Duality", "Schrödinger Equation", "Quantum States", "Uncertainty Principle", "Quantum Entanglement", "Quantum Field Theory"],
                        "Relativity": {
                            "Special Relativity": ["Time Dilation", "Length Contraction", "Mass-Energy Equivalence"],
                            "General Relativity": ["Spacetime Curvature", "Gravitational Waves", "Black Holes", "Cosmology"]
                        }
                    },
                    "Applied Physics": ["Medical Physics", "Geophysics", "Atmospheric Physics", "Engineering Physics", "Computational Physics"],
                    "Theoretical Physics": ["Analytical Mechanics", "Quantum Field Theory", "String Theory", "Loop Quantum Gravity", "Theory of Everything"]
                },
                "Chemistry": ["Inorganic Chemistry", "Organic Chemistry", "Physical Chemistry", "Analytical Chemistry", "Biochemistry", "Materials Chemistry"],
                "Astronomy": ["Observational Astronomy", "Theoretical Astronomy", "Planetary Science", "Stellar Astronomy", "Galactic Astronomy", "Cosmology", "Astrobiology"]
            },
            "Life Sciences": {
                "Biology": ["Cell Biology", "Molecular Biology", "Genetics", "Evolutionary Biology", "Ecology", "Physiology", "Developmental Biology"],
                "Medicine": ["Anatomy", "Pathology", "Pharmacology", "Clinical Medicine", "Surgery", "Psychiatry", "Public Health"],
                "Neuroscience": ["Cognitive Neuroscience", "Behavioral Neuroscience", "Computational Neuroscience", "Neuroanatomy", "Neurophysiology"]
            },
            "Earth Sciences": {
                "Geology": ["Mineralogy", "Petrology", "Stratigraphy", "Structural Geology", "Paleontology", "Geophysics"],
                "Atmospheric Sciences": ["Meteorology", "Climatology", "Atmospheric Physics", "Atmospheric Chemistry"],
                "Oceanography": ["Physical Oceanography", "Chemical Oceanography", "Biological Oceanography", "Marine Geology"],
                "Environmental Science": ["Environmental Chemistry", "Environmental Physics", "Ecology", "Conservation Science"]
            }
        },
        "Formal Sciences": {
            "Mathematics": {
                "Pure Mathematics": ["Algebra", "Analysis", "Geometry", "Topology", "Number Theory", "Logic", "Set Theory"],
                "Applied Mathematics": ["Statistics", "Probability", "Mathematical Physics", "Operations Research", "Numerical Analysis"]
            },
            "Logic": ["Propositional Logic", "Predicate Logic", "Modal Logic", "Fuzzy Logic", "Mathematical Logic"],
            "Computer Science": {
                "Theoretical Computer Science": ["Algorithms", "Computational Complexity", "Formal Methods", "Programming Language Theory"],
                "Applied Computer Science": ["Software Engineering", "Database Systems", "Computer Networks", "Human-Computer Interaction", "Artificial Intelligence", "Machine Learning"]
            }
        },
        "Social Sciences": {
            "Psychology": ["Cognitive Psychology", "Social Psychology", "Developmental Psychology", "Clinical Psychology", "Behavioral Psychology"],
            "Sociology": ["Social Theory", "Social Research Methods", "Criminology", "Urban Sociology", "Political Sociology"],
            "Economics": ["Microeconomics", "Macroeconomics", "Econometrics", "Behavioral Economics", "International Economics"],
            "Political Science": ["Political Theory", "Comparative Politics", "International Relations", "Public Policy", "Public Administration"],
            "Anthropology": ["Cultural Anthropology", "Physical Anthropology", "Linguistic Anthropology", "Archaeological Anthropology"]
        },
        "Applied Sciences": {
            "Engineering": {
                "Civil Engineering": ["Structural Engineering", "Transportation Engineering", "Environmental Engineering", "Geotechnical Engineering"],
                "Mechanical Engineering": ["Thermodynamics", "Fluid Mechanics", "Materials Science", "Manufacturing"],
                "Electrical Engineering": ["Electronics", "Power Systems", "Control Systems", "Telecommunications"],
                "Chemical Engineering": ["Process Design", "Reaction Engineering", "Separation Processes"],
                "Computer Engineering": ["Hardware Design", "Embedded Systems", "Computer Architecture"]
            },
            "Technology": ["Information Technology", "Biotechnology", "Nanotechnology", "Renewable Energy", "Robotics"],
            "Medicine (Applied)": ["Clinical Practice", "Medical Research", "Healthcare Systems", "Medical Technology"]
        },
        "Humanities": {
            "Philosophy": {
                "Theoretical Philosophy": ["Metaphysics", "Epistemology", "Logic", "Philosophy of Mind", "Philosophy of Science"],
                "Practical Philosophy": ["Ethics", "Political Philosophy", "Aesthetics", "Philosophy of Religion"],
                "Historical Philosophy": ["Ancient Philosophy", "Medieval Philosophy", "Modern Philosophy", "Contemporary Philosophy"]
            },
            "History": {
                "Chronological History": ["Ancient History", "Medieval History", "Modern History", "Contemporary History"],
                "Thematic History": ["Political History", "Social History", "Cultural History", "Economic History", "Military History"],
                "Regional History": ["World History", "National Histories", "Local History"]
            },
            "Language and Literature": {
                "Linguistics": ["Phonetics", "Phonology", "Morphology", "Syntax", "Semantics", "Pragmatics", "Sociolinguistics"],
                "Literature": ["Literary Theory", "Comparative Literature", "Genre Studies", "Period Studies", "National Literatures"]
            },
            "Religious Studies": ["Theology", "Comparative Religion", "Religious History", "Religious Philosophy", "Religious Anthropology"]
        }
    },
    "Creative Expression": {
        "Visual Arts": {
            "Fine Arts": ["Painting", "Sculpture", "Drawing", "Printmaking"],
            "Applied Arts": ["Graphic Design", "Industrial Design", "Fashion Design", "Architecture"],
            "Digital Arts": ["Digital Painting", "3D Modeling", "Animation", "Interactive Media"]
        },
        "Performing Arts": {
            "Music": {
                "Performance": ["Vocal Music", "Instrumental Music", "Conducting"],
                "Composition": ["Classical Composition", "Popular Music", "Electronic Music"],
                "Music Theory": ["Harmony", "Counterpoint", "Analysis", "Ethnomusicology"]
            },
            "Theater": ["Acting", "Directing", "Playwriting", "Stage Design", "Theater History"],
            "Dance": ["Classical Dance", "Contemporary Dance", "Folk Dance", "Choreography"]
        },
        "Literature (Creative)": ["Fiction", "Poetry", "Drama", "Creative Nonfiction", "Screenwriting"],
        "Design": ["User Experience Design", "Product Design", "Environmental Design", "Communication Design"],
        "Innovation": ["Entrepreneurship", "Technology Innovation", "Social Innovation", "Creative Problem Solving"]
    }
}

def flatten_tree(tree, parent_path=""):
    """Flatten nested tree structure and track relationships"""
    topics = {}
    
    def recurse(node, path="", parent=None, level=0):
        if isinstance(node, dict):
            for key, value in node.items():
                current_path = f"{path}/{key}" if path else key
                topics[key] = {
                    'path': current_path,
                    'parent': parent,
                    'children': [],
                    'siblings': [],
                    'level': level,
                    'category': get_main_category(current_path)
                }
                if parent:
                    topics[parent]['children'].append(key)
                
                recurse(value, current_path, key, level + 1)
        elif isinstance(node, list):
            for item in node:
                topics[item] = {
                    'path': f"{path}/{item}",
                    'parent': parent,
                    'children': [],
                    'siblings': [x for x in node if x != item],
                    'level': level,
                    'category': get_main_category(f"{path}/{item}")
                }
                if parent:
                    topics[parent]['children'].append(item)
    
    recurse(tree)
    return topics

def get_main_category(path):
    """Extract main category for tagging"""
    parts = path.split('/')
    if len(parts) >= 2:
        if parts[1] in ["Natural Sciences", "Formal Sciences", "Social Sciences", "Applied Sciences", "Humanities"]:
            return parts[1].lower().replace(" ", "-")
        elif parts[0] == "Creative Expression":
            return "creative-expression"
    return "knowledge"

def generate_related_files(topic, topic_data, all_topics):
    """Generate related files list based on hierarchy"""
    related = set()
    
    # Add parent
    if topic_data['parent']:
        related.add(f"[[{topic_data['parent']}]]")
    
    # Add children (limit to 8 for broader subjects)
    children = topic_data['children'][:8]
    for child in children:
        related.add(f"[[{child}]]")
    
    # Add siblings (limit to 4)
    siblings = topic_data['siblings'][:4]
    for sibling in siblings:
        related.add(f"[[{sibling}]]")
    
    # Add root based on category
    if topic != "Knowledge" and topic != "Creative Expression":
        if topic_data['category'] == "creative-expression":
            related.add("[[Creative Expression]]")
        else:
            related.add("[[Knowledge]]")
    
    return sorted(list(related))

def create_note_content(topic, topic_data, all_topics):
    """Create the markdown content for a note"""
    related_files = generate_related_files(topic, topic_data, all_topics)
    
    # Determine tags
    tags = [topic_data['category']]
    if topic in ["Knowledge", "Creative Expression"]:
        tags.append("index")
    
    content = f"""---
tags:
"""
    for tag in tags:
        content += f"  - {tag}\n"
    
    content += "related-files:\n"
    for file_link in related_files:
        content += f"  - \"{file_link}\"\n"
    
    content += "---\n\n"
    content += f"# {topic}\n\n"
    content += "## Overview\n\n"
    
    if topic_data['children']:
        content += "## Subfields\n\n"
        for child in topic_data['children'][:10]:  # Limit displayed children
            content += f"- [[{child}]]\n"
        content += "\n"
    
    content += "## Related Topics\n\n"
    for file_link in related_files:
        if file_link != f"[[{topic}]]":
            content += f"- {file_link}\n"
    
    return content

def generate_obsidian_notes(tree_section=None, output_dir="knowledge_notes"):
    """Generate Obsidian notes for entire tree or specific section"""
    Path(output_dir).mkdir(exist_ok=True)
    
    # Use specific section or entire tree
    if tree_section:
        if tree_section in knowledge_tree:
            working_tree = {tree_section: knowledge_tree[tree_section]}
        else:
            # Try to find section in nested structure
            working_tree = find_section_in_tree(knowledge_tree, tree_section)
            if not working_tree:
                print(f"Section '{tree_section}' not found in tree")
                return
    else:
        working_tree = knowledge_tree
    
    all_topics = flatten_tree(working_tree)
    
    # Generate notes for all topics
    for topic, topic_data in all_topics.items():
        content = create_note_content(topic, topic_data, all_topics)
        filename = f"{output_dir}/{topic.replace('/', '_')}.md"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"Created: {filename}")
    
    print(f"\nGenerated {len(all_topics)} notes in '{output_dir}/' directory")

def find_section_in_tree(tree, section_name):
    """Recursively find a section in the tree"""
    if isinstance(tree, dict):
        for key, value in tree.items():
            if key == section_name:
                return {key: value}
            result = find_section_in_tree(value, section_name)
            if result:
                return result
    return None

def list_available_sections():
    """List all available sections for generation"""
    def get_sections(tree, level=0):
        sections = []
        if isinstance(tree, dict):
            for key, value in tree.items():
                sections.append("  " * level + key)
                sections.extend(get_sections(value, level + 1))
        return sections
    
    return get_sections(knowledge_tree)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        section = sys.argv[1]
        if section == "--list":
            print("Available sections:")
            for section in list_available_sections():
                print(section)
        else:
            generate_obsidian_notes(section)
    else:
        generate_obsidian_notes()  # Generate entire tree